#!/usr/bin/env python3
"""Đánh giá edge TỪNG thị trường (cùng chiến thuật breakout, risk 2%) để chọn rổ."""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import pandas as pd
from run_portfolio import load_h4_safe, quote_to_usd, metrics, MARKETS_WIDE
from src.backtest.broker import CostConfig, TradeBroker
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr
from src.backtest.metrics import compute

START, END = "2010-01-01", "2024-01-01"
params = BreakoutParams(entry_period=5, sl_atr=3.0, trail_atr=5.0, use_trend=False)

print(f"{'market':>8} | {'CAGR':>6} {'DD':>7} {'Calmar':>6} {'PF':>5} {'n':>5} {'từ năm':>7}")
print("-" * 58)
rows = []
for sym in MARKETS_WIDE:
    df = load_h4_safe(sym, START, END)
    setups = BreakoutTrend(params).generate_setups(df, pd.Series(0, index=df.index))
    q = quote_to_usd(sym, df, START, END)
    res = TradeBroker(sym, 0.01 if "JPY" in sym else 0.0001, 10_000.0, risk_pct=0.02,
                      costs=CostConfig()).run(df, setups, q, atr(df, 14).to_numpy())
    m = compute(res)
    _, cg, dd, cal = metrics(res.equity, 10_000.0)
    rows.append((sym, cg, dd, cal, m["profit_factor"], m["n_trades"]))
    print(f"{sym:>8} | {cg*100:5.1f}% {dd*100:6.1f}% {cal:6.2f} {m['profit_factor']:4.2f} "
          f"{m['n_trades']:5d} {df.index[0].year:>7}")

print("\nThị trường có EDGE (PF>1.05), sắp theo Calmar:")
for r in sorted([r for r in rows if r[4] > 1.05], key=lambda r: r[3], reverse=True):
    print(f"  {r[0]:>8}  Calmar {r[3]:.2f}  PF {r[4]:.2f}  CAGR {r[1]*100:.0f}%")
