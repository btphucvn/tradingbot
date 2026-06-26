#!/usr/bin/env python3
"""Chạy backtest một chiến lược trên dữ liệu Dukascopy thật.

Ví dụ:
    python run_backtest.py --symbol EURUSD --interval H1 \
        --start 2015-01-01 --end 2024-01-01

Mặc định chia dữ liệu 70% IN-SAMPLE / 30% OUT-OF-SAMPLE và báo cáo riêng
từng phần. Phần out-of-sample (chiến lược "chưa thấy") mới là thước đo thật.
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")  # không cần màn hình, lưu ra file PNG
import matplotlib.pyplot as plt

from src.backtest.engine import Backtest, CostConfig
from src.backtest.metrics import compute, report
from src.data.loader import load, pip_size
from src.strategies.donchian import DonchianBreakout


def parse_args():
    p = argparse.ArgumentParser(description="Backtest forex trên data Dukascopy")
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--interval", default="H1")
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--equity", type=float, default=10_000.0)
    p.add_argument("--leverage", type=float, default=3.0)
    p.add_argument("--entry", type=int, default=20, help="Donchian entry period")
    p.add_argument("--exit", type=int, default=10, help="Donchian exit period")
    p.add_argument("--split", type=float, default=0.7, help="tỉ lệ in-sample")
    p.add_argument("--no-short", action="store_true", help="chỉ giao dịch long")
    p.add_argument("--out", default="results/equity.png")
    return p.parse_args()


def run_segment(df, strat, symbol, equity, leverage, costs, title):
    bt = Backtest(symbol, pip_size(symbol), equity, leverage, costs)
    signal = strat.generate_signal(df)
    result = bt.run(df, signal)
    metrics = compute(result)
    print(report(metrics, title))
    return result


def main():
    args = parse_args()

    print(f"Đang tải {args.symbol} {args.interval} {args.start}..{args.end} từ Dukascopy...")
    df = load(args.symbol, args.interval, args.start, args.end)
    print(f"-> {len(df)} bars.")

    strat = DonchianBreakout(args.entry, args.exit, allow_short=not args.no_short)
    costs = CostConfig()  # dùng spread thật trong data

    # Chia in-sample / out-of-sample theo thời gian.
    cut = int(len(df) * args.split)
    df_is, df_oos = df.iloc[:cut], df.iloc[cut:]

    print(f"\nChiến lược: Donchian({args.entry}/{args.exit})"
          f"{' [long-only]' if args.no_short else ''} | leverage={args.leverage}x")

    res_is = run_segment(df_is, strat, args.symbol, args.equity,
                         args.leverage, costs, "IN-SAMPLE (tối ưu/quan sát)")
    res_oos = run_segment(df_oos, strat, args.symbol, args.equity,
                          args.leverage, costs, "OUT-OF-SAMPLE (thước đo thật)")
    res_full = run_segment(df, strat, args.symbol, args.equity,
                           args.leverage, costs, "TOÀN BỘ giai đoạn")

    # Vẽ equity curve toàn kỳ + mốc chia.
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(res_full.equity.index, res_full.equity.values, lw=1.0)
    ax.axvline(df_oos.index[0], color="red", ls="--", lw=1,
               label="bắt đầu out-of-sample")
    ax.axhline(args.equity, color="gray", ls=":", lw=0.8)
    ax.set_title(f"{args.symbol} {args.interval} - Donchian({args.entry}/{args.exit})")
    ax.set_ylabel("Equity ($)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=110)
    print(f"\nĐã lưu equity curve -> {args.out}")


if __name__ == "__main__":
    main()
