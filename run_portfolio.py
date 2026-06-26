#!/usr/bin/env python3
"""Danh mục đa thị trường (CTA): cùng chiến thuật breakout trend cho 5 thị trường
ít tương quan, mỗi cái 1 sleeve vốn riêng, gộp equity -> drawdown triệt tiêu nhau.

Markets: GBP/JPY (FX), XAU/USD (vàng), WTI (dầu), S&P500 (chỉ số), Coffee (nông sản).
Lịch sử lệch nhau -> sleeve nào có data thì tham gia (trước đó giữ nguyên vốn cấp).
Dùng CÙNG tham số cho mọi thị trường (chuẩn CTA, tránh overfit).
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.broker import CostConfig, TradeBroker
from src.data.loader import load, pip_size
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr

MARKETS = ["GBPJPY", "XAUUSD", "WTI", "SPX500", "COFFEE"]
# Rổ mở rộng 14 thị trường, 5 lớp (FX, kim loại, năng lượng, chỉ số, nông sản)
MARKETS_WIDE = ["GBPJPY", "EURUSD",                     # FX
                "XAUUSD", "XAGUSD", "COPPER",           # kim loại
                "WTI", "BRENT", "NATGAS",               # năng lượng
                "SPX500", "NAS100",                     # chỉ số
                "COFFEE", "SUGAR", "COCOA", "SOYBEAN"]  # nông sản


# Ngày sớm nhất an toàn (Dukascopy treo nếu xin trước mốc này, kể cả D1)
MIN_START = {"BTCUSD": "2017-05-07", "ETHUSD": "2017-12-11", "LTCUSD": "2018-09-03"}


def load_h4_safe(sym, start, end):
    """Tải H4 an toàn: dùng D1 (bền) dò ngày khai sinh, rồi chỉ tải H4 từ đó.

    Tránh treo vĩnh viễn khi xin H4 trước ngày instrument có data (Dukascopy retry).
    Với crypto, chính D1 cũng treo nếu xin trước inception -> dùng MIN_START.
    """
    safe_start = start
    if sym in MIN_START and pd.Timestamp(start) < pd.Timestamp(MIN_START[sym]):
        safe_start = MIN_START[sym]
    d1 = load(sym, "D1", safe_start, end)
    incept = d1.index[0].date()
    real_start = max(pd.Timestamp(safe_start).date(), incept)
    return load(sym, "H4", real_start.isoformat(), end)


def quote_to_usd(sym, df, start, end):
    """Chỉ GBPJPY (quote JPY) cần quy đổi; còn lại quote USD -> 1."""
    if sym == "GBPJPY":
        usdjpy = load("USDJPY", "H4", start, end)["close"]
        return (1.0 / usdjpy.reindex(df.index, method="ffill").bfill()).to_numpy()
    return np.ones(len(df))


def metrics(eq, init):
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 24 * 3600)
    total = eq.iloc[-1] / init - 1
    cagr = (eq.iloc[-1] / init) ** (1 / years) - 1
    dd = (eq / eq.cummax() - 1).min()
    cal = cagr / abs(dd) if dd < 0 else float("nan")
    return total, cagr, dd, cal


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--equity", type=float, default=10_000.0)
    p.add_argument("--risks", default="0.02,0.03,0.05,0.08")
    p.add_argument("--entry", type=int, default=5)
    p.add_argument("--sl-atr", type=float, default=3.0)
    p.add_argument("--trail-atr", type=float, default=5.0)
    p.add_argument("--split", type=float, default=0.6)
    p.add_argument("--wide", action="store_true", help="dùng rổ mở rộng (14 thị trường)")
    p.add_argument("--markets", default="", help="danh sách tùy chỉnh, phẩy ngăn cách")
    p.add_argument("--out", default="results/portfolio.png")
    return p.parse_args()


def build_combined(sleeves, master, alloc):
    cols = []
    for eq in sleeves:
        cols.append(eq.reindex(master).ffill().fillna(alloc))
    return pd.concat(cols, axis=1).sum(axis=1)


def main():
    a = parse_args()
    if a.markets:
        markets = [s.strip().upper() for s in a.markets.split(",")]
    else:
        markets = MARKETS_WIDE if a.wide else MARKETS
    alloc = a.equity / len(markets)
    params = BreakoutParams(entry_period=a.entry, sl_atr=a.sl_atr,
                            trail_atr=a.trail_atr, use_trend=False)

    data = {}
    for sym in markets:
        print(f"Tải + sinh tín hiệu {sym}...")
        df = load_h4_safe(sym, a.start, a.end)
        setups = BreakoutTrend(params).generate_setups(df, pd.Series(0, index=df.index))
        data[sym] = dict(df=df, setups=setups, atr=atr(df, 14).to_numpy(),
                         q=quote_to_usd(sym, df, a.start, a.end), pip=pip_size(sym))
        print(f"  -> {len(df)} nến ({df.index[0].date()}..{df.index[-1].date()}), {len(setups)} setup")

    master = pd.DatetimeIndex([])
    for d in data.values():
        master = master.union(d["df"].index)
    master = master.sort_values()

    risks = [float(x) for x in a.risks.split(",")]
    print(f"\n{'risk':>5} | {'CAGR':>7} {'maxDD':>8} {'Calmar':>7} {'x lần':>7} | "
          f"{'CAGR>35&DD<40?':>14}")
    print("-" * 62)
    results = {}
    for r in risks:
        sleeves = []
        for sym, d in data.items():
            res = TradeBroker(sym, d["pip"], alloc, risk_pct=r, costs=CostConfig()).run(
                d["df"], d["setups"], d["q"], d["atr"])
            sleeves.append(res.equity)
        comb = build_combined(sleeves, master, alloc)
        tot, cg, dd, cal = metrics(comb, a.equity)
        ok = "✅ ĐẠT" if (cg > 0.35 and dd > -0.40) else ""
        print(f"{r*100:4.0f}% | {cg*100:6.1f}% {dd*100:7.1f}% {cal:7.2f} {comb.iloc[-1]/a.equity:6.1f}x | {ok:>14}")
        results[r] = comb

    # Chọn risk có CAGR cao nhất giữ DD<40%, vẽ + IS/OOS
    best_r = None
    for r in risks:
        _, cg, dd, _ = metrics(results[r], a.equity)
        if dd > -0.40 and (best_r is None or cg > metrics(results[best_r], a.equity)[1]):
            best_r = r
    if best_r is None:
        best_r = risks[0]
    comb = results[best_r]
    cut = comb.index[int(len(comb) * a.split)]
    for label, seg in [("IN-SAMPLE", comb.loc[:cut]), ("OUT-OF-SAMPLE", comb.loc[cut:])]:
        _, cg, dd, cal = metrics(seg, seg.iloc[0])
        print(f"  [{label}] CAGR {cg*100:.1f}%  DD {dd*100:.1f}%  Calmar {cal:.2f}")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(comb.index, comb.values, lw=1.0, label="Danh mục 5 thị trường")
    ax.axhline(a.equity, color="gray", ls=":", lw=0.8)
    ax.set_yscale("log")
    ax.set_title(f"Portfolio CTA 5 thị trường — risk {best_r*100:.0f}%/lệnh")
    ax.set_ylabel("Equity ($, log)"); ax.legend()
    fig.tight_layout(); fig.savefig(a.out, dpi=110)
    print(f"\nĐã lưu {a.out}")


if __name__ == "__main__":
    main()
