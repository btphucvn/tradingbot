#!/usr/bin/env python3
"""Phép thử cuối: GBP/JPY có chạm x5 bằng BẤT KỲ cấu hình breakout nào không?

Bỏ ràng buộc winrate. Tối đa hóa x (vốn cuối / vốn đầu), điều kiện >=200 lệnh.
Quét cả risk. In top theo x kèm drawdown để thấy giá phải trả.
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

    setup_grid = itertools.product([5, 10, 20, 40], [1.5, 2.0, 3.0],
                                   [3.0, 5.0, 8.0], [True, False])
    risks = [0.02, 0.03, 0.05]
    rows = []
    print("Đang quét (mỗi dòng = cấu hình tốt nhất theo risk)...")
    for entry, sl, trail, ut in setup_grid:
        params = BreakoutParams(entry_period=entry, sl_atr=sl, trail_atr=trail, use_trend=ut)
        setups = BreakoutTrend(params).generate_setups(df, trend)
        if len(setups) < 200:
            continue
        for r in risks:
            res = TradeBroker(SYM, pip, 10_000.0, risk_pct=r, costs=CostConfig()).run(df, setups, q, a_arr)
            m = compute(res)
            if m["n_trades"] < 200:
                continue
            x = m["final_equity"] / 10_000.0
            rows.append((entry, sl, trail, ut, r, x, m["win_rate"], m["profit_factor"],
                         m["max_drawdown"], m["n_trades"]))

    rows.sort(key=lambda r: r[5], reverse=True)
    print(f"\n===== TOP theo x (>=200 lệnh) =====")
    print(f"{'entry':>5} {'sl':>4} {'trail':>5} {'trend':>5} {'risk':>5} | "
          f"{'x':>6} {'win%':>6} {'PF':>5} {'maxDD':>7} {'n':>5}")
    for r in rows[:15]:
        print(f"{r[0]:5d} {r[1]:4.1f} {r[2]:5.1f} {str(r[3]):>5} {r[4]*100:4.0f}% | "
              f"{r[5]:5.1f}x {r[6]*100:5.1f}% {r[7]:4.2f} {r[8]*100:6.1f}% {r[9]:5d}")
    best = rows[0]
    print(f"\n>>> x cao nhất: {best[5]:.1f}x "
          f"(entry={best[0]} sl={best[1]} trail={best[2]} trend={best[3]} risk={best[4]*100:.0f}%) "
          f"| winrate {best[6]*100:.0f}%, DD {best[8]*100:.0f}%, {best[9]} lệnh")
    print(f">>> Đạt x5? {'CÓ' if best[5] >= 5.0 else 'KHÔNG'}")


if __name__ == "__main__":
    main()
