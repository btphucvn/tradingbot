"""Backtest engine bar-by-bar cho forex, minh bạch về chi phí.

Nguyên tắc tránh tự lừa dối:
  * Tín hiệu tính trên bar t, nhưng lệnh khớp ở GIÁ MỞ CỬA bar t+1
    (không nhìn trộm tương lai - no look-ahead).
  * Mỗi lần đổi vị thế đều trừ: nửa spread + slippage (cross the spread).
  * Giữ qua đêm bị trừ swap (phí qua đêm).
  * Vốn COMPOUND: notional = equity * leverage, nên lời/lỗ cộng dồn theo vốn.

Quy ước:
  * signal trong {-1, 0, +1}: hướng mong muốn (short/flat/long).
  * P&L tính bằng quote currency. Với cặp .../USD (EURUSD...) thì là USD.
    -> Để đơn giản v1, chỉ nên dùng các cặp quote = USD.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class CostConfig:
    """Cấu hình chi phí giao dịch (đơn vị: pips trừ khi ghi rõ)."""
    slippage_pips: float = 0.2          # trượt giá mỗi lần khớp
    swap_long_pips: float = -0.3        # phí qua đêm khi giữ long (âm = trừ tiền)
    swap_short_pips: float = -0.1       # phí qua đêm khi giữ short
    commission_per_lot: float = 0.0     # hoa hồng mỗi lot mỗi vòng (quote ccy)
    use_data_spread: bool = True        # dùng spread thật trong data; nếu False dùng spread_pips
    spread_pips: float = 0.5            # spread cố định khi use_data_spread=False


@dataclass
class BacktestResult:
    equity: pd.Series                   # đường vốn theo thời gian
    returns: pd.Series                  # lợi nhuận mỗi bar (theo %)
    position: pd.Series                 # vị thế (lot) đang giữ mỗi bar
    trades: pd.DataFrame                # nhật ký từng lần đổi vị thế
    initial_equity: float
    meta: dict = field(default_factory=dict)

    @property
    def final_equity(self) -> float:
        return float(self.equity.iloc[-1])


class Backtest:
    """Mô phỏng một chiến lược trên một cặp tiền."""

    LOT_SIZE = 100_000  # 1 standard lot = 100k đơn vị tiền cơ sở

    def __init__(
        self,
        symbol: str,
        pip: float,
        initial_equity: float = 10_000.0,
        leverage: float = 1.0,
        costs: CostConfig | None = None,
    ):
        self.symbol = symbol
        self.pip = pip
        self.initial_equity = initial_equity
        self.leverage = leverage
        self.costs = costs or CostConfig()

    def run(self, df: pd.DataFrame, signal: pd.Series) -> BacktestResult:
        """Chạy backtest.

        Args:
            df: DataFrame có cột open/high/low/close (+ spread nếu dùng).
            signal: Series {-1,0,+1} cùng index với df. Tín hiệu ở bar t
                    được THỰC THI ở giá mở cửa bar t+1.
        """
        df = df.copy()
        signal = signal.reindex(df.index).fillna(0.0)

        # Dịch tín hiệu 1 bar: quyết định ở t -> khớp ở open của t+1.
        target_dir = signal.shift(1).fillna(0.0).to_numpy()

        open_ = df["open"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        if self.costs.use_data_spread and "spread" in df:
            spread = df["spread"].to_numpy(dtype=float)
        else:
            spread = np.full(len(df), self.costs.spread_pips * self.pip)

        n = len(df)
        equity = np.empty(n, dtype=float)
        pos_units = np.zeros(n, dtype=float)   # vị thế (đơn vị tiền cơ sở) đang giữ trong bar
        slip = self.costs.slippage_pips * self.pip

        cash_equity = self.initial_equity
        cur_units = 0.0                         # vị thế hiện tại
        cur_dir = 0.0
        trades: list[dict] = []

        # Phát hiện ranh giới ngày để tính swap (giữ qua nửa đêm UTC).
        idx = df.index
        day = idx.normalize() if hasattr(idx, "normalize") else None

        for t in range(n):
            # 1) Đổi vị thế nếu hướng mục tiêu khác hướng hiện tại.
            want_dir = target_dir[t]
            if want_dir != cur_dir:
                # Đóng vị thế cũ (nếu có) rồi mở mới, đều ở open[t].
                exec_price = open_[t]
                # Sizing: notional = equity * leverage, quy ra đơn vị tiền cơ sở.
                new_units = want_dir * (cash_equity * self.leverage) / exec_price

                traded = abs(new_units - cur_units)
                # Chi phí cross spread + slippage trên khối lượng giao dịch.
                cost = traded * (spread[t] / 2.0 + slip)
                # Hoa hồng theo số lot giao dịch.
                cost += (traded / self.LOT_SIZE) * self.costs.commission_per_lot
                cash_equity -= cost

                trades.append({
                    "time": idx[t],
                    "price": exec_price,
                    "from_units": cur_units,
                    "to_units": new_units,
                    "cost": cost,
                })
                cur_units = new_units
                cur_dir = want_dir

            pos_units[t] = cur_units

            # 2) P&L theo biến động giá trong bar (open -> close).
            #    (mark-to-market đơn giản, đủ cho khung bar.)
            pnl = cur_units * (close[t] - open_[t])
            cash_equity += pnl

            # 3) Swap qua đêm: nếu sang ngày mới mà vẫn giữ vị thế.
            if day is not None and t > 0 and day[t] != day[t - 1] and cur_units != 0:
                swap_pips = (self.costs.swap_long_pips if cur_units > 0
                             else self.costs.swap_short_pips)
                cash_equity += abs(cur_units) * swap_pips * self.pip

            equity[t] = cash_equity

            # Cháy tài khoản -> dừng.
            if cash_equity <= 0:
                equity[t:] = 0.0
                break

        equity_s = pd.Series(equity, index=idx, name="equity")
        returns_s = equity_s.pct_change().fillna(0.0)
        position_s = pd.Series(pos_units / self.LOT_SIZE, index=idx, name="position_lots")
        trades_df = pd.DataFrame(trades)

        return BacktestResult(
            equity=equity_s,
            returns=returns_s,
            position=position_s,
            trades=trades_df,
            initial_equity=self.initial_equity,
            meta={"symbol": self.symbol, "leverage": self.leverage},
        )
