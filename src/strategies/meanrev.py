"""Chiến lược mean-reversion (RSI) — NGƯỢC pha với trend-following.

Vào lệnh khi giá quá mua/quá bán (RSI cực trị), kỳ vọng giá hồi về trung bình.
Lãi khi thị trường ĐI NGANG; thua khi trend mạnh — tức ngược pha với breakout.
Mục đích: ghép với trend-follower để triệt tiêu drawdown lẫn nhau (tăng Calmar).

Thoát bằng TP/SL cố định theo ATR (không trailing — MR chốt nhanh khi hồi).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.backtest.broker import TradeSetup
from src.strategies.indicators import atr, rsi


@dataclass
class MeanRevParams:
    rsi_period: int = 14
    atr_period: int = 14
    oversold: float = 30.0     # RSI <= -> mua
    overbought: float = 70.0   # RSI >= -> bán
    tp_atr: float = 1.5        # chốt lời = entry +/- tp_atr*ATR (giá hồi về)
    sl_atr: float = 2.0        # cắt lỗ = entry -/+ sl_atr*ATR (trend tiếp diễn)


class MeanReversion:
    name = "mean_reversion"

    def __init__(self, params: MeanRevParams | None = None,
                 allow_long: bool = True, allow_short: bool = True):
        self.p = params or MeanRevParams()
        self.allow_long = allow_long
        self.allow_short = allow_short

    def generate_setups(self, df: pd.DataFrame, d1_trend: pd.Series = None) -> list[TradeSetup]:
        p = self.p
        c = df["close"].to_numpy()
        a = atr(df, p.atr_period).to_numpy()
        r = rsi(df["close"], p.rsi_period).to_numpy()
        n = len(df)
        setups: list[TradeSetup] = []
        for t in range(p.rsi_period + p.atr_period, n - 1):
            if a[t] <= 0 or np.isnan(r[t]) or np.isnan(r[t - 1]):
                continue
            # Vào khi RSI vừa CẮT vào vùng cực trị (tránh trùng lặp khi nằm lì).
            if self.allow_long and r[t - 1] > p.oversold >= r[t]:
                setups.append(TradeSetup(t, +1, c[t] - p.sl_atr * a[t],
                                         c[t] + p.tp_atr * a[t], "mr-long"))
            elif self.allow_short and r[t - 1] < p.overbought <= r[t]:
                setups.append(TradeSetup(t, -1, c[t] + p.sl_atr * a[t],
                                         c[t] - p.tp_atr * a[t], "mr-short"))
        return setups
