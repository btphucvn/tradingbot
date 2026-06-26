#!/usr/bin/env python3
"""Tìm trên GBP/JPY: CAGR cao nhất GIỮ drawdown < 40%, và Calmar tối đa.

Quét entry/sl/trail × risk (no-trend, đã chứng minh tốt nhất). >=200 lệnh.
Mục tiêu user: CAGR>35% & DD<40% (Calmar>0.88).
"""

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

    setup_grid = itertools.product([5, 10, 20, 40], [1.5, 2.0, 3.0], [3.0, 5.0, 8.0])
    risks = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
    rows = []
    for entry, sl, trail in setup_grid:
        params = BreakoutParams(entry_period=entry, sl_atr=sl, trail_atr=trail, use_trend=False)
        setups = BreakoutTrend(params).generate_setups(df, trend)
        if len(setups) < 200:
            continue
        for r in risks:
            res = TradeBroker(SYM, pip, 10_000.0, risk_pct=r, costs=CostConfig()).run(df, setups, q, a_arr)
            m = compute(res)
            if m["n_trades"] < 200:
                continue
            rows.append((entry, sl, trail, r, m["cagr"], m["max_drawdown"],
                         m["calmar"], m["profit_factor"], m["n_trades"]))

    # 1) CAGR cao nhất GIỮ DD < 40%
    dd_ok = [x for x in rows if x[5] > -0.40]
    dd_ok.sort(key=lambda x: x[4], reverse=True)
    print("===== CAGR cao nhất với DD < 40% =====")
    print(f"{'entry':>5} {'sl':>4} {'trail':>5} {'risk':>5} | {'CAGR':>6} {'DD':>7} {'Calmar':>6} {'PF':>5} {'n':>5}")
    for x in dd_ok[:8]:
        print(f"{x[0]:5d} {x[1]:4.1f} {x[2]:5.1f} {x[3]*100:4.1f}% | {x[4]*100:5.1f}% "
              f"{x[5]*100:6.1f}% {x[6]:6.2f} {x[7]:4.2f} {x[8]:5d}")

    # 2) Calmar cao nhất tổng thể
    rows.sort(key=lambda x: x[6], reverse=True)
    print("\n===== Calmar (CAGR/DD) cao nhất tổng thể =====")
    for x in rows[:8]:
        print(f"entry={x[0]} sl={x[1]} trail={x[2]} risk={x[3]*100:.1f}% -> Calmar {x[6]:.2f}, "
              f"CAGR {x[4]*100:.0f}%, DD {x[5]*100:.0f}%, PF {x[7]:.2f}")

    best = dd_ok[0] if dd_ok else None
    print("\n>>> Mục tiêu CAGR>35% & DD<40%:",
          "ĐẠT" if (best and best[4] > 0.35) else "KHÔNG ĐẠT")
    if best:
        print(f"    CAGR cao nhất khi giữ DD<40% = {best[4]*100:.1f}% (DD {best[5]*100:.0f}%)")


if __name__ == "__main__":
    main()
