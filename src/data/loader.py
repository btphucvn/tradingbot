"""Tải dữ liệu lịch sử forex từ Dukascopy.

Fetch cả bid và ask để tính spread thật (rất quan trọng cho backtest trung thực).
Kết quả được cache ra CSV để lần sau không phải tải lại.

Cột trả về (giá mid trừ khi ghi rõ):
    open, high, low, close   -> giá mid (trung bình bid/ask)
    volume                   -> volume
    spread                   -> ask_close - bid_close (đơn vị giá, không phải pip)
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import dukascopy_python
import pandas as pd
from dukascopy_python import instruments as duka_instruments

# Map tên cặp -> hằng số instrument của dukascopy.
# Thêm cặp mới ở đây khi cần.
INSTRUMENTS: dict[str, str] = {
    "EURUSD": duka_instruments.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": duka_instruments.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": duka_instruments.INSTRUMENT_FX_MAJORS_USD_JPY,
    "AUDUSD": duka_instruments.INSTRUMENT_FX_MAJORS_AUD_USD,
    "USDCHF": duka_instruments.INSTRUMENT_FX_MAJORS_USD_CHF,
    "USDCAD": duka_instruments.INSTRUMENT_FX_MAJORS_USD_CAD,
    "NZDUSD": duka_instruments.INSTRUMENT_FX_MAJORS_NZD_USD,
    # Crosses / EM (quote != USD -> cần quote_to_usd khi backtest)
    "GBPJPY": duka_instruments.INSTRUMENT_FX_CROSSES_GBP_JPY,
    "EURJPY": duka_instruments.INSTRUMENT_FX_CROSSES_EUR_JPY,
    "AUDJPY": duka_instruments.INSTRUMENT_FX_CROSSES_AUD_JPY,
    "USDTRY": duka_instruments.INSTRUMENT_FX_CROSSES_USD_TRY,
    "USDZAR": duka_instruments.INSTRUMENT_FX_CROSSES_USD_ZAR,
    "USDMXN": duka_instruments.INSTRUMENT_FX_CROSSES_USD_MXN,
    # Đa lớp tài sản (đều quote USD -> quote_to_usd=1, trừ ghi chú)
    "XAUUSD": duka_instruments.INSTRUMENT_FX_METALS_XAU_USD,   # vàng
    "XAGUSD": duka_instruments.INSTRUMENT_FX_METALS_XAG_USD,   # bạc
    "WTI": duka_instruments.INSTRUMENT_CMD_ENERGY_E_LIGHT,     # dầu WTI
    "BRENT": duka_instruments.INSTRUMENT_CMD_ENERGY_E_BRENT,
    "SPX500": duka_instruments.INSTRUMENT_IDX_AMERICA_E_SANDP_500,  # S&P 500
    "NAS100": duka_instruments.INSTRUMENT_IDX_AMERICA_E_NQ_100,
    "COFFEE": duka_instruments.INSTRUMENT_CMD_AGRICULTURAL_COFFEE_CMD_USX,  # giá theo US cents
    "SUGAR": duka_instruments.INSTRUMENT_CMD_AGRICULTURAL_SUGAR_CMD_USD,
    "COPPER": duka_instruments.INSTRUMENT_CMD_METALS_COPPER_CMD_USD,
    "NATGAS": duka_instruments.INSTRUMENT_CMD_ENERGY_GAS_CMD_USD,
    "PLATINUM": duka_instruments.INSTRUMENT_CMD_METALS_XPT_CMD_USD,
    "COCOA": duka_instruments.INSTRUMENT_CMD_AGRICULTURAL_COCOA_CMD_USD,
    "SOYBEAN": duka_instruments.INSTRUMENT_CMD_AGRICULTURAL_SOYBEAN_CMD_USX,
}

# Map khung thời gian -> hằng số interval của dukascopy.
INTERVALS: dict[str, str] = {
    "M1": dukascopy_python.INTERVAL_MIN_1,
    "M5": dukascopy_python.INTERVAL_MIN_5,
    "M15": dukascopy_python.INTERVAL_MIN_15,
    "M30": dukascopy_python.INTERVAL_MIN_30,
    "H1": dukascopy_python.INTERVAL_HOUR_1,
    "H4": dukascopy_python.INTERVAL_HOUR_4,
    "D1": dukascopy_python.INTERVAL_DAY_1,
}

# Kích thước 1 pip theo cặp (cặp có JPY dùng 0.01, còn lại 0.0001).
def pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"


def _fetch_side(symbol: str, interval: str, side: str,
                start: dt.datetime, end: dt.datetime) -> pd.DataFrame:
    return dukascopy_python.fetch(
        INSTRUMENTS[symbol],
        INTERVALS[interval],
        side,
        start,
        end,
    )


def load(
    symbol: str,
    interval: str = "H1",
    start: str | dt.datetime = "2015-01-01",
    end: str | dt.datetime | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Tải OHLC mid + spread cho một cặp tiền.

    Args:
        symbol: vd "EURUSD" (xem INSTRUMENTS).
        interval: vd "H1", "D1" (xem INTERVALS).
        start, end: ngày bắt đầu/kết thúc (str "YYYY-MM-DD" hoặc datetime).
        use_cache: nếu True, đọc/ghi cache CSV để tránh tải lại.
    """
    symbol = symbol.upper()
    if symbol not in INSTRUMENTS:
        raise ValueError(f"Chưa hỗ trợ cặp {symbol!r}. Có: {list(INSTRUMENTS)}")
    if interval not in INTERVALS:
        raise ValueError(f"Khung {interval!r} không hợp lệ. Có: {list(INTERVALS)}")

    start_dt = pd.Timestamp(start).to_pydatetime()
    end_dt = (pd.Timestamp(end) if end else pd.Timestamp.utcnow()).to_pydatetime()

    cache_file = CACHE_DIR / f"{symbol}_{interval}_{start_dt:%Y%m%d}_{end_dt:%Y%m%d}.csv"
    if use_cache and cache_file.exists():
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        df.index.name = "timestamp"
        return df

    bid = _fetch_side(symbol, interval, dukascopy_python.OFFER_SIDE_BID, start_dt, end_dt)
    ask = _fetch_side(symbol, interval, dukascopy_python.OFFER_SIDE_ASK, start_dt, end_dt)

    if bid.empty or ask.empty:
        raise RuntimeError(f"Dukascopy trả về rỗng cho {symbol} {interval} {start_dt}..{end_dt}")

    # Căn theo timestamp chung của cả hai phía.
    common = bid.index.intersection(ask.index)
    bid, ask = bid.loc[common], ask.loc[common]

    df = pd.DataFrame(index=common)
    for col in ("open", "high", "low", "close"):
        df[col] = (bid[col] + ask[col]) / 2.0  # giá mid
    df["volume"] = bid["volume"]
    df["spread"] = (ask["close"] - bid["close"]).clip(lower=0)
    df.index.name = "timestamp"

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file)

    return df


if __name__ == "__main__":
    # Test nhanh: tải 1 tháng EUR/USD H1 và in thống kê spread.
    d = load("EURUSD", "H1", "2024-01-01", "2024-02-01")
    print(d.head())
    print(f"\n{len(d)} bars | spread trung bình = "
          f"{d['spread'].mean() / pip_size('EURUSD'):.2f} pips")
