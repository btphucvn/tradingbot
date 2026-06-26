#!/usr/bin/env python3
"""Backtest 1 cặp bất kỳ (kể cả quote != USD) + quy đổi tỷ giá + lọc phiên + risk sweep.

quote_to_usd:
  * Cặp XXX/USD (quote=USD): = 1.
  * Cặp USD/XXX (quote=XXX): = 1/giá chính nó (vì giá = XXX trên 1 USD).
  * Cặp chéo XXX/JPY (quote=JPY): = 1/USDJPY (tải thêm).
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.broker import TradeBroker
from src.backtest.engine import BacktestResult, CostConfig
from src.backtest.metrics import compute, report
from src.data.loader import load, pip_size
from src.strategies.price_action_sr import (PAParams, PriceActionSR,
                                            d1_trend_from, map_d1_to_h4)


def quote_to_usd_series(symbol: str, df: pd.DataFrame, start, end) -> np.ndarray:
    base, quote = symbol[:3], symbol[3:]
    if quote == "USD":
        return np.ones(len(df))
    if base == "USD":                      # USD/XXX -> 1/giá
        return (1.0 / df["close"]).to_numpy()
    if quote == "JPY":                     # cross /JPY -> 1/USDJPY
        usdjpy = load("USDJPY", "H4", start, end)["close"]
        aligned = usdjpy.reindex(df.index, method="ffill").bfill()
        return (1.0 / aligned).to_numpy()
    raise ValueError(f"Chưa hỗ trợ quy đổi quote {quote!r} cho {symbol}")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--equity", type=float, default=10_000.0)
    p.add_argument("--risks", default="0.01,0.02,0.03,0.05")
    p.add_argument("--tp-atr", type=float, default=1.5)
    p.add_argument("--sl-atr", type=float, default=2.5)
    p.add_argument("--mode", default="trend")
    p.add_argument("--min-touches", type=int, default=2)
    p.add_argument("--ema", type=int, default=50)
    p.add_argument("--session-start", type=int, default=0)
    p.add_argument("--session-end", type=int, default=24)
    p.add_argument("--split", type=float, default=0.7)
    p.add_argument("--out", default="results/pair.png")
    return p.parse_args()


def seg(res, lo, hi):
    eq = res.equity.loc[lo:hi]
    tr = res.trades
    if not tr.empty:
        tr = tr[(tr["exit_time"] >= lo) & (tr["exit_time"] < hi)].reset_index(drop=True)
    return BacktestResult(eq, eq.pct_change().fillna(0.0),
                          res.position.loc[lo:hi], tr, float(eq.iloc[0]), res.meta)


def main():
    a = parse_args()
    sym = a.symbol.upper()
    print(f"Tải + sinh tín hiệu {sym} ({a.start}..{a.end})...")
    df = load(sym, "H4", a.start, a.end)
    df_d1 = load(sym, "D1", a.start, a.end)
    trend = map_d1_to_h4(d1_trend_from(df_d1, a.ema), df.index)
    q = quote_to_usd_series(sym, df, a.start, a.end)
    params = PAParams(exit_mode="atr", min_rr=0.0, tp_atr=a.tp_atr, sl_atr=a.sl_atr,
                      mode=a.mode, min_touches=a.min_touches,
                      session_start=a.session_start, session_end=a.session_end)
    setups = PriceActionSR(params).generate_setups(df, trend)
    pip = pip_size(sym)
    sess = "" if (a.session_start == 0 and a.session_end == 24) else f" sess={a.session_start}-{a.session_end}h"
    print(f"-> {len(df)} nến, {len(setups)} setup (tp={a.tp_atr} sl={a.sl_atr} {a.mode} touch={a.min_touches}{sess})\n")

    risks = [float(x) for x in a.risks.split(",")]
    print(f"{'risk':>6} | {'return':>11} | {'x lần':>7} | {'CAGR':>7} | "
          f"{'winrate':>7} | {'maxDD':>7} | {'PF':>5} | lệnh")
    print("-" * 78)
    best = None
    for r in risks:
        res = TradeBroker(sym, pip, a.equity, risk_pct=r, costs=CostConfig()).run(df, setups, q)
        m = compute(res)
        x = m["final_equity"] / a.equity
        print(f"{r*100:5.0f}% | {m['total_return']*100:+10.0f}% | {x:6.1f}x | "
              f"{m['cagr']*100:+6.1f}% | {m['win_rate']*100:6.1f}% | "
              f"{m['max_drawdown']*100:6.1f}% | {m['profit_factor']:4.2f} | {m['n_trades']}")
        # giữ mức risk cho x>=5 và DD ít tệ nhất; nếu không có thì risk cao nhất
        if x >= 5.0 and (best is None or m["max_drawdown"] > best[1]):
            best = (r, m["max_drawdown"], res, x)
    if best is None:
        best = (r, m["max_drawdown"], res, x)

    r, _, res, x = best
    print(f"\n>>> Risk {r*100:.0f}%/lệnh ({x:.1f}x). Chi tiết IS/OOS:")
    cut = res.equity.index[int(len(res.equity) * a.split)]
    print(report(compute(seg(res, res.equity.index[0], cut)), "IN-SAMPLE"))
    print(report(compute(seg(res, cut, res.equity.index[-1] + pd.Timedelta(seconds=1))), "OUT-OF-SAMPLE"))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(res.equity.index, res.equity.values, lw=1.0)
    ax.axhline(a.equity, color="gray", ls=":", lw=0.8)
    ax.axhline(a.equity * 5, color="green", ls="--", lw=1, label="mốc x5")
    ax.set_yscale("log")
    ax.set_title(f"{sym} H4 — risk {r*100:.0f}% — {x:.1f}x — winrate {compute(res)['win_rate']*100:.0f}%")
    ax.set_ylabel("Equity ($, log)"); ax.legend()
    fig.tight_layout(); fig.savefig(a.out, dpi=110)
    print(f"\nĐã lưu {a.out}")


if __name__ == "__main__":
    main()
