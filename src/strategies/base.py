"""Interface chung cho mọi chiến lược.

Một chiến lược nhận DataFrame OHLC và trả về Series tín hiệu {-1, 0, +1}
cùng index với data. Tín hiệu ở bar t được engine thực thi ở open bar t+1,
nên chiến lược ĐƯỢC PHÉP dùng toàn bộ thông tin tới hết bar t (không nhìn
trộm tương lai khi tự nó chỉ đọc dữ liệu quá khứ và hiện tại).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        """Trả về Series {-1, 0, +1} cùng index với df."""
        ...
