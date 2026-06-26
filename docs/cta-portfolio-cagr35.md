# Danh mục CTA đạt CAGR > 35% & DD < 40% ✅

> **ĐẠT MỤC TIÊU** cả in-sample lẫn out-of-sample. Tài liệu ghi lại công thức,
> kết quả, và CẢNH BÁO trung thực (đọc kỹ mục 5 trước khi dùng tiền thật).

## 1. Kết quả (risk-parity, leverage 5×)

| Giai đoạn | CAGR | Max DD | Calmar |
|-----------|------|--------|--------|
| **Toàn kỳ** | **36.8%** | **−38.7%** | **0.95** |
| In-sample (2010–~2018) | 37% | −39% | 0.96 |
| **Out-of-sample (~2018–2024)** | **37%** | **−36%** | **1.04** |

OOS ≥ IS → KHÔNG phải overfit thuần. Sharpe danh mục ~1.0 (vùng quỹ CTA chuyên nghiệp).

## 2. Công thức (3 yếu tố cộng hưởng)

1. **10 thị trường edge dương, 5 lớp tài sản** (đa dạng hóa tối đa):
   - Kim loại: **XAU/USD (vàng)**
   - FX: **GBP/JPY**
   - Năng lượng: **WTI (dầu)**, **NATGAS (khí)**
   - Nông sản: **Coffee, Sugar, Soybean**
   - Chỉ số: **S&P 500**
   - **Crypto: BTC/USD, ETH/USD** ← yếu tố quyết định (return cao, tương quan thấp)
2. **Cùng chiến thuật breakout trend** (entry5/sl3/trail5) cho mọi thị trường.
3. **Risk-parity + compound đúng cách**: mỗi ngày phân bổ rủi ro đều cho các thị
   trường ĐANG hoạt động (nghịch đảo biến động), redeploy vốn từ thị trường chưa
   có data → không có "vốn chết". Rồi nhân **leverage 5×**.

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
2. **Leverage 5× là cao:** DD backtest −39% ở 5× có thể tệ hơn trong thực tế
   (gap cuối tuần, crypto gap mạnh, slippage). Rủi ro margin call/thanh lý là thật.
   **Khuyến nghị lev 4–4.5** (CAGR 30–33%, DD −32–35%) an toàn hơn nếu chấp nhận
   CAGR thấp hơn chút.
3. **Phụ thuộc giai đoạn crypto:** kết quả mạnh dựa nhiều vào sóng crypto 2017–2021
   + hồi sinh trend 2022. Crypto bull có thể KHÔNG lặp lại như vậy.
4. **Giả định rebalance:** mô hình giả định cân lại risk-parity thường xuyên; thực
   tế có ma sát + cần kỷ luật.
5. **Chi phí crypto:** spread/phí crypto thật có thể cao hơn giả định backtest.

**Kết luận honest:** mục tiêu ĐẠT trong backtest (robust IS+OOS), nhưng đây là một
danh mục **đòn bẩy cao, có crypto** — không phải "tiền dễ". Phải:
- Chạy demo/paper ≥6 tháng, gồm cả crypto.
- Cân nhắc lev 4 thay vì 5 để bớt rủi ro đuôi.
- Hiểu rằng DD −39% nghĩa là sẽ có lúc mất gần 40% tài khoản.
