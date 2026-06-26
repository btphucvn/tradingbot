#!/usr/bin/env python3
"""Backtest chiến lược price action S/R trên H4, lọc trend D1.

Ví dụ:
    .venv/bin/python run_price_action.py --symbol EURUSD \
        --start 2010-01-01 --end 2024-01-01

Chạy 1 backtest trên TOÀN BỘ giai đoạn (giữ liên tục lịch sử vùng S/R), rồi
chia kết quả thành in-sample / out-of-sample để báo cáo riêng. Out-of-sample
là thước đo thật.
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
from src.strategies.indicators import atr
from src.strategies.levels import active_zones_at, find_pivots
from src.strategies.price_action_sr import (PAParams, PriceActionSR,
                                            d1_trend_from, map_d1_to_h4)


def parse_args():
    p = argparse.ArgumentParser(description="Backtest price action S/R (H4)")
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--interval", default="H4")
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--equity", type=float, default=10_000.0)
    p.add_argument("--risk", type=float, default=0.01, help="rủi ro mỗi lệnh (vd 0.01=1%)")
    p.add_argument("--split", type=float, default=0.7, help="tỉ lệ in-sample")
    p.add_argument("--ema", type=int, default=50, help="EMA D1 lọc trend")
    p.add_argument("--no-reversal", action="store_true")
    p.add_argument("--no-break-retest", action="store_true")
    p.add_argument("--exit-mode", default="zone", choices=["zone", "atr"])
    p.add_argument("--tp-atr", type=float, default=1.0)
    p.add_argument("--sl-atr", type=float, default=0.0)
    p.add_argument("--mode", default="trend", choices=["trend", "range", "both"])
    p.add_argument("--min-touches", type=int, default=2)
    p.add_argument("--min-rr", type=float, default=1.5)
    p.add_argument("--equity-out", default="results/pa_equity.png")
    p.add_argument("--levels-out", default="results/pa_levels.png")
    return p.parse_args()


def segment(res: BacktestResult, lo, hi) -> BacktestResult:
    """Trích một đoạn thời gian [lo, hi) từ kết quả full để báo cáo riêng."""
    eq = res.equity.loc[lo:hi]
    pos = res.position.loc[lo:hi]
    tr = res.trades
    if not tr.empty:
        tr = tr[(tr["exit_time"] >= lo) & (tr["exit_time"] < hi)].reset_index(drop=True)
    return BacktestResult(
        equity=eq, returns=eq.pct_change().fillna(0.0), position=pos,
        trades=tr, initial_equity=float(eq.iloc[0]), meta=res.meta,
    )


def plot_levels(df, res, symbol, path, window=400):
    """Vẽ giá + vùng S/R (tại nến cuối) + điểm vào/ra trong cửa sổ gần nhất."""
    sub = df.iloc[-window:]
    a = atr(df, 14)
    pivots = find_pivots(df, 3, 3)
    t = len(df) - 1
    tol = 0.5 * float(a.iloc[t])
    zones = active_zones_at(pivots, t, tol, lookback=250, min_touches=2)

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(sub.index, sub["close"], lw=0.8, color="black", label="close")
    lo, hi = sub["low"].min(), sub["high"].max()
    for z in zones:
        if lo <= z.price <= hi:
            ax.axhspan(z.lower, z.upper, color="steelblue", alpha=0.12)
            ax.axhline(z.price, color="steelblue", lw=0.6, alpha=0.5)

    if not res.trades.empty:
        tr = res.trades
        tr = tr[tr["entry_time"] >= sub.index[0]]
        for _, r in tr.iterrows():
            col = "green" if r["dir"] > 0 else "red"
            mk = "^" if r["dir"] > 0 else "v"
            ax.scatter(r["entry_time"], r["entry_price"], marker=mk, color=col, s=40, zorder=5)
            xcol = "blue" if r["pnl"] > 0 else "gray"
            ax.scatter(r["exit_time"], r["exit_price"], marker="x", color=xcol, s=30, zorder=5)

    ax.set_title(f"{symbol} H4 — vùng S/R + lệnh ({window} nến gần nhất)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    args = parse_args()

    print(f"Tải {args.symbol} H4 + D1 ({args.start}..{args.end})...")
    df = load(args.symbol, args.interval, args.start, args.end)
    df_d1 = load(args.symbol, "D1", args.start, args.end)
    print(f"-> H4: {len(df)} nến | D1: {len(df_d1)} nến")

    trend = map_d1_to_h4(d1_trend_from(df_d1, args.ema), df.index)
    params = PAParams(use_reversal=not args.no_reversal,
                      use_break_retest=not args.no_break_retest,
                      exit_mode=args.exit_mode, tp_atr=args.tp_atr, sl_atr=args.sl_atr,
                      mode=args.mode, min_touches=args.min_touches, min_rr=args.min_rr)
    strat = PriceActionSR(params)

    print("Sinh tín hiệu (quét vùng S/R từng nến)...")
    setups = strat.generate_setups(df, trend)
    print(f"-> {len(setups)} setup.")

    broker = TradeBroker(args.symbol, pip_size(args.symbol),
                         initial_equity=args.equity, risk_pct=args.risk,
                         costs=CostConfig())
    res = broker.run(df, setups)

    cut = df.index[int(len(df) * args.split)]
    res_is = segment(res, df.index[0], cut)
    res_oos = segment(res, cut, df.index[-1] + pd.Timedelta(seconds=1))

    print(report(compute(res_is), "IN-SAMPLE"))
    print(report(compute(res_oos), "OUT-OF-SAMPLE (thước đo thật)"))
    print(report(compute(res), "TOÀN BỘ"))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(res.equity.index, res.equity.values, lw=1.0)
    ax.axvline(cut, color="red", ls="--", lw=1, label="bắt đầu out-of-sample")
    ax.axhline(args.equity, color="gray", ls=":", lw=0.8)
    ax.set_title(f"{args.symbol} H4 Price-Action S/R — risk {args.risk*100:.1f}%/lệnh")
    ax.set_ylabel("Equity ($)"); ax.legend()
    fig.tight_layout(); fig.savefig(args.equity_out, dpi=110)
    plot_levels(df, res, args.symbol, args.levels_out)
    print(f"\nĐã lưu: {args.equity_out} và {args.levels_out}")


if __name__ == "__main__":
    main()
