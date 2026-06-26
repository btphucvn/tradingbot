#!/usr/bin/env python3
"""Ensemble đa tham số trên GBP/JPY: gộp nhiều entry period để giảm drawdown.

Ý tưởng: 3 hệ con (entry 5/10/20) vào lệnh ở thời điểm khác nhau -> equity gộp
mượt hơn -> maxDD nhỏ hơn -> Calmar cao hơn -> dùng risk cao hơn ở cùng DD ->
CAGR cao hơn. Mỗi hệ con chia 1/3 vốn, chạy độc lập, cộng equity.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from run_pair import quote_to_usd_series
from src.backtest.broker import CostConfig, TradeBroker
from src.backtest.metrics import _periods_per_year
from src.data.loader import load, pip_size
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr
from src.strategies.price_action_sr import d1_trend_from, map_d1_to_h4

SYM, START, END = "GBPJPY", "2010-01-01", "2024-01-01"
ENTRIES = [5, 10, 20]


def curve_metrics(eq: pd.Series, init: float):
    total = eq.iloc[-1] / init - 1
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 24 * 3600)
    cagr = (eq.iloc[-1] / init) ** (1 / years) - 1
    dd = (eq / eq.cummax() - 1).min()
    return total, cagr, dd


def run_one(df, setups, q, a_arr, pip, equity, risk):
    return TradeBroker(SYM, pip, equity, risk_pct=risk, costs=CostConfig()).run(df, setups, q, a_arr)


def main():
    df = load(SYM, "H4", START, END)
    df_d1 = load(SYM, "D1", START, END)
    trend = map_d1_to_h4(d1_trend_from(df_d1, 50), df.index)
    q = quote_to_usd_series(SYM, df, START, END)
    a_arr = atr(df, 14).to_numpy()
    pip = pip_size(SYM)

    setups_by_entry = {}
    for e in ENTRIES:
        p = BreakoutParams(entry_period=e, sl_atr=3.0, trail_atr=5.0, use_trend=False)
        setups_by_entry[e] = BreakoutTrend(p).generate_setups(df, trend)

    print("So sánh ĐƠN (entry=5, 1 hệ) vs ENSEMBLE (entry 5/10/20, chia 3) ở các risk:\n")
    print(f"{'risk':>5} | {'ĐƠN-CAGR':>9} {'ĐƠN-DD':>7} {'ĐƠN-Calmar':>10} | "
          f"{'ENS-CAGR':>9} {'ENS-DD':>7} {'ENS-Calmar':>10}")
    print("-" * 74)
    for risk in [0.03, 0.05, 0.08, 0.12]:
        # Đơn: entry=5, full vốn
        single = run_one(df, setups_by_entry[5], q, a_arr, pip, 10_000.0, risk)
        s_tot, s_cagr, s_dd = curve_metrics(single.equity, 10_000.0)

        # Ensemble: 3 hệ con, mỗi hệ 1/3 vốn, cộng equity
        sub_eqs = []
        for e in ENTRIES:
            r = run_one(df, setups_by_entry[e], q, a_arr, pip, 10_000.0 / 3, risk)
            sub_eqs.append(r.equity)
        ens_eq = pd.concat(sub_eqs, axis=1).ffill().fillna(10_000.0 / 3).sum(axis=1)
        e_tot, e_cagr, e_dd = curve_metrics(ens_eq, 10_000.0)

        s_cal = s_cagr / abs(s_dd) if s_dd < 0 else float("nan")
        e_cal = e_cagr / abs(e_dd) if e_dd < 0 else float("nan")
        print(f"{risk*100:4.0f}% | {s_cagr*100:8.1f}% {s_dd*100:6.1f}% {s_cal:10.2f} | "
              f"{e_cagr*100:8.1f}% {e_dd*100:6.1f}% {e_cal:10.2f}")


if __name__ == "__main__":
    main()
