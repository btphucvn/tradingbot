#!/usr/bin/env python3
"""Backtest breakout cưỡi-trend (trailing stop) cho 1 cặp + risk sweep.

Mặc định GBP/JPY. Đây là phía trend-following: kỳ vọng bắt sóng lớn (x cao)
nhưng winrate thấp. So với S/R fade (winrate cao, x thấp) để thấy mâu thuẫn.
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from run_pair import quote_to_usd_series, seg
from src.backtest.broker import CostConfig, TradeBroker
from src.backtest.metrics import compute, report
from src.data.loader import load, pip_size
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="GBPJPY")
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--equity", type=float, default=10_000.0)
    p.add_argument("--risks", default="0.01,0.02,0.03,0.05")
    p.add_argument("--entry", type=int, default=20)
    p.add_argument("--sl-atr", type=float, default=2.0)
    p.add_argument("--trail-atr", type=float, default=3.0)
    p.add_argument("--no-trend", action="store_true")
    p.add_argument("--split", type=float, default=0.7)
    p.add_argument("--out", default="results/breakout.png")
    return p.parse_args()


def main():
    a = parse_args()
    sym = a.symbol.upper()
    print(f"Tải + sinh tín hiệu breakout {sym} ({a.start}..{a.end})...")
    df = load(sym, "H4", a.start, a.end)
    df_d1 = load(sym, "D1", a.start, a.end)
    from src.strategies.price_action_sr import d1_trend_from, map_d1_to_h4
    trend = map_d1_to_h4(d1_trend_from(df_d1, 50), df.index)
    q = quote_to_usd_series(sym, df, a.start, a.end)
    a_arr = atr(df, 14).to_numpy()

    params = BreakoutParams(entry_period=a.entry, sl_atr=a.sl_atr,
                            trail_atr=a.trail_atr, use_trend=not a.no_trend)
    setups = BreakoutTrend(params).generate_setups(df, trend)
    pip = pip_size(sym)
    print(f"-> {len(df)} nến, {len(setups)} setup "
          f"(entry={a.entry} sl={a.sl_atr} trail={a.trail_atr} trend={not a.no_trend})\n")

    risks = [float(x) for x in a.risks.split(",")]
    print(f"{'risk':>6} | {'return':>11} | {'x lần':>7} | {'CAGR':>7} | "
          f"{'winrate':>7} | {'maxDD':>7} | {'PF':>5} | lệnh")
    print("-" * 78)
    best = None
    for r in risks:
        res = TradeBroker(sym, pip, a.equity, risk_pct=r, costs=CostConfig()).run(df, setups, q, a_arr)
        m = compute(res)
        x = m["final_equity"] / a.equity
        print(f"{r*100:5.0f}% | {m['total_return']*100:+10.0f}% | {x:6.1f}x | "
              f"{m['cagr']*100:+6.1f}% | {m['win_rate']*100:6.1f}% | "
              f"{m['max_drawdown']*100:6.1f}% | {m['profit_factor']:4.2f} | {m['n_trades']}")
        if best is None or x > best[1]:
            best = (r, x, res)

    r, x, res = best
    print(f"\n>>> Risk tốt nhất {r*100:.0f}%/lệnh ({x:.1f}x). Chi tiết IS/OOS:")
    cut = res.equity.index[int(len(res.equity) * a.split)]
    print(report(compute(seg(res, res.equity.index[0], cut)), "IN-SAMPLE"))
    print(report(compute(seg(res, cut, res.equity.index[-1] + pd.Timedelta(seconds=1))), "OUT-OF-SAMPLE"))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(res.equity.index, res.equity.values, lw=1.0)
    ax.axhline(a.equity, color="gray", ls=":", lw=0.8)
    ax.axhline(a.equity * 5, color="green", ls="--", lw=1, label="mốc x5")
    ax.set_yscale("log")
    ax.set_title(f"{sym} H4 breakout — risk {r*100:.0f}% — {x:.1f}x — winrate {compute(res)['win_rate']*100:.0f}%")
    ax.set_ylabel("Equity ($, log)"); ax.legend()
    fig.tight_layout(); fig.savefig(a.out, dpi=110)
    print(f"\nĐã lưu {a.out}")


if __name__ == "__main__":
    main()
