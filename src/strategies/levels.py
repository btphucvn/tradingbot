"""Phát hiện vùng kháng cự / hỗ trợ từ swing pivot.

Quy trình:
  1. find_pivots: tìm swing-high/swing-low (đỉnh/đáy cục bộ).
     Pivot tại vị trí i chỉ được XÁC NHẬN sau `right` nến (confirm_pos = i+right)
     -> khi backtest tại bar t, chỉ dùng pivot có confirm_pos <= t -> no look-ahead.
  2. cluster_zones: gom các pivot gần nhau (trong dung sai tol) thành "zone".
     Số pivot trong cụm = số lần chạm (touches) = sức mạnh vùng.
  3. nearest_levels: tìm vùng hỗ trợ gần nhất dưới giá và kháng cự gần nhất trên giá.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Pivot:
    pos: int          # vị trí trong df
    price: float
    kind: str         # 'high' | 'low'
    confirm_pos: int  # nến xác nhận pivot (pos + right)


@dataclass
class Zone:
    price: float          # giá đại diện (trung bình các pivot trong cụm)
    lower: float          # rìa dưới vùng
    upper: float          # rìa trên vùng
    touches: int          # số lần chạm (sức mạnh)
    last_touch_pos: int   # vị trí lần chạm gần nhất
    kind: str = ""        # 'support' | 'resistance' (gán khi query theo giá)


def find_pivots(df: pd.DataFrame, left: int = 3, right: int = 3) -> list[Pivot]:
    """Tìm tất cả swing-high và swing-low.

    swing-high tại i: high[i] cao hơn `left` nến trái và `right` nến phải.
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    pivots: list[Pivot] = []

    for i in range(left, n - right):
        h = high[i]
        if (h > high[i - left:i]).all() and (h > high[i + 1:i + right + 1]).all():
            pivots.append(Pivot(i, h, "high", i + right))
        l = low[i]
        if (l < low[i - left:i]).all() and (l < low[i + 1:i + right + 1]).all():
            pivots.append(Pivot(i, l, "low", i + right))
    return pivots


def cluster_zones(pivots: list[Pivot], tol: float) -> list[Zone]:
    """Gom các pivot có giá gần nhau (chênh <= tol) thành vùng.

    Args:
        pivots: danh sách pivot ĐÃ lọc (đã xác nhận, trong cửa sổ lookback).
        tol: dung sai giá để coi 2 pivot là "cùng vùng" (vd 0.5*ATR).
    """
    if not pivots:
        return []
    ordered = sorted(pivots, key=lambda p: p.price)
    zones: list[Zone] = []
    cluster: list[Pivot] = [ordered[0]]

    def flush(c: list[Pivot]):
        prices = [p.price for p in c]
        zones.append(Zone(
            price=float(np.mean(prices)),
            lower=float(min(prices)),
            upper=float(max(prices)),
            touches=len(c),
            last_touch_pos=max(p.pos for p in c),
        ))

    for p in ordered[1:]:
        if p.price - cluster[0].price <= tol:
            cluster.append(p)
        else:
            flush(cluster)
            cluster = [p]
    flush(cluster)
    return zones


def active_zones_at(pivots: list[Pivot], t: int, tol: float,
                    lookback: int = 250, min_touches: int = 1) -> list[Zone]:
    """Các vùng S/R còn hiệu lực tại bar t (chỉ dùng pivot đã xác nhận tới t)."""
    usable = [p for p in pivots
              if p.confirm_pos <= t and (t - p.pos) <= lookback]
    zones = cluster_zones(usable, tol)
    return [z for z in zones if z.touches >= min_touches]


def nearest_levels(zones: list[Zone], price: float):
    """Trả về (support gần nhất dưới giá, resistance gần nhất trên giá).

    Mỗi cái có thể là None nếu không tồn tại.
    """
    support = None   # vùng cao nhất nằm dưới giá
    resistance = None  # vùng thấp nhất nằm trên giá
    for z in zones:
        if z.price <= price:
            if support is None or z.price > support.price:
                support = z
        else:
            if resistance is None or z.price < resistance.price:
                resistance = z
    if support is not None:
        support.kind = "support"
    if resistance is not None:
        resistance.kind = "resistance"
    return support, resistance


if __name__ == "__main__":
    # Sanity-check: in các vùng S/R phát hiện ở cuối đoạn dữ liệu mẫu.
    from src.data.loader import load
    from src.strategies.indicators import atr

    df = load("EURUSD", "H4", "2023-01-01", "2024-01-01")
    a = atr(df, 14)
    pivots = find_pivots(df, 3, 3)
    t = len(df) - 1
    tol = 0.5 * float(a.iloc[t])
    zones = active_zones_at(pivots, t, tol, lookback=250, min_touches=2)
    price = float(df["close"].iloc[t])

    print(f"Tìm thấy {len(pivots)} pivot tổng cộng.")
    print(f"Giá hiện tại: {price:.5f} | tol vùng = {tol/0.0001:.1f} pips\n")
    print(f"{len(zones)} vùng mạnh (>=2 chạm) trong 250 nến gần nhất:")
    for z in sorted(zones, key=lambda z: z.price):
        mark = "  <-- giá" if z.lower <= price <= z.upper else ""
        print(f"  {z.price:.5f}  [{z.lower:.5f}-{z.upper:.5f}]  "
              f"chạm={z.touches}{mark}")
    sup, res = nearest_levels(zones, price)
    print(f"\nHỗ trợ gần nhất:  {sup.price:.5f} (chạm {sup.touches})" if sup else "\nKhông có hỗ trợ")
    print(f"Kháng cự gần nhất: {res.price:.5f} (chạm {res.touches})" if res else "Không có kháng cự")
