# Chiến thuật danh mục CTA (6 thị trường) — bản chính thức

> Đạt mục tiêu **CAGR > 35% & DD < 40%** trên backtest. Tài liệu này là spec đầy
> đủ: thị trường, luật giao dịch, kết quả, và CẢNH BÁO trung thực (mục 6).

## 1. Danh mục (6 thị trường, 5 lớp tài sản)

| Thị trường | Mã | Lớp | Edge lẻ (Calmar) |
|-----------|-----|-----|------------------|
| Vàng | XAUUSD | Kim loại | 0.56 |
| GBP/JPY | GBPJPY | Forex | 0.34 |
| Dầu WTI | WTI / USOIL | Năng lượng | 0.27 |
| Cà phê | COFFEE | Nông sản | 0.31 |
| Bitcoin | BTCUSD | Crypto | 0.47 |
| Ethereum | ETHUSD | Crypto | 0.44 |

Đây là 6 thị trường **edge mạnh nhất, ít tương quan**. (Bỏ sugar/soybean/natgas/SPX
vì edge yếu + khó tìm broker → Sharpe còn TĂNG.)

## 2. Luật giao dịch (áp dụng GIỐNG NHAU cho cả 6, khung H4)

- **Vào lệnh:** giá đóng cửa phá **đỉnh/đáy 5 nến** gần nhất → mua/bán ở nến kế tiếp.
  Giao dịch cả 2 chiều, không lọc trend. Mỗi thị trường tối đa 1 vị thế.
- **Stop ban đầu:** entry ∓ **3 × ATR(14)**.
- **Trailing stop:** đỉnh/đáy kể từ khi vào lệnh ∓ **5 × ATR**, chỉ siết không nới.
- **Thoát:** không TP cố định — chỉ thoát khi chạm trailing stop (để winners chạy).
- **Sizing:** mỗi lệnh rủi ro **% cố định** của vốn (ATR-based → tự cân biến động).

## 3. Ghép danh mục (yếu tố quyết định nâng Calmar)

- **Risk-parity + compound đúng cách:** mỗi ngày phân bổ rủi ro đều cho các thị
  trường ĐANG hoạt động (nghịch đảo biến động), không để "vốn chết". *Đây là phát
  hiện kỹ thuật quan trọng nhất — mô hình equity-sum cũ để vốn chết → kéo Calmar
  từ 0.95 xuống 0.69.*
- **Đòn bẩy ~4.5×** để scale danh mục Sharpe ~1.0 lên CAGR mục tiêu.
- File: `cta_portfolio.py`.

## 4. Kết quả

### Toàn kỳ 2010–2024 (lev 4×, rổ 6)
CAGR 37%, DD −35%, Calmar 1.06. IS Calmar 1.24, OOS 0.89. Sharpe 1.09.

### Gần đây 2018–2026 (lev 4.5×) — QUAN TRỌNG, sát thực tế hơn
| Giai đoạn | CAGR | DD | Calmar |
|-----------|------|-----|--------|
| **Toàn kỳ 2018–2026** | **36%** | **−39%** | 0.92 |
| 2018–2022 (bùng nổ) | 44% | −39% | 1.14 |
| **2022–2026 (gần đây)** | **23%** | −30% | **0.76** |

→ Con số 36% bị "thổi" bởi giai đoạn vàng son 2018–2022 (crypto bull + COVID + trend
hàng hóa 2022). **Vài năm gần đây hệ thống cho ~23%/năm, Calmar 0.76** — vẫn rất tốt
nhưng dưới mốc 35%. Equity vẫn tăng đều qua 2024–2026.

## 5. Tái tạo & triển khai

- Backtest: `.venv/bin/python cta_portfolio.py` (sửa `START/END/MARKETS` trong file).
- EA MT5: `mql5/CtaPortfolio.mq5` — gắn 1 chart H4, sửa `InpSymbols` cho đúng tên
  broker, **bắt đầu InpRiskPct thấp (0.5–1%)** rồi tăng dần trên demo.
- Backtest danh mục PHẢI dùng Python; MT5 Strategy Tester đa-symbol rất hạn chế.

## 6. ⚠️ CẢNH BÁO TRUNG THỰC (đọc trước khi dùng tiền thật)

1. **Kỳ vọng forward ≈ chế độ gần đây (~20–25%/năm), KHÔNG phải 36%.** 36% cần chế
   độ trend/crypto thuận lợi quay lại — không đảm bảo.
2. **Crypto chiếm 1/3 danh mục** (BTC+ETH tương quan ~0.8 ≈ 1 khối). Phụ thuộc NẶNG
   vào crypto — đây là rủi ro tập trung lớn nhất. Crypto gấu dài → Calmar tụt mạnh.
3. **Leverage 4–4.5× cao:** DD backtest −35÷39% có thể tệ hơn thực tế (gap cuối tuần,
   crypto gap, slippage). Margin call là rủi ro thật. An toàn hơn: lev 3× (~24%/năm).
4. **Selection bias:** 6 thị trường được chọn vì edge dương đo trên dữ liệu quá khứ
   → OOS hơi lạc quan.
5. **Phải chịu DD ~−35÷39%** = mất hơn 1/3 tài khoản lúc xấu. Cần kỷ luật giữ hệ thống.
6. **BẮT BUỘC chạy demo ≥6 tháng** (gồm crypto) với spread/phí thật trước khi vào tiền thật.
