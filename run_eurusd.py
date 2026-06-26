#!/usr/bin/env python3
"""Tìm risk để EURUSD đạt x5 mà winrate vẫn >60%.

Winrate KHÔNG đổi theo risk (cùng tập lệnh TP/SL) -> sinh setup 1 lần, rồi chạy
broker ở nhiều mức risk để xem mức nào chạm x5 và drawdown ra sao.
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.backtest.broker import TradeBroker
from src.backtest.engine import BacktestResult, CostConfig
from src.backtest.metrics import compute, report
from src.data.loader import load, pip_size
from src.strategies.price_action_sr import (PAParams, PriceActionSR,
                                            d1_trend_from, map_d1_to_h4)

SYMBOL = "EURUSD"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--equity", type=float, default=10_000.0)
    p.add_argument("--risks", default="0.01,0.02,0.03,0.05,0.08,0.12")
    p.add_argument("--tp-atr", type=float, default=0.75)
    p.add_argument("--sl-atr", type=float, default=2.5)
    p.add_argument("--mode", default="trend")
    p.add_argument("--min-touches", type=int, default=2)
    p.add_argument("--split", type=float, default=0.7)
    p.add_argument("--out", default="results/eurusd_x5.png")
    return p.parse_args()


def seg(res, lo, hi):
    eq = res.equity.loc[lo:hi]
    tr = res.trades
    if not tr.empty:
        tr = tr[(tr["exit_time"] >= lo) & (tr["exit_time"] < hi)].reset_index(drop=True)
    return BacktestResult(eq, eq.pct_change().fillna(0.0),
                          res.position.loc[lo:hi], tr, float(eq.iloc[0]), res.meta)


def main():
    args = parse_args()
    print(f"Tải + sinh tín hiệu {SYMBOL} ({args.start}..{args.end})...")
    df = load(SYMBOL, "H4", args.start, args.end)
    df_d1 = load(SYMBOL, "D1", args.start, args.end)
    trend = map_d1_to_h4(d1_trend_from(df_d1, 50), df.index)
    params = PAParams(exit_mode="atr", min_rr=0.0, tp_atr=args.tp_atr,
                      sl_atr=args.sl_atr, mode=args.mode, min_touches=args.min_touches)
    setups = PriceActionSR(params).generate_setups(df, trend)
    pip = pip_size(SYMBOL)
    print(f"-> {len(df)} nến, {len(setups)} setup "
          f"(tp={args.tp_atr} sl={args.sl_atr} {args.mode} touch={args.min_touches})\n")

    risks = [float(x) for x in args.risks.split(",")]
    print(f"{'risk':>6} | {'return':>10} | {'x lần':>6} | {'CAGR':>7} | "
          f"{'winrate':>7} | {'maxDD':>7} | {'PF':>5} | lệnh")
    print("-" * 74)
    best = None
    for r in risks:
        broker = TradeBroker(SYMBOL, pip, args.equity, risk_pct=r, costs=CostConfig())
        res = broker.run(df, setups)
        m = compute(res)
        x = m["final_equity"] / args.equity
        print(f"{r*100:5.0f}% | {m['total_return']*100:+9.0f}% | {x:5.1f}x | "
              f"{m['cagr']*100:+6.1f}% | {m['win_rate']*100:6.1f}% | "
              f"{m['max_drawdown']*100:6.1f}% | {m['profit_factor']:4.2f} | {m['n_trades']}")
        if x >= 5.0 and (best is None or r < best[0]):
            best = (r, x, res)
    if best is None:  # chưa cặp nào đạt x5 -> lấy risk cao nhất
        best = (r, x, res)

    r, x, res = best
    print(f"\n>>> Risk {r*100:.0f}%/lệnh: {x:.1f}x. Chi tiết IS/OOS:")
    cut = res.equity.index[int(len(res.equity) * args.split)]
    print(report(compute(seg(res, res.equity.index[0], cut)), "IN-SAMPLE"))
    print(report(compute(seg(res, cut, res.equity.index[-1] + pd.Timedelta(seconds=1))),
                 "OUT-OF-SAMPLE"))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(res.equity.index, res.equity.values, lw=1.0)
    ax.axhline(args.equity, color="gray", ls=":", lw=0.8)
    ax.axhline(args.equity * 5, color="green", ls="--", lw=1, label="mốc x5")
    ax.set_yscale("log")
    ax.set_title(f"{SYMBOL} H4 — risk {r*100:.0f}%/lệnh — {x:.1f}x — winrate {compute(res)['win_rate']*100:.0f}%")
    ax.set_ylabel("Equity ($, log)"); ax.legend()
    fig.tight_layout(); fig.savefig(args.out, dpi=110)
    print(f"\nĐã lưu {args.out}")


if __name__ == "__main__":
    main()
