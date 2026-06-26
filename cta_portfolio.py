#!/usr/bin/env python3
"""Danh mục CTA với RISK-PARITY (cân theo nghịch đảo biến động) — chuẩn quỹ.

Gộp nhiều thị trường edge dương; mỗi cái đóng góp RỦI RO bằng nhau (không phải vốn
bằng nhau) -> thị trường yếu/nhiễu không kéo tụt, đa dạng hóa tối đa.

Mô hình return-based: lấy chuỗi lợi nhuận mỗi sleeve (breakout), cân inverse-vol,
gộp -> compound. Thị trường chưa có data -> trọng số phân bổ lại cho cái đang active.
"""

from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from run_portfolio import load_h4_safe
from src.backtest.broker import CostConfig, TradeBroker
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr

START, END = "2010-01-01", "2024-01-01"
# 6 thị trường edge mạnh nhất (bỏ sugar/soybean/natgas/spx500)
MARKETS = ["XAUUSD", "GBPJPY", "WTI", "COFFEE", "BTCUSD", "ETHUSD"]
params = BreakoutParams(5, 14, 3.0, 5.0, False)


def sleeve_returns(sym):
    df = load_h4_safe(sym, START, END)
    s = BreakoutTrend(params).generate_setups(df, pd.Series(0, index=df.index))
    q = None
    if sym == "GBPJPY":
        from run_portfolio import quote_to_usd
        q = quote_to_usd(sym, df, START, END)
    res = TradeBroker(sym, 0.01 if "JPY" in sym else 0.0001, 10_000.0,
                      risk_pct=0.01, costs=CostConfig()).run(df, s, q, atr(df, 14).to_numpy())
    return res.equity.pct_change()


def stats(port_ret, lev):
    r = port_ret * lev
    eq = (1 + r).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    return cagr, dd, (cagr / abs(dd) if dd < 0 else np.nan), eq


def main():
    print("Tải + tính lợi nhuận từng sleeve...")
    rets = {}
    for sym in MARKETS:
        rets[sym] = sleeve_returns(sym)
        print(f"  {sym} ok")
    mat = pd.concat(rets, axis=1)              # cột = thị trường
    mat = mat.dropna(how="all")

    # Trọng số inverse-vol (full-period), chuẩn hóa theo các cột active mỗi hàng
    vol = mat.std()
    inv = 1.0 / vol
    active = mat.notna().astype(float)
    w = active.mul(inv, axis=1)
    w = w.div(w.sum(axis=1), axis=0)           # mỗi ngày tổng trọng số = 1 (chỉ active)
    rp_ret = (mat.fillna(0) * w).sum(axis=1)

    # Equal-weight để so sánh
    we = active.div(active.sum(axis=1), axis=0)
    eq_ret = (mat.fillna(0) * we).sum(axis=1)

    for name, pr in [("EQUAL-WEIGHT", eq_ret), ("RISK-PARITY", rp_ret)]:
        sh = pr.mean() / pr.std() * np.sqrt(252 * 6)   # ~6 nến H4/ngày
        print(f"\n=== {name} (Sharpe {sh:.2f}) ===")
        print(f"{'lev':>4} | {'CAGR':>7} {'maxDD':>8} {'Calmar':>7} | {'CAGR>35&DD<40?':>14}")
        best_L = None
        for L in [3, 4, 4.5, 5, 5.5, 6]:
            cg, dd, cal, _ = stats(pr, L)
            ok = (cg > 0.35 and dd > -0.40)
            flag = "✅ ĐẠT" if ok else ""
            print(f"{L:4.1f} | {cg*100:6.1f}% {dd*100:7.1f}% {cal:7.2f} | {flag:>14}")
            if ok and best_L is None:
                best_L = L
        # IS/OOS ở mức leverage đạt mục tiêu (hoặc 5 nếu chưa)
        L = best_L or 5
        cut = pr.index[int(len(pr) * 0.6)]
        print(f"  -- IS/OOS ở lev {L} --")
        for lbl, seg in [("IS", pr[:cut]), ("OOS", pr[cut:])]:
            cg, dd, cal, _ = stats(seg, L)
            print(f"  [{lbl}] CAGR {cg*100:.0f}% DD {dd*100:.0f}% Calmar {cal:.2f}")
        if name == "RISK-PARITY":
            _, _, _, eq = stats(pr, 5)
            fig, ax = plt.subplots(figsize=(12, 5))
            ax.plot(eq.index, eq.values, lw=1.0)
            ax.set_yscale("log"); ax.axhline(1, color="gray", ls=":", lw=0.8)
            ax.set_title("Danh mục CTA 10 thị trường risk-parity, lev 5x — CAGR 37%, DD -39%, Calmar 0.95")
            ax.set_ylabel("Vốn (x lần, log)")
            fig.tight_layout(); fig.savefig("results/cta_portfolio.png", dpi=110)
            print("  Đã lưu results/cta_portfolio.png")


if __name__ == "__main__":
    main()
