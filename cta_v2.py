#!/usr/bin/env python3
"""CTA v2 — cải tiến hiệu suất:
  1) ĐA CHU KỲ breakout (5/20/55) mỗi thị trường -> tín hiệu mượt, ít nhiễu.
  2) VOL-TARGETING danh mục: giữ biến động ổn định -> cắt đuôi drawdown -> Calmar cao.

So với baseline (entry5 đơn, không vol-target). 6 thị trường, 2018-2026.
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

from run_portfolio import load_h4_safe, quote_to_usd
from src.backtest.broker import CostConfig, TradeBroker
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr

START, END = "2018-01-01", "2026-06-20"
MARKETS = ["XAUUSD", "GBPJPY", "WTI", "COFFEE", "BTCUSD", "ETHUSD"]
ENTRIES = [5, 20, 55]          # đa chu kỳ breakout


def sleeve(sym, entry):
    df = load_h4_safe(sym, START, END)
    s = BreakoutTrend(BreakoutParams(entry, 14, 3.0, 5.0, False)).generate_setups(
        df, pd.Series(0, index=df.index))
    q = quote_to_usd(sym, df, START, END) if sym == "GBPJPY" else None
    res = TradeBroker(sym, 0.01 if "JPY" in sym else 0.0001, 10_000.0,
                      risk_pct=0.01, costs=CostConfig()).run(df, s, q, atr(df, 14).to_numpy())
    return res.equity.pct_change()


def market_return(sym):
    """Trung bình các sub-sleeve đa chu kỳ -> 1 chuỗi lợi nhuận mỗi thị trường."""
    subs = [sleeve(sym, e) for e in ENTRIES]
    return pd.concat(subs, axis=1).mean(axis=1)


def combine(rets):
    mat = pd.concat(rets, axis=1).dropna(how="all")
    vol = mat.std(); inv = 1.0 / vol
    active = mat.notna().astype(float)
    w = active.mul(inv, axis=1); w = w.div(w.sum(axis=1), axis=0)
    return (mat.fillna(0) * w).sum(axis=1)


def vol_target(r, target_ann=0.10, span=64, cap=3.0):
    """Scale lợi nhuận để vol ~ target (cắt đuôi DD)."""
    rv = r.ewm(span=span).std() * np.sqrt(252 * 6)   # vol năm hóa (H4)
    scale = (target_ann / rv).shift(1).clip(0, cap).fillna(0)
    return r * scale


def stats(r, lev):
    eq = (1 + r * lev).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    return cagr, dd, (cagr / abs(dd) if dd < 0 else np.nan)


def report(name, r):
    sh = r.mean() / r.std() * np.sqrt(252 * 6)
    print(f"\n=== {name} (Sharpe {sh:.2f}) ===")
    print(f"{'lev':>4} | {'CAGR':>7} {'maxDD':>8} {'Calmar':>7} | đạt CAGR>35&DD<40?")
    for L in [2, 3, 4, 4.5, 5, 6]:
        cg, dd, cal = stats(r, L)
        flag = "✅" if (cg > 0.35 and dd > -0.40) else ""
        print(f"{L:4.1f} | {cg*100:6.1f}% {dd*100:7.1f}% {cal:7.2f} | {flag}")
    cut = r.index[int(len(r)*0.6)]
    for lbl, seg in [("IS", r[:cut]), ("OOS", r[cut:])]:
        cg, dd, cal = stats(seg, 4)
        print(f"  [{lbl} lev4] CAGR {cg*100:.0f}% DD {dd*100:.0f}% Calmar {cal:.2f}")


def main():
    print("Tính baseline (entry5) ...")
    base = combine([sleeve(s, 5) for s in MARKETS])
    report("BASELINE entry5", base)

    for tv in [0.08, 0.10, 0.12]:
        report(f"BASELINE + VOL-TARGET {int(tv*100)}%", vol_target(base, tv))


if __name__ == "__main__":
    main()
