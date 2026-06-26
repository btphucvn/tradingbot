#!/usr/bin/env python3
"""Quét tham số breakout trên GBP/JPY để tìm TRẦN tăng trưởng thật (ở risk 2%)."""

from __future__ import annotations

import itertools

from run_pair import quote_to_usd_series
from src.backtest.broker import CostConfig, TradeBroker
from src.backtest.metrics import compute
from src.data.loader import load, pip_size
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr
from src.strategies.price_action_sr import d1_trend_from, map_d1_to_h4

SYM, START, END = "GBPJPY", "2010-01-01", "2024-01-01"


def main():
    df = load(SYM, "H4", START, END)
    df_d1 = load(SYM, "D1", START, END)
    trend = map_d1_to_h4(d1_trend_from(df_d1, 50), df.index)
    q = quote_to_usd_series(SYM, df, START, END)
    a_arr = atr(df, 14).to_numpy()
    pip = pip_size(SYM)

    # Thêm tp1 (chốt một phần) để đẩy winrate lên >50% trong khi giữ đuôi trend.
    grid = itertools.product([20, 40], [2.0, 3.0], [3.0, 5.0],
                             [0.0, 1.0, 1.5, 2.0], [0.5, 0.6])
    rows = []
    print(f"{'entry':>5} {'sl':>4} {'trail':>5} {'tp1':>4} {'frac':>4} | {'x':>5} {'win%':>6} {'PF':>5} {'maxDD':>7} {'n':>5}")
    print("-" * 64)
    for entry, sl, trail, tp1, frac in grid:
        params = BreakoutParams(entry_period=entry, sl_atr=sl, trail_atr=trail,
                                use_trend=True, tp1_atr=tp1, tp1_frac=frac)
        setups = BreakoutTrend(params).generate_setups(df, trend)
        if not setups:
            continue
        res = TradeBroker(SYM, pip, 10_000.0, risk_pct=0.02, costs=CostConfig()).run(df, setups, q, a_arr)
        m = compute(res)
        x = m["final_equity"] / 10_000.0
        rows.append((entry, sl, trail, tp1, frac, x, m["win_rate"], m["profit_factor"], m["max_drawdown"], m["n_trades"]))
        print(f"{entry:5d} {sl:4.1f} {trail:5.1f} {tp1:4.1f} {frac:4.1f} | {x:4.1f}x {m['win_rate']*100:5.1f}% "
              f"{m['profit_factor']:4.2f} {m['max_drawdown']*100:6.1f}% {m['n_trades']:5d}")

    print("\n===== TOP theo x trong nhóm winrate>50% (risk 2%) =====")
    cands = [r for r in rows if r[6] > 0.50]
    cands.sort(key=lambda r: r[5], reverse=True)
    for r in cands[:8]:
        print(f"entry={r[0]} sl={r[1]} trail={r[2]} tp1={r[3]} frac={r[4]} -> {r[5]:.1f}x, "
              f"winrate {r[6]*100:.0f}%, PF {r[7]:.2f}, DD {r[8]*100:.0f}%")
    if not cands:
        print("(không có cấu hình nào winrate>50%)")


if __name__ == "__main__":
    main()
