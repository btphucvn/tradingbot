# EA cho MetaTrader 5

Hai EA trong thư mục này (cùng cách cài: chép vào `MQL5\Experts\`, compile F7):

- **`BreakoutTrendCTA.mq5`** ⭐ — chiến thuật chính đã verify (breakout cưỡi-trend +
  trailing + sizing theo % rủi ro). Đây là EA NÊN DÙNG. Xem mục dưới cùng.
- `DonchianBreakout.mq5` — baseline cũ (chỉ để tham khảo/so sánh).

---

## ⭐ BreakoutTrendCTA — chiến thuật chính (đa thị trường)

Port từ `src/strategies/breakout.py` + `src/backtest/broker.py`. Logic:
- Vào lệnh khi giá đóng cửa phá đỉnh/đáy **5 nến** (cả 2 chiều, không lọc trend).
- Stop ban đầu = **3×ATR**; **trailing stop = 5×ATR** (chỉ siết, để winners chạy).
- Không chốt lời cố định — thoát khi chạm trailing stop.
- Khối lượng = **2% rủi ro** mỗi lệnh (tự quy đổi tiền tệ qua tick value của MT5).

### Cách dùng cho DANH MỤC 4 thị trường
Gắn EA vào **4 chart H4** riêng (mỗi cái 1 magic khác nhau nếu cùng tài khoản):
| Chart | InpMagic gợi ý | Vốn phân bổ |
|-------|---------------|-------------|
| GBP/JPY H4 | 770055 | 1/4 |
| XAU/USD (Gold) H4 | 770056 | 1/4 |
| WTI/USOIL H4 | 770057 | 1/4 |
| Coffee H4 | 770058 | 1/4 |

> Mỗi EA tự sizing theo % equity tài khoản. Để chia vốn thật cho danh mục, giảm
> `InpRiskPct` (vd 0.5% mỗi lệnh nếu chạy 4 chart cùng lúc để tổng rủi ro ~2%).

### Tham số mặc định (đã verify backtest Python)
| Input | Mặc định | Ý nghĩa |
|-------|----------|---------|
| InpEntryPeriod | 5 | Donchian phá kênh 5 nến |
| InpSlAtr | 3.0 | Stop ban đầu 3×ATR |
| InpTrailAtr | 5.0 | Trailing 5×ATR |
| InpRiskPct | 2.0 | Rủi ro 2%/lệnh (giảm xuống nếu chạy nhiều chart) |

### ⚠️ Lưu ý
- Backtest Python: GBP/JPY đơn risk 2% → CAGR ~14%, DD −42%, 675 lệnh; danh mục 4
  thị trường → CAGR ~11%, DD −20%. **KHÔNG phải CAGR 35%** (xem
  `docs/portfolio-cta-architecture.md` về vì sao 35%/DD40% bất khả thi honest).
- **Chạy DEMO ≥6 tháng** trước khi nghĩ tới tiền thật — spread/slippage thật trên
  GBP/JPY/Gold/Oil/Coffee có thể khác backtest.
- Strategy Tester dùng **"Every tick based on real ticks"**, ký hiệu symbol đúng
  của broker (Gold thường là XAUUSD, dầu là USOIL/WTI, coffee tùy broker).

---

# (Cũ) Donchian Breakout EA — hướng dẫn backtest trong MT5

EA `DonchianBreakout.mq5` port từ chiến lược Python trong repo này, để chạy
trong **Strategy Tester** của MetaTrader 5.

## 1. Chép file vào MT5

1. Mở **MetaTrader 5** → menu **File → Open Data Folder**
2. Vào thư mục `MQL5\Experts\`
3. Chép `DonchianBreakout.mq5` vào đó

> Từ WSL, thư mục này thường ở:
> `/mnt/c/Users/<tên_user>/AppData/Roaming/MetaQuotes/Terminal/<hash>/MQL5/Experts/`
> (dùng "Open Data Folder" trong MT5 để chắc đường dẫn đúng)

## 2. Biên dịch

1. Mở **MetaEditor** (F4 trong MT5, hoặc icon)
2. Mở `DonchianBreakout.mq5` → bấm **Compile** (F7)
3. Không có lỗi → EA xuất hiện trong Navigator của MT5

## 3. Tải dữ liệu lịch sử

- **View → Symbols** → chọn cặp (vd EURUSD) → tab **Bars/Ticks** → tải về
- Hoặc Strategy Tester sẽ tự tải khi chạy lần đầu

## 4. Chạy Strategy Tester

1. Mở Strategy Tester: **View → Strategy Tester** (Ctrl+R)
2. Chọn:
   - **Expert**: DonchianBreakout
   - **Symbol**: EURUSD
   - **Period**: D1 (khung ngày, khớp với backtest Python)
   - **Date**: 2010.01.01 → nay
   - **Modeling**: "Every tick based on real ticks" (chính xác nhất) hoặc
     "1 minute OHLC" (nhanh hơn)
   - **Deposit**: 10000 USD, **Leverage** theo broker
3. Bấm **Start**

## 5. Tham số (input) chỉnh trong tab Inputs

| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| InpEntryPeriod | 20 | Số bar tính kênh vào lệnh |
| InpExitPeriod | 10 | Số bar tính kênh thoát (phải < entry) |
| InpAllowShort | true | Cho phép bán khống |
| InpLots | 0.10 | Khối lượng cố định (lot) |
| InpRiskPercent | 0.0 | >0 = size theo % equity (bỏ qua InpLots) |
| InpMagic | 990021 | Magic number |

## ⚠️ Lưu ý quan trọng

- **Backtest Python (-74%) và MT5 sẽ KHÁC nhau đôi chút** vì: data của broker
  khác Dukascopy, mô hình spread/swap khác, cách khớp lệnh khác. Đừng ngạc nhiên.
- EA này hành động **mỗi khi có bar mới** (đóng nến) — đúng logic close-of-bar
  của bản Python, tránh nhìn trộm tương lai.
- Đây là **baseline để học**, không phải chiến lược chắc lãi. Bản Python đã cho
  thấy nó thua trên EURUSD D1 2010–2024.
- Muốn dùng tối ưu tham số: bật **Optimization** trong Strategy Tester, chọn dải
  giá trị cho InpEntryPeriod/InpExitPeriod. **Cẩn thận overfit** — luôn kiểm
  forward (out-of-sample) sau khi tối ưu.
