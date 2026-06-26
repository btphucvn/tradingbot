#!/usr/bin/env python3
"""Báo cáo HTML chi tiết cho Danh mục CTA risk-parity (cta_portfolio.py).

Chạy lại backtest, thu thập đầy đủ số liệu (per-market, drawdown, tương quan,
lợi nhuận theo năm, sweep đòn bẩy, IS/OOS, thống kê lệnh) rồi xuất một trang
HTML tự chứa: results/cta_portfolio.html (vẽ bằng Chart.js).
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import json
import numpy as np
import pandas as pd

from run_portfolio import load_h4_safe, quote_to_usd
from src.backtest.broker import CostConfig, TradeBroker
from src.strategies.breakout import BreakoutParams, BreakoutTrend
from src.strategies.indicators import atr

START, END = "2018-01-01", "2026-06-20"
MARKETS = ["XAUUSD", "GBPJPY", "WTI", "COFFEE", "BTCUSD", "ETHUSD"]
LABELS = {
    "XAUUSD": "Vàng (XAU/USD)", "GBPJPY": "GBP/JPY", "WTI": "Dầu WTI",
    "COFFEE": "Cà phê", "BTCUSD": "Bitcoin", "ETHUSD": "Ethereum",
    "SUGAR": "Đường", "SOYBEAN": "Đậu tương", "SPX500": "S&P 500",
    "NATGAS": "Khí gas",
}
CLASS = {
    "XAUUSD": "Kim loại", "GBPJPY": "Ngoại hối", "WTI": "Năng lượng",
    "COFFEE": "Nông sản", "BTCUSD": "Crypto", "ETHUSD": "Crypto",
    "SUGAR": "Nông sản", "SOYBEAN": "Nông sản", "SPX500": "Chỉ số",
    "NATGAS": "Năng lượng",
}
PARAMS = BreakoutParams(5, 14, 3.0, 5.0, False)
BARS_PER_YEAR = 252 * 6   # ~6 nến H4/ngày
LEV_MAIN = 4.5


def run_sleeve(sym):
    df = load_h4_safe(sym, START, END)
    setups = BreakoutTrend(PARAMS).generate_setups(df, pd.Series(0, index=df.index))
    q = quote_to_usd(sym, df, START, END)
    res = TradeBroker(sym, 0.01 if "JPY" in sym else 0.0001, 10_000.0,
                      risk_pct=0.01, costs=CostConfig()).run(df, setups, q, atr(df, 14).to_numpy())
    return res


def curve_stats(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else -1
    dd = (eq / eq.cummax() - 1).min()
    cal = cagr / abs(dd) if dd < 0 else float("nan")
    return cagr, dd, cal


def trade_stats(trades):
    if trades is None or len(trades) == 0:
        return dict(n=0, win=float("nan"), pf=float("nan"), avg_win=0, avg_loss=0)
    pnl = trades["pnl"].to_numpy()
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("nan")
    return dict(n=len(pnl), win=len(wins) / len(pnl),
                pf=pf, avg_win=wins.mean() if len(wins) else 0,
                avg_loss=losses.mean() if len(losses) else 0)


def main():
    print("Chạy backtest từng thị trường...")
    rets, results = {}, {}
    for sym in MARKETS:
        res = run_sleeve(sym)
        results[sym] = res
        rets[sym] = res.equity.pct_change()
        print(f"  {sym} ok ({len(res.trades)} lệnh)")

    mat = pd.concat(rets, axis=1).dropna(how="all")
    vol = mat.std()
    inv = 1.0 / vol
    active = mat.notna().astype(float)
    w = active.mul(inv, axis=1)
    w = w.div(w.sum(axis=1), axis=0)
    rp_ret = (mat.fillna(0) * w).sum(axis=1)
    eq_w = active.div(active.sum(axis=1), axis=0)
    eq_ret = (mat.fillna(0) * eq_w).sum(axis=1)

    avg_w = w.mean()  # trọng số trung bình mỗi thị trường

    # ---- per-market table ----
    market_rows = []
    for sym in MARKETS:
        eq = results[sym].equity
        cg, dd, cal = curve_stats(eq / eq.iloc[0])
        ts = trade_stats(results[sym].trades)
        sret = rets[sym].dropna()
        sharpe = sret.mean() / sret.std() * np.sqrt(BARS_PER_YEAR) if sret.std() else 0
        # đường vốn chuẩn hóa (bắt đầu = 1) + drawdown, lấy mẫu theo tuần cho chart
        norm = eq / eq.iloc[0]
        nds = norm.resample("W").last().dropna()
        ddm = (norm / norm.cummax() - 1).resample("W").last().reindex(nds.index).fillna(0)
        mchart = dict(
            dates=[x.strftime("%Y-%m-%d") for x in nds.index],
            equity=[round(float(v), 4) for v in nds.values],
            dd=[round(float(v) * 100, 2) for v in ddm.values],
        )
        market_rows.append(dict(
            sym=sym, label=LABELS[sym], cls=CLASS[sym],
            cagr=cg, dd=dd, calmar=cal, sharpe=sharpe,
            weight=avg_w[sym], **ts,
            start=str(eq.index[0].date()), chart=mchart,
        ))

    # ---- portfolio (risk-parity, lev 5) ----
    r = rp_ret * LEV_MAIN
    eq = (1 + r).cumprod()
    cg, dd, cal = curve_stats(eq)
    sharpe = rp_ret.mean() / rp_ret.std() * np.sqrt(BARS_PER_YEAR)
    dd_series = (eq / eq.cummax() - 1)

    # ---- leverage sweep ----
    sweep = []
    for L in [3, 4, 4.5, 5, 5.5, 6]:
        e = (1 + rp_ret * L).cumprod()
        c, d, ca = curve_stats(e)
        sweep.append(dict(lev=L, cagr=c, dd=d, calmar=ca,
                          mult=e.iloc[-1], ok=(c > 0.35 and d > -0.40)))

    # ---- equal-weight comparison ----
    ew = []
    for L in [3, 4, 4.5, 5, 5.5, 6]:
        e = (1 + eq_ret * L).cumprod()
        c, d, ca = curve_stats(e)
        ew.append(dict(lev=L, cagr=c, dd=d, calmar=ca))

    # ---- IS / OOS ----
    cut = rp_ret.index[int(len(rp_ret) * 0.6)]
    iso = {}
    for lbl, seg in [("IS", rp_ret[:cut]), ("OOS", rp_ret[cut:])]:
        e = (1 + seg * LEV_MAIN).cumprod()
        c, d, ca = curve_stats(e)
        iso[lbl] = dict(cagr=c, dd=d, calmar=ca,
                        start=str(seg.index[0].date()), end=str(seg.index[-1].date()))

    # ---- yearly returns ----
    yearly = []
    eq_year = eq.resample("YE").last()
    prev = 1.0
    for ts_, v in eq_year.items():
        yearly.append(dict(year=ts_.year, ret=v / prev - 1))
        prev = v

    # ---- correlation matrix ----
    corr = mat.corr().round(2)

    # ---- equity & drawdown downsample (weekly) ----
    eq_ds = eq.resample("W").last().dropna()
    dd_ds = dd_series.resample("W").last().reindex(eq_ds.index).fillna(0)
    eqw_ds = (1 + eq_ret * LEV_MAIN).cumprod().resample("W").last().reindex(eq_ds.index)
    chart = dict(
        dates=[d.strftime("%Y-%m-%d") for d in eq_ds.index],
        equity=[round(float(x), 4) for x in eq_ds.values],
        equalw=[round(float(x), 4) for x in eqw_ds.values],
        dd=[round(float(x) * 100, 2) for x in dd_ds.values],
    )

    data = dict(
        meta=dict(start=START, end=END, lev=LEV_MAIN, sharpe=round(float(sharpe), 2),
                  n_markets=len(MARKETS), bars=int(len(mat)),
                  generated=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")),
        port=dict(cagr=cg, dd=dd, calmar=cal, sharpe=float(sharpe),
                  total=float(eq.iloc[-1]), final_eq=float(eq.iloc[-1] * 10000)),
        markets=market_rows, sweep=sweep, ew=ew, iso=iso, yearly=yearly,
        corr=dict(syms=list(corr.columns), m=corr.values.tolist()),
        chart=chart,
    )
    build_html(data)
    print(f"\nDanh mục lev {LEV_MAIN}: CAGR {cg*100:.1f}%  DD {dd*100:.1f}%  "
          f"Calmar {cal:.2f}  Sharpe {sharpe:.2f}")
    print("Đã lưu results/cta_portfolio.html")


def build_html(d):
    from report_template import render
    html = render(d)
    with open("results/cta_portfolio.html", "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    main()
