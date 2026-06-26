# tradingbot

Bot giao dịch forex + khung backtest **trung thực** (tính spread thật, swap,
slippage, không nhìn trộm tương lai, kiểm out-of-sample). Dữ liệu lịch sử lấy từ
**Dukascopy** (`dukascopy-python`).

## Cài đặt

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Cấu trúc

```
src/data/loader.py            tải OHLC + spread thật từ Dukascopy (cache CSV)
src/backtest/engine.py        engine signal-based ({-1,0,+1}, sizing exposure)
src/backtest/broker.py        engine cấp-lệnh: SL/TP trong nến, sizing theo % rủi ro
src/backtest/metrics.py       Sharpe, Sortino, max drawdown, profit factor, winrate
src/strategies/levels.py      phát hiện vùng kháng cự/hỗ trợ (pivot + cluster)
src/strategies/patterns.py    nến price action: pin bar, engulfing, rejection
src/strategies/price_action_sr.py  chiến lược S/R: đảo chiều + break-retest, lọc trend D1
run_backtest.py               backtest Donchian baseline
run_price_action.py           backtest price action S/R (H4)
sweep_price_action.py         tự động quét cấu hình, xếp hạng theo winrate
mql5/DonchianBreakout.mq5     EA cho MetaTrader 5 Strategy Tester
```

## Lưu ý dữ liệu Dukascopy

- **D1 và H4 tải nhanh** (vài giây/nhiều năm — endpoint candle tổng hợp).
- **H1 trở xuống tải rất chậm** (tải file tick từng giờ). Dùng D1/H4 cho lịch sử dài.

## Cấu hình tốt nhất hiện tại (winrate cao)

Price action S/R, H4, EUR/USD, exit theo ATR (TP gần + SL xa) lọc thuận trend D1:

```bash
.venv/bin/python run_price_action.py --symbol EURUSD --start 2010-01-01 --end 2024-01-01 \
  --exit-mode atr --tp-atr 0.75 --sl-atr 2.5 --mode trend --min-touches 2 --min-rr 0
```

Kết quả verify (2010–2024):

| Giai đoạn | Winrate | Return | Profit factor | Max DD |
|-----------|---------|--------|---------------|--------|
| In-sample (2010–2019) | 74.3% | +5.9% | 1.02 | −28.6% |
| Out-of-sample (2019–2024) | 77.0% | +14.2% | 1.10 | −9.5% |
| Toàn bộ 14 năm | 75.2% | +21% | 1.04 | −29.7% |

## Cấu hình đạt x5 (GBP/JPY, breakout cưỡi-trend)

Mục tiêu x5 lợi nhuận + ≥200 lệnh (bỏ ràng buộc winrate) — đạt được bằng breakout
ngắn + trailing stop rộng, cưỡi xu hướng dài của GBP/JPY:

```bash
.venv/bin/python run_breakout.py --symbol GBPJPY --entry 5 --sl-atr 3 --trail-atr 5 \
  --no-trend --risks 0.02,0.03
```

| Risk | x | CAGR | Winrate | PF | Max DD | Lệnh |
|------|---|------|---------|-----|--------|------|
| 2% | 6.4x | 14.1% | 39% | 1.27 | −42% | 675 |
| 3% | 12.9x | 20% | 39% | 1.22 | −56% | 675 |

Out-of-sample (2019–2024) PF 1.15, CAGR +10.8% → edge thật, không overfit thuần.

⚠️ **Cái giá:** drawdown −42% (risk 2%) tới −56% (risk 3%). Edge phụ thuộc regime
JPY yếu/trend bền (carry trade); nếu regime đổi, edge giảm. Forward kỳ vọng ~OOS
(~10%/năm). Khuyến nghị risk 2%. Phải chịu được mất ~nửa tài khoản lúc drawdown.

---

⚠️ **Đọc kỹ (cấu hình winrate cao bên dưới):** winrate ~75% chủ yếu đến từ **hình học TP/SL** (TP=0.75 ATR gần,
SL=2.5 ATR xa → xác suất chạm TP trước ≈ 2.5/3.25 ≈ 77%), KHÔNG phải "phép màu dự
đoán". Mỗi lệnh thua ≈ 3.3 lần một lệnh thắng, nên lợi nhuận mỏng (PF ~1.04,
~1.4%/năm). Đây là kết quả TRUNG THỰC, có lãi nhẹ và winrate cao bền vững, nhưng
KHÔNG phải máy in tiền. Luôn đánh giá out-of-sample.
