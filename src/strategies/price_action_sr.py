"""Chiến lược price action theo vùng kháng cự / hỗ trợ (khung H4).

Hai loại setup, đều lọc thuận xu hướng D1:
  * ĐẢO CHIỀU TẠI VÙNG: giá chạm hỗ trợ mạnh + nến từ chối tăng (trong uptrend) -> LONG.
  * BREAK & RETEST: giá phá kháng cự, quay lại test nó như hỗ trợ + xác nhận -> LONG.
  (đối xứng cho SHORT trong downtrend).

Sinh ra danh sách TradeSetup (entry ở open nến kế tiếp, có stop & target sẵn) để
đưa vào TradeBroker. Tín hiệu chỉ dùng dữ liệu tới hết nến t -> no look-ahead.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.backtest.broker import TradeSetup
from src.strategies import patterns as pat
from src.strategies.indicators import atr
from src.strategies.levels import active_zones_at, find_pivots, nearest_levels


@dataclass
class PAParams:
    pivot_left: int = 3
    pivot_right: int = 3
    atr_period: int = 14
    tol_factor: float = 0.5        # dung sai gom vùng = tol_factor * ATR
    lookback: int = 250            # số nến H4 giữ vùng còn hiệu lực
    min_touches: int = 2           # vùng phải chạm >= ngần này lần
    touch_tol_atr: float = 0.4     # giá "chạm" vùng nếu cách <= ngần này * ATR
    stop_buffer_atr: float = 0.5   # stop đặt ngoài rìa vùng thêm ngần này * ATR
    min_rr: float = 1.5            # lọc reward:risk tối thiểu (0 = tắt)
    fallback_rr: float = 2.0       # nếu không có vùng đối diện, target = fallback_rr * risk
    use_reversal: bool = True
    use_break_retest: bool = True
    break_lookback: int = 20       # cửa sổ phát hiện break gần đây
    # --- điều khiển cách thoát & chế độ (cho vòng lặp tối ưu) ---
    exit_mode: str = "zone"        # "zone" = target vùng đối diện | "atr" = TP cố định theo ATR
    tp_atr: float = 1.0            # với exit_mode="atr": TP = entry +/- tp_atr*ATR (TP gần -> winrate cao)
    sl_atr: float = 0.0            # >0: override stop = entry -/+ sl_atr*ATR (thay vì theo rìa vùng)
    mode: str = "trend"            # "trend" = thuận D1 | "range" = fade ngược tại vùng | "both"
    zone_refresh: int = 6          # chỉ tính lại vùng mỗi N nến (tăng tốc; vùng đổi chậm)
    session_start: int = 0         # lọc phiên: chỉ vào lệnh khi giờ UTC trong [start, end)
    session_end: int = 24          # mặc định 0-24 = mọi giờ (London~7-16, NY~13-22)


class PriceActionSR:
    name = "price_action_sr"

    def __init__(self, params: PAParams | None = None,
                 allow_long: bool = True, allow_short: bool = True):
        self.p = params or PAParams()
        self.allow_long = allow_long
        self.allow_short = allow_short

    def generate_setups(self, df: pd.DataFrame, d1_trend: pd.Series) -> list[TradeSetup]:
        p = self.p
        o, h, l, c = pat.as_arrays(df)
        a = atr(df, p.atr_period).to_numpy()
        trend = d1_trend.reindex(df.index).fillna(0.0).to_numpy()
        pivots = find_pivots(df, p.pivot_left, p.pivot_right)
        n = len(df)
        setups: list[TradeSetup] = []

        start = max(p.lookback, p.atr_period, p.break_lookback) + p.pivot_right
        hours = df.index.hour.to_numpy()
        use_session = not (p.session_start == 0 and p.session_end == 24)
        zones_cache: list = []
        last_refresh = -10**9
        for t in range(start, n - 1):   # n-1: cần có nến t+1 để khớp
            if use_session and not (p.session_start <= hours[t] < p.session_end):
                continue
            bias = trend[t]
            atr_t = a[t]
            if atr_t <= 0:
                continue
            # Hướng được phép vào tùy chế độ.
            if p.mode == "trend":
                if bias == 0:
                    continue
                long_ok, short_ok = bias > 0, bias < 0
            elif p.mode == "range":          # fade tại vùng, bỏ qua trend
                long_ok = short_ok = True
            else:                             # "both"
                long_ok = bias >= 0
                short_ok = bias <= 0
            long_ok &= self.allow_long
            short_ok &= self.allow_short

            tol = p.tol_factor * atr_t
            touch_tol = p.touch_tol_atr * atr_t
            buf = p.stop_buffer_atr * atr_t
            if t - last_refresh >= p.zone_refresh:
                zones_cache = active_zones_at(pivots, t, tol, p.lookback, p.min_touches)
                last_refresh = t
            zones = zones_cache
            if not zones:
                continue
            price = c[t]
            support, resistance = nearest_levels(zones, price)

            setup = None

            # ---- LONG ----
            if long_ok:
                if p.use_reversal and support is not None:
                    touched = l[t] <= support.upper + touch_tol and c[t] >= support.lower
                    if touched and pat.bullish_rejection(o, h, l, c, t):
                        stop = self._stop(+1, price, support.lower - buf, atr_t)
                        target = self._target(+1, price, stop, resistance, atr_t)
                        setup = self._mk(t, +1, price, stop, target, "reversal-sup")
                if setup is None and p.use_break_retest:
                    z = self._broken_up_zone(zones, c, t, tol, p.break_lookback)
                    if z is not None:
                        touched = l[t] <= z.upper + touch_tol and c[t] >= z.lower
                        if touched and pat.bullish_rejection(o, h, l, c, t):
                            stop = self._stop(+1, price, z.lower - buf, atr_t)
                            res = resistance if resistance and resistance.price > price else None
                            target = self._target(+1, price, stop, res, atr_t)
                            setup = self._mk(t, +1, price, stop, target, "break-retest-up")

            # ---- SHORT ----
            if setup is None and short_ok:
                if p.use_reversal and resistance is not None:
                    touched = h[t] >= resistance.lower - touch_tol and c[t] <= resistance.upper
                    if touched and pat.bearish_rejection(o, h, l, c, t):
                        stop = self._stop(-1, price, resistance.upper + buf, atr_t)
                        target = self._target(-1, price, stop, support, atr_t)
                        setup = self._mk(t, -1, price, stop, target, "reversal-res")
                if setup is None and p.use_break_retest:
                    z = self._broken_down_zone(zones, c, t, tol, p.break_lookback)
                    if z is not None:
                        touched = h[t] >= z.lower - touch_tol and c[t] <= z.upper
                        if touched and pat.bearish_rejection(o, h, l, c, t):
                            stop = self._stop(-1, price, z.upper + buf, atr_t)
                            sup = support if support and support.price < price else None
                            target = self._target(-1, price, stop, sup, atr_t)
                            setup = self._mk(t, -1, price, stop, target, "break-retest-dn")

            if setup is not None:
                setups.append(setup)

        return setups

    def _stop(self, direction, price, zone_stop, atr_t):
        """Stop: theo rìa vùng, hoặc override theo ATR nếu sl_atr>0."""
        if self.p.sl_atr > 0:
            return price - direction * self.p.sl_atr * atr_t
        return zone_stop

    def _target(self, direction, price, stop, opp_zone, atr_t):
        """Target: TP cố định theo ATR (winrate cao) hoặc theo vùng đối diện."""
        if self.p.exit_mode == "atr":
            return price + direction * self.p.tp_atr * atr_t
        if opp_zone is not None:
            return opp_zone.price
        return price + direction * self.p.fallback_rr * abs(price - stop)

    def _mk(self, t, direction, price, stop, target, reason):
        """Tạo setup nếu thỏa lọc reward:risk (dùng close[t] làm proxy entry)."""
        risk = abs(price - stop)
        reward = abs(target - price)
        if risk <= 0 or (self.p.min_rr > 0 and reward / risk < self.p.min_rr):
            return None
        # target/stop phải đúng phía.
        if direction > 0 and not (stop < price < target):
            return None
        if direction < 0 and not (target < price < stop):
            return None
        return TradeSetup(entry_pos=t, direction=direction, stop=stop,
                          target=target, reason=reason)

    @staticmethod
    def _broken_up_zone(zones, c, t, tol, lookback):
        """Vùng nằm dưới giá hiện tại, vừa bị phá LÊN gần đây (kháng cự -> hỗ trợ)."""
        lo = max(0, t - lookback)
        window_min = c[lo:t].min() if t > lo else c[t]
        best = None
        for z in zones:
            if z.price < c[t] and window_min < z.lower and c[t - 1] > z.upper:
                if best is None or z.price > best.price:  # gần giá nhất
                    best = z
        return best

    @staticmethod
    def _broken_down_zone(zones, c, t, tol, lookback):
        """Vùng nằm trên giá hiện tại, vừa bị phá XUỐNG gần đây (hỗ trợ -> kháng cự)."""
        lo = max(0, t - lookback)
        window_max = c[lo:t].max() if t > lo else c[t]
        best = None
        for z in zones:
            if z.price > c[t] and window_max > z.upper and c[t - 1] < z.lower:
                if best is None or z.price < best.price:
                    best = z
        return best


def d1_trend_from(df_d1: pd.DataFrame, ema_period: int = 50) -> pd.Series:
    """Bias xu hướng D1: +1 uptrend, -1 downtrend, 0 không rõ.

    Uptrend: close > EMA và EMA đang dốc lên. Dùng dữ liệu D1 ĐÃ ĐÓNG (shift 1)
    để khi map sang H4 không nhìn trộm tương lai.
    """
    from src.strategies.indicators import ema
    e = ema(df_d1["close"], ema_period)
    up = (df_d1["close"] > e) & (e.diff() > 0)
    dn = (df_d1["close"] < e) & (e.diff() < 0)
    trend = pd.Series(0, index=df_d1.index, dtype=int)
    trend[up] = 1
    trend[dn] = -1
    return trend.shift(1).fillna(0).astype(int)


def map_d1_to_h4(d1_trend: pd.Series, h4_index: pd.DatetimeIndex) -> pd.Series:
    """Gán bias D1 cho từng nến H4 theo thời gian (as-of, chỉ lấy D1 đã đóng).

    reindex + ffill: mỗi nến H4 nhận giá trị D1 gần nhất có timestamp <= nó.
    """
    mapped = d1_trend.sort_index().reindex(h4_index, method="ffill")
    return mapped.fillna(0).astype(int)
