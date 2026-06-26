# Kiến trúc hệ thống đạt x5 — GBP/JPY Breakout Trend-Following

> Tài liệu lưu lại **toàn bộ kiến trúc và cấu hình** đã đạt mục tiêu:
> **x5 lợi nhuận + ≥200 lệnh** trên GBP/JPY (H4, 2010–2024), edge xác nhận
> out-of-sample. Dùng để tái tạo và phát triển tiếp.

---

## 1. Kết quả đạt được

| Risk | x | CAGR | Winrate | PF | Max DD | Lệnh |
|------|-----|------|---------|-----|--------|------|
| **2% (khuyến nghị)** | **6.4x** | 14.1% | 39% | 1.27 | −42% | 675 |
| 3% (mạo hiểm) | 12.9x | 20% | 39% | 1.22 | −56% | 675 |

**Phân tách In-Sample / Out-of-Sample (risk 3%):**

| Giai đoạn | x | CAGR | PF | Sharpe | Max DD | Lệnh |
|-----------|-----|------|-----|--------|--------|------|
| IS 2010–2019 | 8.0x | 24.8% | 1.35 | 0.91 | −51% | 498 |
| **OOS 2019–2024** | 1.6x | **+10.8%** | **1.15** | 0.60 | −56% | 177 |

→ OOS **dương** và equity tăng lan tỏa toàn kỳ ⟹ edge thật, không phải overfit thuần.

**Lệnh tái tạo:**
```bash
.venv/bin/python run_breakout.py --symbol GBPJPY --entry 5 --sl-atr 3 --trail-atr 5 \
  --no-trend --risks 0.02,0.03
```

### 1.1. Bảng risk → CAGR → drawdown (CÙNG một chiến thuật, chỉ đổi % rủi ro)

CAGR chỉ là hàm của **mức risk** — KHÔNG phải edge tốt hơn. Đổi % rủi ro để chọn
điểm trên đường cong này:

| Risk/lệnh | x lần | **CAGR** | Max DD | PF | Đánh giá |
|-----------|-------|----------|--------|-----|----------|
| 2% | 6.4x | 14% | −42% | 1.27 | Hợp lý, chịu được |
| 3% | 12.9x | 20% | −56% | 1.22 | Đau |
| 4% | 22.8x | 25% | −67% | 1.17 | Sát giới hạn |
| 5% | 35.6x | 29% | −75% | 1.14 | Rất liều |
| 6% | 49.2x | 32% | −82% | 1.11 | Nguy hiểm |
| 7% | 60.4x | 34% | −87% | 1.09 | Gần cháy |
| **8%** | **66.7x** | **35%** | **−90%** | 1.07 | **Cờ bạc (sẽ cháy thật)** |

⚠️ **Lệnh cho CAGR > 35%:**
```bash
.venv/bin/python run_breakout.py --symbol GBPJPY --entry 5 --sl-atr 3 --trail-atr 5 \
  --no-trend --risks 0.08
```
**CAGR 35% = drawdown −90%** (tài khoản $10k có lúc còn ~$1k). Để mức risk 8% là
**over-betting** quá điểm Kelly: chú ý **PF GIẢM** 1.27→1.07 khi tăng risk — bạn
nhận thêm RỦI RO, không phải lợi nhuận thật. Thực tế sẽ bị margin call. **Không
khuyến nghị.** CAGR cao bền vững chỉ đến từ edge mạnh hơn, không phải đòn bẩy.

### 1.2. Đã thử nâng edge (PF) — kết quả trung thực

Để tăng CAGR mà DD không nổ, cần nâng PF > 1.27. Đã thử thật, **đều KHÔNG hiệu quả**
trên GBP/JPY (edge đã chạm trần):

| Cách thử | Kết quả |
|----------|---------|
| Lọc phiên London/NY (6–22h) | PF 1.22 → 1.19 (giảm) |
| Lọc ATR đang tăng | PF → 1.19–1.20 (giảm) |
| Yêu cầu break mạnh (buffer ATR) | PF → 1.07–1.17 (giảm) |
| Ensemble entry 5/10/20 | Calmar 0.39 → 0.28 (giảm; các hệ tương quan cao) |

→ Mọi bộ lọc cắt bớt cả lệnh thắng lớn (đuôi béo), giảm edge. Ensemble vô ích vì
cùng 1 cặp = cùng nguồn rủi ro. **Trần edge GBP/JPY ≈ PF 1.27** với chiến thuật
price-action/breakout thuần. Muốn vượt phải có nguồn tín hiệu khác hẳn (order-flow,
lãi suất, ML có kiểm định) — chưa làm.

---

## 2. Ý tưởng cốt lõi (vì sao nó hoạt động)

GBP/JPY có **xu hướng dài và mạnh** do *carry trade* (chênh lãi suất GBP > JPY)
và các đợt JPY yếu kéo dài (2012–2015, 2020–2022). Hệ thống là một
**trend-follower luôn-trong-thị-trường**:

- Vào lệnh **sớm** khi giá phá kênh ngắn (5 nến H4 ≈ 20 giờ) → bắt được nhiều sóng.
- **Trailing stop rộng (5×ATR)** → để lệnh thắng CHẠY theo sóng dài (đuôi béo).
- Cắt lỗ nhanh (3×ATR) → thua nhỏ.
- Kết quả: **thua ~6/10 lệnh** (winrate 39%) nhưng vài lệnh thắng RẤT lớn bù lại
  → PF 1.27. Đây là bản chất trend-following: winrate thấp, payoff lớn.

> ⚠️ Đây KHÔNG phải "winrate cao". Đã chứng minh: winrate cao ⟂ x5 (xem mục 7).
> x5 chỉ đạt được bằng cách chấp nhận winrate thấp + drawdown lớn.

---

## 3. Chiến thuật giao dịch chi tiết (playbook)

Luật đầy đủ — có thể đọc và thực thi bằng tay. Tất cả trên khung **H4 GBP/JPY**,
dùng **ATR(14)** làm đơn vị đo biến động.

### 3.1. Điều kiện VÀO lệnh (Entry)
- **LONG:** khi giá **ĐÓNG CỬA** một nến H4 **> đỉnh cao nhất của 5 nến H4 liền
  trước** (phá đỉnh Donchian-5) → đặt lệnh **MUA ở giá MỞ CỬA nến kế tiếp**.
- **SHORT:** khi giá đóng cửa **< đáy thấp nhất của 5 nến liền trước** → **BÁN ở
  mở cửa nến kế tiếp**.
- **Không lọc xu hướng** — giao dịch cả 2 chiều (long và short).
- **Chỉ 1 vị thế tại một thời điểm** — đang có lệnh thì bỏ qua tín hiệu mới.
- (Khớp ở mở cửa nến sau, không phải nến tín hiệu → tránh nhìn trộm tương lai.)

### 3.2. Cắt lỗ ban đầu (Initial Stop-Loss)
- **LONG:** stop = giá_vào − **3 × ATR**.
- **SHORT:** stop = giá_vào + **3 × ATR**.
- Đây là mức thua tối đa nếu sai ngay → cố định rủi ro mỗi lệnh.

### 3.3. Trailing Stop — cách "giữ đuôi béo" (mấu chốt của lợi nhuận)
Mỗi nến, sau khi kiểm stop:
- **LONG:** cập nhật `đỉnh_cao_nhất` đã đạt từ khi vào lệnh; rồi
  `stop_mới = max(stop_cũ, đỉnh_cao_nhất − 5 × ATR)`. **Stop chỉ dời LÊN, không lùi.**
- **SHORT:** cập nhật `đáy_thấp_nhất`; rồi
  `stop_mới = min(stop_cũ, đáy_thấp_nhất + 5 × ATR)`. **Stop chỉ dời XUỐNG.**
- Trailing rộng (5×ATR) cho giá "thở" → lệnh thắng chạy theo cả sóng dài.

### 3.4. THOÁT lệnh (Exit)
- **KHÔNG có chốt lời cố định.** (Trong code target đặt 100×ATR = vô hiệu hóa TP.)
- Thoát **100% vị thế khi giá chạm trailing stop** — đây là cách RA lệnh duy nhất.
- Hệ quả: winners chạy tới khi xu hướng đảo đủ 5×ATR mới bị cắt → vài lệnh thắng
  rất lớn; losers bị cắt nhanh ở 3×ATR.

### 3.5. Khối lượng vào lệnh (Position Sizing) — rủi ro cố định 2%
```
rủi_ro_tiền   = vốn_hiện_tại × 2%
khoảng_cách_stop = 3 × ATR              (đơn vị giá, JPY)
quote_to_usd  = 1 / USDJPY              (quy đổi JPY → USD)
units (GBP)   = rủi_ro_tiền / (khoảng_cách_stop × quote_to_usd)
```
- Vốn **compound**: thắng → vốn tăng → lệnh sau lớn hơn (và ngược lại).
- Mỗi lệnh dính stop ban đầu mất đúng **2% vốn**.

### 3.6. Ví dụ một lệnh đầy đủ (số minh họa)
- Vốn $10,000; ATR(14) = 0.80 JPY (80 pip); USDJPY = 150.
- Giá phá đỉnh 5 nến, vào **LONG ở 185.00**.
- Stop ban đầu = 185.00 − 3×0.80 = **182.60** (cách 2.40 = 240 pip).
- Rủi ro = 2% × $10,000 = **$200**; quote_to_usd = 1/150 = 0.006667.
- units = 200 / (2.40 × 0.006667) = **12,500 GBP** (~0.125 lot).
- Giá chạy lên 190 → đỉnh=190 → stop dời lên 190 − 5×0.80 = **186.00** (khóa lãi).
- Giá lên 195 → stop = **191.00**; … cứ thế tới khi đảo chiều chạm stop thì thoát.
- Nếu sai ngay từ đầu (giá rơi về 182.60) → thua $200 (−2%). Xong, tìm lệnh mới.

### 3.7. Tóm tắt luật (pseudo-code)
```
Mỗi nến H4 đóng cửa:
  nếu KHÔNG có vị thế:
      nếu close > max(high[5 nến trước]):  vào LONG  ở open nến sau
      nếu close < min(low[5 nến trước]):   vào SHORT ở open nến sau
      stop = entry ∓ 3*ATR;  size theo mục 3.5
  nếu ĐANG có vị thế:
      nếu giá chạm stop (trong nến):       thoát 100%
      ngược lại:                           dời trailing stop (mục 3.3)
```

### 3.8. Tâm lý & kỷ luật (sống còn)
- **Winrate chỉ 39%** → bạn THUA ~6/10 lệnh. Đây là bình thường, không phải hệ
  thống hỏng. Lãi đến từ vài lệnh thắng lớn — **không được bỏ lỡ chúng** bằng cách
  tự ý chốt sớm hay nhảy lệnh.
- **Phải giữ đúng luật mọi lệnh.** Bỏ vài lệnh thua = có thể bỏ luôn lệnh thắng to
  kế tiếp → phá vỡ kỳ vọng.
- Phải chịu được **drawdown −42%** (mất gần nửa tài khoản) mà không bỏ cuộc.

---

## 4. Kiến trúc tổng thể

```
Dukascopy (H4 GBPJPY + USDJPY) ──► loader ──► DataFrame OHLC + spread thật
                                                  │
                          D1 GBPJPY ──► trend bias (không dùng ở config x5)
                                                  │
                                                  ▼
                              BreakoutTrend.generate_setups()
                              → list[TradeSetup] (entry, stop, target, trail_atr)
                                                  │
                                                  ▼
        quote_to_usd (=1/USDJPY) ──► TradeBroker.run(df, setups, q, atr)
                                       • sizing theo % rủi ro
                                       • trailing stop theo ATR
                                       • khớp SL/TP trong nến (no look-ahead)
                                       • trừ spread/slippage/swap, quy đổi JPY→USD
                                                  │
                                                  ▼
                              BacktestResult ──► metrics.compute()
                              (x, CAGR, winrate, PF, maxDD, Sharpe...)
```

### File liên quan
| File | Vai trò |
|------|---------|
| `src/data/loader.py` | Tải OHLC + spread thật từ Dukascopy, cache CSV |
| `src/strategies/breakout.py` | Chiến lược breakout cưỡi-trend (`BreakoutTrend`) |
| `src/strategies/indicators.py` | ATR (đo biến động cho stop/trail) |
| `src/backtest/broker.py` | Engine cấp-lệnh: trailing, risk-sizing, quy đổi tiền tệ |
| `src/backtest/metrics.py` | Chỉ số hiệu suất |
| `run_breakout.py` | Runner + risk sweep + IS/OOS + biểu đồ |
| `sweep_x5.py` | Quét tìm cấu hình tối đa x (cách tìm ra config này) |

---

## 5. Tham số chính xác

### Chiến lược — `BreakoutParams` (src/strategies/breakout.py)
| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `entry_period` | **5** | Phá đỉnh/đáy 5 nến H4 → vào lệnh (ngắn = nhiều sóng) |
| `atr_period` | 14 | Chu kỳ ATR |
| `sl_atr` | **3.0** | Stop ban đầu = entry ∓ 3×ATR |
| `trail_atr` | **5.0** | Trailing = đỉnh/đáy ∓ 5×ATR (giữ đuôi béo) |
| `use_trend` | **False** | KHÔNG lọc trend D1 (giao dịch cả 2 chiều) |
| `tp1_atr` | 0 | Không chốt một phần (chốt sớm sẽ giết đuôi béo) |

### Quản lý vốn — `TradeBroker` (src/backtest/broker.py)
| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `risk_pct` | **0.02** (khuyến nghị) | Mỗi lệnh rủi ro 2% vốn hiện tại (compound) |
| `max_leverage` | 30 | Trần đòn bẩy |
| `costs` | spread thật + slippage 0.2 pip + swap | Chi phí giao dịch |

### Dữ liệu
- Cặp: **GBPJPY**, khung **H4**, 2010-01-01 → 2024-01-01, nguồn **Dukascopy**.
- Cần thêm **USDJPY H4** để quy đổi P&L JPY → USD.

---

## 6. Cơ chế engine bảo đảm trung thực (chống tự lừa dối)

1. **No look-ahead:** tín hiệu tính ở nến đóng cửa `t`, khớp ở **giá mở cửa nến
   t+1**. Kênh Donchian dùng `.shift(1)`. Trailing cập nhật bằng đỉnh/đáy nến `t`
   chỉ để siết stop cho nến SAU.
2. **Khớp SL/TP trong nến:** dùng high/low từng nến; nếu cùng nến chạm cả SL lẫn
   TP thì giả định **SL trước** (xấu nhất). Xử lý cả gap (khớp ở open).
3. **Quy đổi tiền tệ:** GBPJPY quote = JPY. Engine nhận mảng `quote_to_usd = 1/USDJPY`
   để mọi P&L, sizing, phí, swap quy về **USD chính xác**.
4. **Sizing theo rủi ro thật:** `units = (equity × risk%) / (khoảng_cách_stop × quote_to_usd)`
   → mỗi lệnh thua đúng `risk%` vốn, bất kể cặp.
5. **Chi phí thật:** trừ nửa spread (từ data) + slippage mỗi lần khớp, swap qua đêm.
6. **Kiểm Out-of-Sample:** luôn tách IS/OOS; OOS là thước đo thật.

---

## 7. Cách đã tìm ra cấu hình này

`sweep_x5.py` quét lưới `entry ∈ {5,10,20,40} × sl ∈ {1.5,2,3} × trail ∈ {3,5,8}
× trend ∈ {T,F} × risk ∈ {2,3,5}%`, tối đa hóa **x** với điều kiện ≥200 lệnh.
Phát hiện: **entry càng ngắn (5) + không lọc trend + trailing rộng** cho x cao nhất
vì bắt nhiều sóng + giữ đuôi béo. Sau đó verify IS/OOS bằng `run_breakout.py`.

---

## 8. Bài học định lượng (ràng buộc cơ bản)

Quá trình nghiên cứu (~140+ cấu hình) cho thấy quy luật **không thể phá**:

| Muốn | Phải | Hệ quả |
|------|------|--------|
| Winrate cao (>60%) | TP gần (mean-reversion) | Thắng nhỏ → **không thể x5** |
| x5 | Cưỡi sóng lớn (trend + trailing) | **Winrate buộc thấp (~39%)** |

→ **Winrate và lợi nhuận lớn đánh đổi nhau** (thị trường gần hiệu quả, edge mỏng).
Chốt lời sớm để tăng winrate sẽ giết "đuôi béo" → PF rơi từ 1.27 xuống 0.72.
**x5 chỉ đạt được khi CHẤP NHẬN winrate thấp + drawdown lớn.**

---

## 9. Hạn chế & rủi ro (đọc trước khi dùng tiền thật)

- **Drawdown −42% (risk 2%) tới −56% (risk 3%):** phải chịu được mất ~nửa tài khoản.
- **Phụ thuộc regime:** edge đến từ JPY yếu + trend bền. BoJ đổi chính sách / JPY
  hết trend → edge giảm. Quá khứ ≠ tương lai.
- **OOS yếu hơn IS** (PF 1.35→1.15): kỳ vọng forward ~10%/năm (≈ x4 sau 14 năm).
  Con số 6.4x của backtest có phần "thổi" bởi giai đoạn 2010–2019.
- **Selection bias:** entry=5 chọn bằng cách quét cả giai đoạn → OOS hơi lạc quan.
- **Chi phí thật:** 675 lệnh, 96% thời gian có vị thế. Spread/slippage GBPJPY thật
  ở broker có thể bào mòn PF → BẮT BUỘC verify trên demo.

---

## 10. Bước tiếp theo

1. **Port sang EA MQL5** (giống `mql5/DonchianBreakout.mq5`) để chạy MT5 Strategy
   Tester với tick data + spread broker thật.
2. **Chạy demo ≥6 tháng** xác nhận spread/slippage thật không giết edge.
3. **Walk-forward** nhiều cửa sổ để kiểm độ bền tham số.
4. Cân nhắc **giảm risk xuống 1–1.5%** nếu không chịu nổi DD −42% (đổi lại x thấp hơn).
