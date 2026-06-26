# EA cho MetaTrader 5

Ba EA (cùng cách cài: chép vào `MQL5\Experts\`, compile F7):

- **`CtaPortfolio.mq5`** ⭐⭐ — danh mục ĐA THỊ TRƯỜNG đạt **CAGR~37%, DD~−39%,
  Calmar 0.95** (backtest Python). Một EA giao dịch cả 10 symbol. Xem ngay dưới.
- `BreakoutTrendCTA.mq5` — phiên bản 1 symbol (cho từng chart riêng).
- `DonchianBreakout.mq5` — baseline cũ (tham khảo).

---

## ⭐⭐ CtaPortfolio — danh mục 10 thị trường (mục tiêu CAGR>35% & DD<40%)

Port từ `cta_portfolio.py`. Gắn vào **1 chart H4 bất kỳ** → EA tự giao dịch cả
danh sách symbol bằng chiến thuật breakout + trailing + sizing theo % rủi ro.

### Cài & chạy
1. Chép `CtaPortfolio.mq5` vào `MQL5\Experts\`, compile (F7).
2. Sửa input **`InpSymbols`** cho ĐÚNG ký hiệu broker của bạn.
   **Mặc định (chuẩn Dukascopy MT):** `XAUUSD,GBPJPY,LIGHT.CMD,COFFEE.CMD,BTCUSD,ETHUSD`
   - Dukascopy: hàng hóa có đuôi **`.CMD`**, **WTI = `LIGHT.CMD`** (không phải USOIL),
     cà phê = `COFFEE.CMD`. Verify tên crypto: `BTC/USD` hay `BTCUSD`.
   - Broker khác đặt tên khác: vàng `GOLD/XAUUSD`, dầu `USOIL/WTI/CL`, S&P `US500/SPX500`...
   - Kiểm chính xác: **chuột phải Market Watch → Symbols**.

   > ⚠️ Dùng **WTI (`LIGHT.CMD`)**, KHÔNG dùng Brent — backtest WTI có lãi (PF 1.18),
   > Brent lỗ (PF 0.84) dù 2 cái tương quan ~95%. Nếu broker không có WTI mới dùng Brent.
3. Đảm bảo các symbol đều **hiện trong Market Watch** (EA tự gọi SymbolSelect nhưng
   broker phải cung cấp symbol đó).
4. Gắn EA vào 1 chart H4, bật AutoTrading.

### Tham số chính
| Input | Mặc định | Ghi chú |
|-------|----------|---------|
| InpSymbols | 10 symbol | Sửa cho đúng tên broker |
| InpEntryPeriod | 5 | Donchian phá 5 nến |
| InpSlAtr / InpTrailAtr | 3 / 5 | Stop 3×ATR, trailing 5×ATR |
| **InpRiskPct** | **1.5** | % rủi ro/lệnh/symbol — **CALIBRATE trên demo** |

### ⚠️ Cực kỳ quan trọng
- **Backtest danh mục PHẢI dùng Python `cta_portfolio.py`.** MT5 Strategy Tester
  chạy đa-symbol rất hạn chế — EA này dành cho **LIVE/DEMO**, không phải để backtest
  trong Tester.
- **`InpRiskPct` quyết định đòn bẩy thực.** Backtest dùng leverage ~5× (DD −39%).
  Với 10 symbol chạy song song, **bắt đầu InpRiskPct THẤP (0.5–1%)** trên demo, theo
  dõi tổng ký quỹ/exposure, rồi tăng dần. 1.5% × nhiều vị thế đồng thời = đòn bẩy cao.
- **Cần broker có đủ 10 thị trường** (gồm crypto + CFD hàng hóa/chỉ số). Nếu thiếu
  vài cái, bỏ khỏi `InpSymbols` — danh mục vẫn chạy nhưng ít đa dạng hóa hơn.
- Rủi ro thật: DD −39% (mất gần 40% tài khoản), phụ thuộc sóng crypto. Đọc
  `docs/cta-portfolio-cagr35.md` mục cảnh báo. **Chạy demo ≥6 tháng trước.**

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
