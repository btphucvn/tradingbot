"""Engine backtest cấp-lệnh (trade-level) cho chiến lược có stop-loss/take-profit.

Khác `engine.py` (signal-based): engine này nhận danh sách "setup" lệnh, mỗi setup
có sẵn STOP và TARGET, rồi:
  * Sizing theo % RỦI RO: units = (equity * risk%) / khoảng_cách_stop.
  * Khớp SL/TP TRONG NẾN bằng high/low (xử lý cả gap).
  * Mỗi thời điểm giữ tối đa 1 vị thế (vào lệnh mới chỉ khi đang flat).
  * Trừ spread/slippage mỗi lần khớp + swap qua đêm.

Tín hiệu ở bar t (entry_pos) -> khớp ở GIÁ MỞ CỬA bar t+1 (no look-ahead).
Trả về BacktestResult tương thích metrics.py (trades có cột `pnl` thực mỗi lệnh).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .engine import BacktestResult, CostConfig


@dataclass
class TradeSetup:
    entry_pos: int      # bar phát tín hiệu (khớp ở open của bar kế tiếp)
    direction: int      # +1 long, -1 short
    stop: float         # giá stop-loss
    target: float       # giá take-profit
    reason: str = ""    # mô tả setup (reversal / break-retest...)
    trail_atr: float = 0.0  # >0: trailing stop = đỉnh/đáy - trail_atr*ATR (cưỡi trend)
    tp1: float = 0.0        # >0: mục tiêu CHỐT MỘT PHẦN (gần) -> tăng winrate
    tp1_frac: float = 0.5   # tỉ lệ đóng tại tp1
    be_after_tp1: bool = True  # sau khi chốt tp1, dời stop về hòa vốn (breakeven)


class TradeBroker:
    LOT_SIZE = 100_000

    def __init__(
        self,
        symbol: str,
        pip: float,
        initial_equity: float = 10_000.0,
        risk_pct: float = 0.01,
        max_leverage: float = 30.0,
        costs: CostConfig | None = None,
    ):
        self.symbol = symbol
        self.pip = pip
        self.initial_equity = initial_equity
        self.risk_pct = risk_pct
        self.max_leverage = max_leverage
        self.costs = costs or CostConfig()

    def run(self, df: pd.DataFrame, setups: list[TradeSetup],
            quote_to_usd: "np.ndarray | None" = None,
            atr: "np.ndarray | None" = None) -> BacktestResult:
        """quote_to_usd: giá trị USD của 1 đơn vị tiền định giá (quote) mỗi nến.
        = 1.0 cho cặp quote=USD (EURUSD...). Với GBPJPY (quote=JPY) thì = 1/USDJPY.
        Nhờ vậy P&L, sizing theo rủi ro, phí, swap đều quy về USD chính xác.
        atr: mảng ATR mỗi nến, cần khi setup có trail_atr>0 (trailing stop).
        """
        idx = df.index
        o = df["open"].to_numpy(float)
        h = df["high"].to_numpy(float)
        l = df["low"].to_numpy(float)
        c = df["close"].to_numpy(float)
        if self.costs.use_data_spread and "spread" in df:
            spread = df["spread"].to_numpy(float)
        else:
            spread = np.full(len(df), self.costs.spread_pips * self.pip)
        n = len(df)
        q = np.ones(n) if quote_to_usd is None else np.asarray(quote_to_usd, float)
        atr_arr = None if atr is None else np.asarray(atr, float)
        slip = self.costs.slippage_pips * self.pip
        day = idx.normalize() if hasattr(idx, "normalize") else None

        # setup phát ở bar t -> khớp ở bar t+1. Map fill_bar -> setup.
        fill_at: dict[int, TradeSetup] = {}
        for s in setups:
            fb = s.entry_pos + 1
            if 0 <= fb < n:
                fill_at.setdefault(fb, s)  # nếu trùng bar, lấy setup đầu

        cash = self.initial_equity
        equity = np.empty(n, float)
        pos_units = np.zeros(n, float)
        pos = None  # dict: units, entry_price, stop, target, dir, entry_time, entry_cost, reason
        trades: list[dict] = []

        for t in range(n):
            cost_per_unit = spread[t] / 2.0 + slip

            # 0) Chốt một phần tại tp1 (nếu chưa chốt và giá chạm tp1, mà chưa dính stop).
            if pos is not None and pos["tp1"] > 0 and not pos["partial_done"]:
                d = pos["dir"]
                hit = (h[t] >= pos["tp1"]) if d > 0 else (l[t] <= pos["tp1"])
                hit_stop_first = (l[t] <= pos["stop"]) if d > 0 else (h[t] >= pos["stop"])
                if hit and not hit_stop_first:
                    part = pos["init_units"] * pos["tp1_frac"]
                    fill = pos["tp1"]
                    realized = part * (fill - pos["entry_price"]) * q[t]
                    pcost = abs(part) * cost_per_unit * q[t]
                    cash += realized - pcost
                    pos["realized"] += realized - pcost
                    pos["units"] -= part
                    pos["partial_done"] = True
                    if pos["be_after_tp1"]:
                        pos["stop"] = pos["entry_price"]   # dời stop về hòa vốn

            # 1) Quản lý vị thế đang mở: kiểm tra chạm SL/TP (phần còn lại) trong nến t.
            if pos is not None:
                exit_price = None
                exit_reason = None
                d = pos["dir"]
                stop, target = pos["stop"], pos["target"]
                if d > 0:
                    if l[t] <= stop:                       # SL (ưu tiên: giả định xấu nhất)
                        exit_price = min(stop, o[t])       # gap xuống -> khớp ở open
                        exit_reason = "SL"
                    elif h[t] >= target:                   # TP
                        exit_price = o[t] if o[t] >= target else target
                        exit_reason = "TP"
                else:
                    if h[t] >= stop:
                        exit_price = max(stop, o[t])       # gap lên -> khớp ở open
                        exit_reason = "SL"
                    elif l[t] <= target:
                        exit_price = o[t] if o[t] <= target else target
                        exit_reason = "TP"

                if exit_price is not None:
                    units = pos["units"]
                    realized = units * (exit_price - pos["entry_price"]) * q[t]
                    exit_cost = abs(units) * cost_per_unit * q[t]
                    cash += realized - exit_cost
                    # P&L tổng = phần đã chốt (tp1) + phần còn lại - phí vào.
                    pnl = pos["realized"] + realized - exit_cost - pos["entry_cost"]
                    trades.append({
                        "entry_time": pos["entry_time"], "exit_time": idx[t],
                        "dir": d, "entry_price": pos["entry_price"],
                        "exit_price": exit_price, "units": pos["init_units"],
                        "pnl": pnl, "cost": pos["entry_cost"] + exit_cost,
                        "reason": pos["reason"], "exit_reason": exit_reason,
                    })
                    pos = None

            # 1b) Trailing stop: siết stop theo đỉnh/đáy đã đạt (cho bar sau).
            if pos is not None and pos["trail_atr"] > 0 and atr_arr is not None:
                k = pos["trail_atr"] * atr_arr[t]
                if pos["dir"] > 0:
                    pos["hw"] = max(pos["hw"], h[t])
                    pos["stop"] = max(pos["stop"], pos["hw"] - k)
                else:
                    pos["lw"] = min(pos["lw"], l[t])
                    pos["stop"] = min(pos["stop"], pos["lw"] + k)

            # 2) Vào lệnh mới nếu đang flat và có setup khớp ở bar t.
            if pos is None and t in fill_at:
                s = fill_at[t]
                entry_price = o[t]
                stop_dist = abs(entry_price - s.stop)
                # stop phải ở đúng phía so với entry.
                valid = stop_dist > 0 and (
                    (s.direction > 0 and s.stop < entry_price) or
                    (s.direction < 0 and s.stop > entry_price))
                if valid:
                    risk_amount = cash * self.risk_pct
                    units = s.direction * risk_amount / (stop_dist * q[t])
                    max_units = cash * self.max_leverage / (entry_price * q[t])
                    if abs(units) > max_units:
                        units = s.direction * max_units
                    entry_cost = abs(units) * cost_per_unit * q[t]
                    cash -= entry_cost
                    pos = {
                        "units": units, "init_units": units, "entry_price": entry_price,
                        "stop": s.stop, "target": s.target, "dir": s.direction,
                        "entry_time": idx[t], "entry_cost": entry_cost,
                        "reason": s.reason, "trail_atr": s.trail_atr,
                        "hw": entry_price, "lw": entry_price,
                        "tp1": s.tp1, "tp1_frac": s.tp1_frac,
                        "be_after_tp1": s.be_after_tp1, "partial_done": False,
                        "realized": 0.0,
                    }

            # 3) Swap qua đêm.
            if pos is not None and day is not None and t > 0 and day[t] != day[t - 1]:
                swap_pips = (self.costs.swap_long_pips if pos["dir"] > 0
                             else self.costs.swap_short_pips)
                cash += abs(pos["units"]) * swap_pips * self.pip * q[t]

            # 4) Equity mark-to-market (cash + lãi/lỗ chưa chốt tại close).
            if pos is not None:
                unreal = pos["units"] * (c[t] - pos["entry_price"]) * q[t]
                equity[t] = cash + unreal
                pos_units[t] = pos["units"]
            else:
                equity[t] = cash

            if cash <= 0:
                equity[t:] = max(cash, 0.0)
                break

        equity_s = pd.Series(equity, index=idx, name="equity")
        returns_s = equity_s.pct_change().fillna(0.0)
        position_s = pd.Series(pos_units / self.LOT_SIZE, index=idx, name="position_lots")
        trades_df = pd.DataFrame(trades)

        return BacktestResult(
            equity=equity_s, returns=returns_s, position=position_s,
            trades=trades_df, initial_equity=self.initial_equity,
            meta={"symbol": self.symbol, "risk_pct": self.risk_pct},
        )
