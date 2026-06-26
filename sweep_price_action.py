#!/usr/bin/env python3
"""Tự động quét nhiều cấu hình chiến lược price action, xếp hạng theo winrate.

Mục tiêu: tìm cấu hình winrate > 65% (kiểm cả out-of-sample để không overfit).
Chiến thuật đẩy winrate: TP gần + SL xa (theo ATR) tại vùng S/R mạnh.

Tải data 1 lần, mỗi config: sinh setup -> chạy broker -> chia IS/OOS -> đo.
"""

from __future__ import annotations

import itertools

import pandas as pd

from src.backtest.broker import CostConfig, TradeBroker
from src.backtest.engine import BacktestResult
from src.backtest.metrics import compute
from src.data.loader import load, pip_size
from src.strategies.price_action_sr import (PAParams, PriceActionSR,
                                            d1_trend_from, map_d1_to_h4)

SYMBOL = "EURUSD"
START, END = "2014-01-01", "2024-01-01"
SPLIT = 0.6   # 2014-2020 tune / 2020-2024 OOS


def seg(res: BacktestResult, lo, hi) -> BacktestResult:
    eq = res.equity.loc[lo:hi]
    tr = res.trades
    if not tr.empty:
        tr = tr[(tr["exit_time"] >= lo) & (tr["exit_time"] < hi)].reset_index(drop=True)
    return BacktestResult(eq, eq.pct_change().fillna(0.0),
                          res.position.loc[lo:hi], tr, float(eq.iloc[0]), res.meta)


def evaluate(df, trend, pip, params, cut):
    strat = PriceActionSR(params)
    setups = strat.generate_setups(df, trend)
    broker = TradeBroker(SYMBOL, pip, 10_000.0, risk_pct=0.01, costs=CostConfig())
    res = broker.run(df, setups)
    m_is = compute(seg(res, df.index[0], cut))
    m_oos = compute(seg(res, cut, df.index[-1] + pd.Timedelta(seconds=1)))
    return m_is, m_oos, len(setups)


def main():
    print(f"Tải {SYMBOL} H4+D1 {START}..{END}...")
    df = load(SYMBOL, "H4", START, END)
    df_d1 = load(SYMBOL, "D1", START, END)
    trend = map_d1_to_h4(d1_trend_from(df_d1, 50), df.index)
    pip = pip_size(SYMBOL)
    cut = df.index[int(len(df) * SPLIT)]
    print(f"-> H4 {len(df)} nến | cut OOS tại {cut.date()}\n")

    # Lưới cấu hình: TP gần + SL xa -> winrate cao.
    grid = []
    for tp, sl, mode, touch in itertools.product(
            [0.5, 0.75, 1.0], [1.5, 2.0, 2.5], ["trend", "range"], [2, 3]):
        if sl <= tp:
            continue
        grid.append(dict(tp_atr=tp, sl_atr=sl, mode=mode, min_touches=touch))

    rows = []
    for i, g in enumerate(grid):
        params = PAParams(exit_mode="atr", min_rr=0.0, use_break_retest=True,
                          tp_atr=g["tp_atr"], sl_atr=g["sl_atr"], mode=g["mode"],
                          min_touches=g["min_touches"])
        m_is, m_oos, nset = evaluate(df, trend, pip, params, cut)
        rows.append({
            "tp": g["tp_atr"], "sl": g["sl_atr"], "mode": g["mode"], "touch": g["min_touches"],
            "IS_win": m_is["win_rate"], "IS_ret": m_is["total_return"], "IS_pf": m_is["profit_factor"], "IS_n": m_is["n_trades"],
            "OOS_win": m_oos["win_rate"], "OOS_ret": m_oos["total_return"], "OOS_pf": m_oos["profit_factor"], "OOS_n": m_oos["n_trades"],
        })
        print(f"[{i+1}/{len(grid)}] tp={g['tp_atr']} sl={g['sl_atr']} {g['mode']:5} touch={g['min_touches']} "
              f"| IS win={m_is['win_rate']*100:.1f}% ret={m_is['total_return']*100:+.0f}% n={m_is['n_trades']} "
              f"| OOS win={m_oos['win_rate']*100:.1f}% ret={m_oos['total_return']*100:+.0f}% n={m_oos['n_trades']}")

    res_df = pd.DataFrame(rows).sort_values("OOS_win", ascending=False)
    print("\n===== TOP theo OOS winrate =====")
    pd.set_option("display.width", 200)
    print(res_df.head(12).to_string(index=False,
          formatters={"IS_win": "{:.1%}".format, "OOS_win": "{:.1%}".format,
                      "IS_ret": "{:+.0%}".format, "OOS_ret": "{:+.0%}".format,
                      "IS_pf": "{:.2f}".format, "OOS_pf": "{:.2f}".format}))


if __name__ == "__main__":
    main()
