#!/usr/bin/env python3
"""Quét bộ lọc edge cho breakout GBP/JPY: tìm PF > 1.27 và Calmar tốt hơn.

Giữ base entry5/sl3/trail5 (đã chứng minh), thử thêm:
  - lọc phiên London/NY (6-22h UTC)
  - ATR đang tăng (biến động nở)
  - breakout mạnh (phá kênh thêm buffer*ATR)
Đo ở risk 3% để so CAGR/DD; PF là thước đo edge.
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

    grid = itertools.product(
        [(0, 24), (6, 22)],     # session
        [0, 6],                 # atr_rising_k
        [0.0, 0.25, 0.5],       # breakout_buffer
    )
    rows = []
    print(f"{'session':>9} {'atrUp':>5} {'buf':>5} | {'CAGR':>6} {'PF':>5} {'maxDD':>7} "
          f"{'Calmar':>6} {'win%':>6} {'n':>5}")
    print("-" * 62)
    for (ss, se), ak, buf in grid:
        params = BreakoutParams(entry_period=5, sl_atr=3.0, trail_atr=5.0, use_trend=False,
                                session_start=ss, session_end=se, atr_rising_k=ak,
                                breakout_buffer=buf)
        setups = BreakoutTrend(params).generate_setups(df, trend)
        if len(setups) < 200:
            continue
        res = TradeBroker(SYM, pip, 10_000.0, risk_pct=0.03, costs=CostConfig()).run(df, setups, q, a_arr)
        m = compute(res)
        if m["n_trades"] < 200:
            continue
        rows.append((f"{ss}-{se}", ak, buf, m["cagr"], m["profit_factor"],
                     m["max_drawdown"], m["calmar"], m["win_rate"], m["n_trades"]))
        print(f"{ss:2d}-{se:<2d}     {ak:5d} {buf:5.2f} | {m['cagr']*100:5.1f}% {m['profit_factor']:4.2f} "
              f"{m['max_drawdown']*100:6.1f}% {m['calmar']:6.2f} {m['win_rate']*100:5.1f}% {m['n_trades']:5d}")

    print("\n===== Sắp theo PF (edge) =====")
    for r in sorted(rows, key=lambda r: r[4], reverse=True)[:6]:
        print(f"session={r[0]} atrUp={r[1]} buf={r[2]} -> PF {r[4]:.2f}, CAGR {r[3]*100:.0f}%, "
              f"DD {r[5]*100:.0f}%, Calmar {r[6]:.2f}, {r[8]} lệnh")
    print("\n===== Sắp theo Calmar (CAGR/DD) =====")
    for r in sorted(rows, key=lambda r: r[6], reverse=True)[:6]:
        print(f"session={r[0]} atrUp={r[1]} buf={r[2]} -> Calmar {r[6]:.2f}, PF {r[4]:.2f}, "
              f"CAGR {r[3]*100:.0f}%, DD {r[5]*100:.0f}%, {r[8]} lệnh")
    print(f"\n(Base không lọc: PF 1.22, CAGR 20%, DD -56%, Calmar ~0.36)")


if __name__ == "__main__":
    main()
