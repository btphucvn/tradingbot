"""Nhận diện mẫu nến price action (tín hiệu từ chối / đảo chiều).

Mỗi hàm nhận OHLC dạng numpy array + chỉ số i, trả về bool cho nến tại i.
Dùng cho xác nhận tín hiệu khi giá phản ứng tại vùng S/R.
"""

from __future__ import annotations

import numpy as np


def _parts(o, h, l, c, i):
    body = abs(c[i] - o[i])
    rng = h[i] - l[i]
    upper_wick = h[i] - max(o[i], c[i])
    lower_wick = min(o[i], c[i]) - l[i]
    return body, rng, upper_wick, lower_wick


def bullish_pin(o, h, l, c, i, wick_ratio: float = 2.0) -> bool:
    """Pin bar tăng: bóng dưới dài (từ chối giá thấp), thân nhỏ ở nửa trên."""
    body, rng, _, lower_wick = _parts(o, h, l, c, i)
    if rng <= 0:
        return False
    return lower_wick >= wick_ratio * body and lower_wick >= 0.5 * rng


def bearish_pin(o, h, l, c, i, wick_ratio: float = 2.0) -> bool:
    """Pin bar giảm: bóng trên dài (từ chối giá cao)."""
    body, rng, upper_wick, _ = _parts(o, h, l, c, i)
    if rng <= 0:
        return False
    return upper_wick >= wick_ratio * body and upper_wick >= 0.5 * rng


def bullish_engulfing(o, h, l, c, i) -> bool:
    """Nến tăng nhấn chìm: nến i tăng và thân bao trùm thân nến giảm i-1."""
    if i < 1:
        return False
    prev_down = c[i - 1] < o[i - 1]
    cur_up = c[i] > o[i]
    engulf = c[i] >= o[i - 1] and o[i] <= c[i - 1]
    return prev_down and cur_up and engulf


def bearish_engulfing(o, h, l, c, i) -> bool:
    """Nến giảm nhấn chìm."""
    if i < 1:
        return False
    prev_up = c[i - 1] > o[i - 1]
    cur_down = c[i] < o[i]
    engulf = c[i] <= o[i - 1] and o[i] >= c[i - 1]
    return prev_up and cur_down and engulf


def bullish_rejection(o, h, l, c, i) -> bool:
    """Có tín hiệu từ chối TĂNG tại nến i (pin hoặc engulfing)."""
    return bullish_pin(o, h, l, c, i) or bullish_engulfing(o, h, l, c, i)


def bearish_rejection(o, h, l, c, i) -> bool:
    """Có tín hiệu từ chối GIẢM tại nến i (pin hoặc engulfing)."""
    return bearish_pin(o, h, l, c, i) or bearish_engulfing(o, h, l, c, i)


def as_arrays(df):
    """Tiện ích: tách df thành 4 array open/high/low/close."""
    return (df["open"].to_numpy(), df["high"].to_numpy(),
            df["low"].to_numpy(), df["close"].to_numpy())
