"""Donchian Channel breakout - chiến lược trend-following baseline.

Ý tưởng (kinh điển, dùng bởi nhóm Turtle Traders):
  * Mua khi giá close vượt đỉnh cao nhất N bar gần nhất -> bắt xu hướng tăng.
  * Bán (short) khi giá close thủng đáy thấp nhất N bar gần nhất.
  * Thoát khi giá quay lại cắt kênh giữa (đường thoát exit_period).

Đây KHÔNG phải chiến lược chắc lãi - nó là mốc tham chiếu sạch, ít tham số,
khó overfit, để so sánh mọi ý tưởng khác.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Strategy


class DonchianBreakout(Strategy):
    name = "donchian"

    def __init__(self, entry_period: int = 20, exit_period: int = 10,
                 allow_short: bool = True):
        if exit_period >= entry_period:
            raise ValueError("exit_period nên nhỏ hơn entry_period")
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.allow_short = allow_short

    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]

        # Kênh vào lệnh: đỉnh/đáy N bar TRƯỚC bar hiện tại (shift 1 -> no look-ahead).
        upper_entry = high.rolling(self.entry_period).max().shift(1)
        lower_entry = low.rolling(self.entry_period).min().shift(1)
        # Kênh thoát: đỉnh/đáy ngắn hơn.
        upper_exit = high.rolling(self.exit_period).max().shift(1)
        lower_exit = low.rolling(self.exit_period).min().shift(1)

        pos = np.zeros(len(df))
        cur = 0.0
        c = close.to_numpy()
        ue, le = upper_entry.to_numpy(), lower_entry.to_numpy()
        ux, lx = upper_exit.to_numpy(), lower_exit.to_numpy()

        for t in range(len(df)):
            if np.isnan(ue[t]):
                pos[t] = cur
                continue
            if cur == 0:
                if c[t] > ue[t]:
                    cur = 1.0
                elif self.allow_short and c[t] < le[t]:
                    cur = -1.0
            elif cur > 0:
                if c[t] < lx[t]:          # thoát long
                    cur = 0.0
                    if self.allow_short and c[t] < le[t]:
                        cur = -1.0
            elif cur < 0:
                if c[t] > ux[t]:          # thoát short
                    cur = 0.0
                    if c[t] > ue[t]:
                        cur = 1.0
            pos[t] = cur

        return pd.Series(pos, index=df.index, name="signal")
