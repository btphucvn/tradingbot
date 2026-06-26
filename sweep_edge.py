#!/usr/bin/env python3
"""Săn cấu hình EURUSD có EDGE THẬT (không chỉ winrate hình học).

Edge = winrate quan sát - baseline hình học sl/(tp+sl). Edge > 0 đáng kể nghĩa là
tín hiệu (S/R + price action + trend) thực sự đoán hướng tốt hơn ngẫu nhiên ->
expectancy dương -> có thể compound tới mục tiêu cao.

Đo ở risk 1% (cố định) để so expectancy giữa các cấu hình. Sắp theo total_return.
"""

from __future__ import annotations

import itertools

from src.backtest.broker import CostConfig, TradeBroker
from src.backtest.metrics import compute
from src.data.loader import load, pip_size
from src.strategies.price_action_sr import (PAParams, PriceActionSR,
                                            d1_trend_from, map_d1_to_h4)

SYMBOL = "EURUSD"
START, END = "2010-01-01", "2024-01-01"


def main():
    print(f"Tải {SYMBOL} H4+D1...")
    df = load(SYMBOL, "H4", START, END)
    df_d1 = load(SYMBOL, "D1", START, END)
    pip = pip_size(SYMBOL)

    rows = []
    grid = list(itertools.product(
        [0.5, 1.0, 1.5, 2.0],          # tp_atr
        [1.0, 1.5, 2.0, 2.5],          # sl_atr
        ["trend", "range"],            # mode
        [2],                           # min_touches
        [50],                          # ema D1
    ))
    print(f"Quét {len(grid)} cấu hình (risk 1%)...\n")
    print(f"{'tp':>4} {'sl':>4} {'mode':>5} {'tch':>3} {'ema':>4} | "
          f"{'win%':>6} {'geo%':>6} {'edge':>6} | {'ret':>7} {'PF':>5} {'n':>5}")
    print("-" * 70)

    trend_cache = {}
    for tp, sl, mode, touch, ema in grid:
        if ema not in trend_cache:
            trend_cache[ema] = map_d1_to_h4(d1_trend_from(df_d1, ema), df.index)
        trend = trend_cache[ema]
        params = PAParams(exit_mode="atr", min_rr=0.0, tp_atr=tp, sl_atr=sl,
                          mode=mode, min_touches=touch)
        setups = PriceActionSR(params).generate_setups(df, trend)
        if not setups:
            continue
        res = TradeBroker(SYMBOL, pip, 10_000.0, risk_pct=0.01,
                          costs=CostConfig()).run(df, setups)
        m = compute(res)
        geo = sl / (tp + sl)
        edge = m["win_rate"] - geo
        rows.append((tp, sl, mode, touch, ema, m["win_rate"], geo, edge,
                     m["total_return"], m["profit_factor"], m["n_trades"]))
        print(f"{tp:4.2f} {sl:4.2f} {mode:>5} {touch:3d} {ema:4d} | "
              f"{m['win_rate']*100:5.1f}% {geo*100:5.1f}% {edge*100:+5.1f}% | "
              f"{m['total_return']*100:+6.0f}% {m['profit_factor']:4.2f} {m['n_trades']:5d}")

    rows.sort(key=lambda r: r[8], reverse=True)
    print("\n===== TOP theo total_return (winrate>60%) =====")
    print(f"{'tp':>4} {'sl':>4} {'mode':>5} {'tch':>3} {'ema':>4} | {'win%':>6} {'edge':>6} {'ret':>7} {'PF':>5}")
    for r in rows:
        if r[5] > 0.60:
            print(f"{r[0]:4.2f} {r[1]:4.2f} {r[2]:>5} {r[3]:3d} {r[4]:4d} | "
                  f"{r[5]*100:5.1f}% {r[7]*100:+5.1f}% {r[8]*100:+6.0f}% {r[9]:4.2f}")


if __name__ == "__main__":
    main()
