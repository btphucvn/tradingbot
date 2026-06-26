#!/usr/bin/env python3
"""Ghép TREND (breakout) + MEAN-REVERSION (RSI) trên GBP/JPY.

Giả thuyết: 2 chiến thuật ngược pha -> drawdown triệt tiêu -> Calmar tăng.
Chạy mỗi hệ trên 1/2 vốn, cộng equity, đo Calmar gộp + tương quan lợi nhuận tháng.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from run_pair import quote_to_usd_series
from src.backtest.broker import CostConfig, TradeBroker
from src.data.loader import load, pip_size
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr
from src.strategies.meanrev import MeanRevParams, MeanReversion
from src.strategies.price_action_sr import d1_trend_from, map_d1_to_h4

SYM, START, END = "GBPJPY", "2010-01-01", "2024-01-01"


def metrics(eq, init):
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 24 * 3600)
    cagr = (eq.iloc[-1] / init) ** (1 / years) - 1
    dd = (eq / eq.cummax() - 1).min()
    return cagr, dd, (cagr / abs(dd) if dd < 0 else float("nan"))


def main():
    df = load(SYM, "H4", START, END)
    df_d1 = load(SYM, "D1", START, END)
    trend = map_d1_to_h4(d1_trend_from(df_d1, 50), df.index)
    q = quote_to_usd_series(SYM, df, START, END)
    a_arr = atr(df, 14).to_numpy()
    pip = pip_size(SYM)

    tr_setups = BreakoutTrend(BreakoutParams(5, 14, 3.0, 5.0, False)).generate_setups(df, trend)

    # 1) Tìm MR standalone tạm ổn (quét nhanh)
    print("--- Mean-Reversion standalone (risk 2%) ---")
    print(f"{'rsi':>3} {'tp':>4} {'sl':>4} | {'CAGR':>6} {'DD':>7} {'Calmar':>6} {'n':>5}")
    best_mr, best_cal = None, -9
    for ob, tp, sl in itertools.product([(25, 75), (30, 70)], [1.0, 1.5, 2.0], [1.5, 2.0, 3.0]):
        mp = MeanRevParams(oversold=ob[0], overbought=ob[1], tp_atr=tp, sl_atr=sl)
        s = MeanReversion(mp).generate_setups(df)
        if len(s) < 200:
            continue
        res = TradeBroker(SYM, pip, 10_000.0, risk_pct=0.02, costs=CostConfig()).run(df, s, q, a_arr)
        cg, dd, cal = metrics(res.equity, 10_000.0)
        print(f"{ob[0]:3.0f} {tp:4.1f} {sl:4.1f} | {cg*100:5.1f}% {dd*100:6.1f}% {cal:6.2f} {len(s):5d}")
        if cal > best_cal:
            best_cal, best_mr = cal, (mp, s)

    mp, mr_setups = best_mr
    print(f"\nMR tốt nhất: oversold={mp.oversold} tp={mp.tp_atr} sl={mp.sl_atr}")

    # 2) Tương quan lợi nhuận tháng giữa trend và MR
    tr_eq = TradeBroker(SYM, pip, 5_000.0, 0.02, costs=CostConfig()).run(df, tr_setups, q, a_arr).equity
    mr_eq = TradeBroker(SYM, pip, 5_000.0, 0.02, costs=CostConfig()).run(df, mr_setups, q, a_arr).equity
    tr_m = tr_eq.resample("ME").last().pct_change().dropna()
    mr_m = mr_eq.resample("ME").last().pct_change().dropna()
    corr = tr_m.corr(mr_m)
    print(f"\nTương quan lợi nhuận THÁNG (trend vs MR): {corr:+.2f}  "
          f"({'NGƯỢC pha tốt' if corr < 0.2 else 'tương quan cao - ít lợi ích'})")

    # 3) Ghép trend+MR ở nhiều risk, so với trend-alone
    print(f"\n--- GHÉP trend(1/2) + MR(1/2) vs TREND-alone ---")
    print(f"{'risk':>5} | {'TREND CAGR/DD/Calmar':>24} | {'GHÉP CAGR/DD/Calmar':>24}")
    for r in [0.02, 0.03, 0.05, 0.08]:
        tr_full = TradeBroker(SYM, pip, 10_000.0, r, costs=CostConfig()).run(df, tr_setups, q, a_arr).equity
        cg_t, dd_t, cal_t = metrics(tr_full, 10_000.0)
        e_tr = TradeBroker(SYM, pip, 5_000.0, r, costs=CostConfig()).run(df, tr_setups, q, a_arr).equity
        e_mr = TradeBroker(SYM, pip, 5_000.0, r, costs=CostConfig()).run(df, mr_setups, q, a_arr).equity
        comb = pd.concat([e_tr, e_mr], axis=1).ffill().fillna(5_000.0).sum(axis=1)
        cg_c, dd_c, cal_c = metrics(comb, 10_000.0)
        print(f"{r*100:4.0f}% | {cg_t*100:6.1f}% {dd_t*100:6.1f}% {cal_t:5.2f}      | "
              f"{cg_c*100:6.1f}% {dd_c*100:6.1f}% {cal_c:5.2f}")


if __name__ == "__main__":
    main()
