"""Chiến lược breakout cưỡi-trend (trend-following) cho TradeBroker.

Vào lệnh khi giá phá kênh Donchian N nến (thuận trend D1 nếu bật), rồi dùng
TRAILING STOP để winners chạy theo xu hướng -> bắt sóng lớn (mục tiêu x5).
Đặc trưng trend-following: winrate THẤP (<50%) nhưng vài lệnh thắng rất lớn.

Đây là phía đối lập của price_action_sr (fade, winrate cao, không cưỡi sóng).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.backtest.broker import TradeSetup
from src.strategies.indicators import atr


@dataclass
class BreakoutParams:
    entry_period: int = 20     # phá đỉnh/đáy N nến
    atr_period: int = 14
    sl_atr: float = 2.0        # stop ban đầu = entry -/+ sl_atr*ATR
    trail_atr: float = 3.0     # trailing = đỉnh/đáy - trail_atr*ATR
    use_trend: bool = True     # lọc thuận trend D1
    tp1_atr: float = 0.0       # >0: chốt một phần tại entry +/- tp1_atr*ATR (tăng winrate)
    tp1_frac: float = 0.5      # tỉ lệ đóng tại tp1
    be_after_tp1: bool = True  # dời stop về hòa vốn sau tp1
    # --- BỘ LỌC EDGE (nâng PF) ---
    session_start: int = 0     # chỉ vào lệnh khi giờ UTC trong [start, end) (London/NY = 6-22)
    session_end: int = 24
    atr_rising_k: int = 0      # >0: chỉ vào khi ATR[t] > ATR[t-k] (biến động đang nở)
    breakout_buffer: float = 0.0  # >0: phải phá kênh thêm buffer*ATR (break mạnh, tránh giả)


class BreakoutTrend:
    name = "breakout_trend"

    def __init__(self, params: BreakoutParams | None = None,
                 allow_long: bool = True, allow_short: bool = True):
        self.p = params or BreakoutParams()
        self.allow_long = allow_long
        self.allow_short = allow_short

    def generate_setups(self, df: pd.DataFrame, d1_trend: pd.Series) -> list[TradeSetup]:
        p = self.p
        c = df["close"].to_numpy()
        a = atr(df, p.atr_period).to_numpy()
        trend = d1_trend.reindex(df.index).fillna(0).to_numpy()
        # kênh Donchian của N nến TRƯỚC nến hiện tại (shift 1 -> no look-ahead)
        upper = df["high"].rolling(p.entry_period).max().shift(1).to_numpy()
        lower = df["low"].rolling(p.entry_period).min().shift(1).to_numpy()

        hours = df.index.hour.to_numpy()
        use_session = not (p.session_start == 0 and p.session_end == 24)

        setups: list[TradeSetup] = []
        n = len(df)
        for t in range(p.entry_period + p.atr_period, n - 1):
            if np.isnan(upper[t]) or a[t] <= 0:
                continue
            # --- Bộ lọc edge ---
            if use_session and not (p.session_start <= hours[t] < p.session_end):
                continue
            if p.atr_rising_k > 0 and not (a[t] > a[t - p.atr_rising_k]):
                continue
            buf = p.breakout_buffer * a[t]
            bias = trend[t] if p.use_trend else 0
            # LONG: phá đỉnh (mạnh hơn buffer), thuận uptrend nếu bật
            if self.allow_long and c[t] > upper[t] + buf and (not p.use_trend or bias > 0):
                stop = c[t] - p.sl_atr * a[t]
                tp1 = c[t] + p.tp1_atr * a[t] if p.tp1_atr > 0 else 0.0
                setups.append(TradeSetup(t, +1, stop, c[t] + 100 * a[t], "breakout-up",
                                         trail_atr=p.trail_atr, tp1=tp1,
                                         tp1_frac=p.tp1_frac, be_after_tp1=p.be_after_tp1))
            # SHORT: thủng đáy
            elif self.allow_short and c[t] < lower[t] - buf and (not p.use_trend or bias < 0):
                stop = c[t] + p.sl_atr * a[t]
                tp1 = c[t] - p.tp1_atr * a[t] if p.tp1_atr > 0 else 0.0
                setups.append(TradeSetup(t, -1, stop, c[t] - 100 * a[t], "breakout-dn",
                                         trail_atr=p.trail_atr, tp1=tp1,
                                         tp1_frac=p.tp1_frac, be_after_tp1=p.be_after_tp1))
        return setups
