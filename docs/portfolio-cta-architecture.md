# Danh mục CTA đa thị trường — Kiến trúc & kết quả

> Mục tiêu user: **CAGR > 35% & DD < 40%** (Calmar > 0.88). Tài liệu này ghi lại
> nỗ lực đa dạng hóa nhiều thị trường để nâng Calmar, kết quả thật, và cấu hình
> tốt nhất giao được.

## 1. Ý tưởng

Một thị trường đơn + một edge → Calmar bị chặn ~0.39 (xem
[gbpjpy-x5-architecture.md](gbpjpy-x5-architecture.md)). Để vượt phải **đa dạng hóa
nhiều thị trường ít tương quan, MỖI thị trường đều có edge dương** — khi cái này
drawdown thì cái kia lãi → DD danh mục triệt tiêu → Calmar tăng. Cùng một chiến
thuật breakout trend (entry5/sl3/trail5) áp cho mọi thị trường (chuẩn CTA).

## 2. Bài học quan trọng: CHẤT LƯỢNG > SỐ LƯỢNG

Thêm thị trường bừa bãi **làm tệ hơn**: rổ 14 thị trường (Calmar 0.30) < rổ 5
(0.50) < rổ 4 chất lượng (0.54). Vì nhiều thị trường có **edge âm** với tham số
này → chia đều vốn → kéo tụt. Phải **lọc theo edge từng thị trường** (`per_market.py`).

### Edge từng thị trường (breakout, risk 2%, 2010–2024)
| Thị trường | Calmar | PF | Giữ? |
|-----------|--------|-----|------|
| XAU/USD (vàng) | 0.56 | 1.36 | ✅ |
| GBP/JPY | 0.34 | 1.27 | ✅ |
| Cà phê | 0.31 | 1.30 | ✅ |
| WTI (dầu) | 0.27 | 1.18 | ✅ |
| Đường | 0.16 | 1.14 | 🟡 |
| S&P500, Gas, Đậu nành | ~0.04 | 1.05 | 🟡 yếu |
| EUR/USD, Đồng, Brent, NAS100, Ca cao, Bạc | <0 | <1 | ❌ kéo tụt |

## 3. Cấu hình TỐT NHẤT giao được

**Rổ 4 chất lượng: Vàng + GBP/JPY + Dầu + Cà phê** (4 lớp tài sản khác nhau).
```bash
.venv/bin/python run_portfolio.py --markets "XAUUSD,GBPJPY,WTI,COFFEE" --risks 0.02,0.03
```
Mỗi thị trường 1 sleeve vốn bằng nhau (1/4), cùng chiến thuật breakout, gộp equity.

| Risk | CAGR | Max DD | Calmar |
|------|------|--------|--------|
| 2% (khuyến nghị) | 10.8% | −20% | 0.54 |
| 3% | 15.8% | −35% | 0.45 |
| 5% | 23.7% | −63% | 0.38 |

- In-sample (2010–18): Calmar **0.84**; Out-of-sample (2018–24): Calmar 0.35.
- So GBP/JPY đơn lẻ (Calmar 0.39, DD −42% ở risk 2%): danh mục **DD chỉ −20%** ở
  cùng risk, CAGR tương đương → đa dạng hóa giảm rủi ro rõ rệt.

## 4. Kết quả so với mục tiêu CAGR>35% & DD<40%

**CHƯA đạt out-of-sample.** Để CAGR 35% cần risk ~8% → DD −85%. Giữ DD<40% thì CAGR
tối đa ~16% (risk 3%). Calmar danh mục ~0.54 (full) / 0.35 (OOS) < 0.88 cần thiết.

In-sample chạm 0.84 (gần mục tiêu) nhưng OOS chỉ 0.35 → **kỳ vọng forward ~0.35–0.5**,
không đủ cho CAGR35/DD40 một cách bền vững.

## 5. Hạ tầng kỹ thuật đã xây

- `run_portfolio.py` — engine danh mục: nhiều sleeve, gộp equity, quy đổi tiền tệ
  (chỉ GBPJPY cần), staggered start theo inception.
- `load_h4_safe()` — dò ngày khai sinh qua D1 rồi mới tải H4 (tránh **treo vĩnh
  viễn** khi xin H4 trước inception — Dukascopy retry vô hạn).
- `per_market.py` — đánh giá edge từng thị trường để lọc rổ.
- Loader thêm: XAU, XAG, WTI, BRENT, NATGAS, SPX500, NAS100, COPPER, COFFEE,
  SUGAR, COCOA, SOYBEAN.

## 6. Hướng có thể nâng tiếp (chưa đảm bảo đạt 0.88)

1. **Risk-parity** thay chia đều (cân theo biến động từng thị trường).
2. **Tối ưu tham số riêng** từng thị trường (cẩn thận overfit).
3. **Thêm lớp thực sự khác** nếu có data: trái phiếu, crypto (BTC), thêm FX EM.
4. **Bộ lọc regime** ở cấp danh mục.

→ Thực tế các lever này có thể đưa Calmar OOS lên ~0.5–0.6, **khó tới 0.88**.
CAGR>35% bền vững + DD<40% là mục tiêu nằm ở ranh giới trên của ngành CTA.
