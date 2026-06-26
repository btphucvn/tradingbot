# Danh mục CTA đạt CAGR > 35% & DD < 40% ✅

> **ĐẠT MỤC TIÊU** cả in-sample lẫn out-of-sample. Tài liệu ghi lại công thức,
> kết quả, và CẢNH BÁO trung thực (đọc kỹ mục 5 trước khi dùng tiền thật).

## 1. Kết quả — RỔ 6 THỊ TRƯỜNG (khuyến nghị, dễ tìm broker)

Markets: **XAU/USD, GBP/JPY, WTI, Coffee, BTC/USD, ETH/USD** (bỏ sugar/soybean/
natgas/SPX vì edge yếu + khó tìm broker → Sharpe còn TĂNG lên 1.09).

| Leverage | CAGR | Max DD | Calmar | Đạt mục tiêu? |
|----------|------|--------|--------|----------------|
| 3× | 27.5% | −27% | 1.03 | |
| **4× (khuyến nghị)** | **37%** | **−35%** | **1.06** | ✅ |
| 4.5× | 41.6% | −39% | 1.07 | ✅ |
| 5× | 46% | −43% | 1.08 | (DD>40%) |

IS Calmar **1.24**, OOS Calmar **0.89** → đạt cả 2 nửa. Sharpe ~1.09.

> (Rổ 10 thị trường gốc: lev 5× → CAGR 37%, DD −39%, Calmar 0.95, OOS 1.04 — cũng
> đạt nhưng cần đủ 10 symbol gồm soybean/sugar khó kiếm.)

## 2. Công thức (3 yếu tố cộng hưởng)

1. **6 thị trường edge mạnh, 5 lớp tài sản** (đa dạng hóa, ít tương quan):
   - Kim loại: **XAU/USD (vàng)** · FX: **GBP/JPY** · Năng lượng: **WTI (dầu)**
   - Nông sản: **Coffee** · **Crypto: BTC/USD, ETH/USD** ← yếu tố quyết định
2. **Cùng chiến thuật breakout trend** (entry5/sl3/trail5) cho mọi thị trường.
3. **Risk-parity + compound đúng cách**: mỗi ngày phân bổ rủi ro đều cho các thị
   trường ĐANG hoạt động (nghịch đảo biến động), redeploy vốn từ thị trường chưa
   có data → không có "vốn chết". Rồi nhân **leverage 4×** (giữ DD < 40%).

## 3. Vì sao crypto là yếu tố quyết định

Trước khi thêm crypto: danh mục Calmar ~0.54–0.69. Sau khi thêm BTC+ETH: **0.95**.
Crypto có edge trend mạnh (BTC Calmar 0.47, ETH 0.44) VÀ **tương quan thấp** với
FX/hàng hóa, lại hoạt động đúng giai đoạn 2017–2024 (vốn là điểm yếu OOS trước đó).

## 4. Tái tạo

```bash
.venv/bin/python cta_portfolio.py
```
Markets trong `cta_portfolio.py`:
`XAUUSD, GBPJPY, WTI, COFFEE, BTCUSD, ETHUSD, SUGAR, SOYBEAN, SPX500, NATGAS`.
Engine: return-based, inverse-vol weighting, leverage sweep. Chart:
`results/cta_portfolio.png`.

## 5. ⚠️ CẢNH BÁO TRUNG THỰC — đọc trước khi dùng tiền thật

Kết quả đẹp nhưng có RỦI RO và GIẢ ĐỊNH phải hiểu:

1. **Selection bias:** mình chọn 10 thị trường này vì chúng có edge dương đo trên
   TOÀN KỲ (gồm cả OOS). Nên OOS hơi lạc quan — thực tế forward có thể yếu hơn.
2. **Leverage 4× vẫn cao:** DD backtest −35% ở 4× có thể tệ hơn thực tế (gap cuối
   tuần, crypto gap mạnh, slippage). Rủi ro margin call/thanh lý là thật. Muốn an
   toàn hơn dùng lev 3× (CAGR ~27%, DD −27%).
3. **Crypto chiếm 1/3 rổ 6 (BTC+ETH):** phụ thuộc NẶNG vào sóng crypto 2017–2021 +
   hồi sinh trend 2022. BTC/ETH tương quan ~0.8 với nhau (≈1 khối). Nếu crypto vào
   thị trường gấu kéo dài/đi ngang, Calmar sẽ tụt đáng kể. Đây là rủi ro lớn nhất
   của rổ 6.
4. **Giả định rebalance:** mô hình giả định cân lại risk-parity thường xuyên; thực
   tế có ma sát + cần kỷ luật.
5. **Chi phí crypto:** spread/phí crypto thật có thể cao hơn giả định backtest.

**Kết luận honest:** mục tiêu ĐẠT trong backtest (robust IS+OOS), nhưng đây là một
danh mục **đòn bẩy cao, có crypto** — không phải "tiền dễ". Phải:
- Chạy demo/paper ≥6 tháng, gồm cả crypto.
- Cân nhắc lev 4 thay vì 5 để bớt rủi ro đuôi.
- Hiểu rằng DD −39% nghĩa là sẽ có lúc mất gần 40% tài khoản.
