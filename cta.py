#!/usr/bin/env python3
"""Engine CTA kiểu managed-futures (Carver/AHL): trend EWMAC đa tốc độ + vol-target
+ risk-parity trên NHIỀU thị trường. Mục tiêu: nâng Calmar NỀN (≈Sharpe) lên cao.

Khác hẳn breakout nhị phân trước:
  - Tín hiệu LIÊN TỤC (forecast), vị thế tỉ lệ với độ mạnh xu hướng / biến động.
  - Vol-target mỗi thị trường -> mỗi cái đóng góp rủi ro bằng nhau (risk parity).
  - Giao dịch nhiều thị trường ít tương quan -> Sharpe danh mục >> Sharpe đơn lẻ.

Dùng D1 (chuẩn managed-futures, load bền). Tính bằng % return -> không cần quy đổi tiền tệ.
"""

from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from src.data.loader import load

START, END = "2010-01-01", "2024-01-01"
SPEEDS = [(8, 32), (16, 64), (32, 128), (64, 256)]   # cặp EMA nhanh/chậm
VOL_SPAN = 32
SIGMA_TGT = 0.01          # vol mục tiêu mỗi thị trường (1%/ngày)
FC_CAP = 2.0              # cap forecast (đơn vị std)
COST = 0.0002            # phí ~ mỗi đơn vị thay đổi vị thế (round-trip ~2bp notional)


def forecast(close: pd.Series, vol: pd.Series) -> pd.Series:
    """Forecast trend liên tục = trung bình các EWMAC, chuẩn hóa, cap."""
    fc = pd.Series(0.0, index=close.index)
    for fast, slow in SPEEDS:
        raw = close.ewm(span=fast).mean() - close.ewm(span=slow).mean()
        f = raw / (close * vol)                 # chuẩn hóa theo biến động giá
        f = f / f.rolling(252, min_periods=40).std()   # về ~đơn vị std
        fc = fc + f.fillna(0)
    fc = fc / len(SPEEDS)
    return fc.clip(-FC_CAP, FC_CAP)


def market_returns(sym: str) -> pd.Series:
    """Chuỗi lợi nhuận DANH MỤC-HÓA của 1 thị trường (đã vol-target, trừ phí)."""
    d = load(sym, "D1", START, END)
    close = d["close"]
    r = close.pct_change()
    vol = r.ewm(span=VOL_SPAN).std()
    fc = forecast(close, vol)
    pos = (fc * SIGMA_TGT / vol).clip(-10, 10)   # vị thế (bội số return), cap chống nổ
    pos = pos.shift(1)                           # vào ở bar sau -> no look-ahead
    pnl = pos * r
    turnover = pos.diff().abs().fillna(0)
    pnl = pnl - turnover * COST
    return pnl.dropna()


def metrics(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    return cagr, dd, (cagr / abs(dd) if dd < 0 else np.nan)


def main():
    universe = ["GBPJPY", "EURUSD", "AUDUSD", "USDJPY", "USDCAD",
                "XAUUSD", "XAGUSD", "COPPER", "WTI", "BRENT", "NATGAS",
                "SPX500", "NAS100", "COFFEE", "SUGAR"]
    rets = {}
    print("Sharpe từng thị trường (vol-target EWMAC):")
    for sym in universe:
        try:
            pr = market_returns(sym)
            if len(pr) < 250:
                print(f"  {sym:8} bỏ (ít data)"); continue
            sh = pr.mean() / pr.std() * np.sqrt(252)
            rets[sym] = pr
            print(f"  {sym:8} Sharpe {sh:+.2f}  ({pr.index[0].year}-{pr.index[-1].year})")
        except Exception as e:
            print(f"  {sym:8} lỗi: {str(e)[:50]}")

    # Danh mục equal-risk: trung bình lợi nhuận các thị trường có data mỗi ngày
    mat = pd.concat(rets.values(), axis=1)
    port = mat.mean(axis=1).dropna()            # equal weight (mỗi cái đã vol-target)
    sh = port.mean() / port.std() * np.sqrt(252)
    ann_vol = port.std() * np.sqrt(252)
    print(f"\n>>> DANH MỤC {len(rets)} thị trường: Sharpe {sh:.2f}, vol {ann_vol*100:.1f}%/năm")

    # Quét đòn bẩy -> CAGR/DD/Calmar (Calmar ~bất biến; tìm L cho CAGR>35%)
    print(f"\n{'lev':>4} | {'CAGR':>7} {'maxDD':>8} {'Calmar':>7}")
    for L in [1, 2, 3, 4, 6, 8]:
        eq = (1 + L * port).cumprod()
        cg, dd, cal = metrics(eq)
        flag = "  <- CAGR>35%&DD<40%" if (cg > 0.35 and dd > -0.40) else ""
        print(f"{L:4d} | {cg*100:6.1f}% {dd*100:7.1f}% {cal:7.2f}{flag}")

    # IS/OOS của danh mục (Sharpe ổn định?)
    cut = port.index[int(len(port) * 0.6)]
    for lbl, seg in [("IS", port[:cut]), ("OOS", port[cut:])]:
        s = seg.mean() / seg.std() * np.sqrt(252)
        print(f"  [{lbl}] Sharpe {s:.2f}")


if __name__ == "__main__":
    main()
