//+------------------------------------------------------------------+
//|                                               CtaPortfolio.mq4    |
//|   Danh mục CTA ĐA THỊ TRƯỜNG: breakout trend + trailing + risk%   |
//|   Một EA gắn 1 chart -> giao dịch CẢ DANH SÁCH symbol (6 TT).     |
//|   Port từ cta_portfolio.py / CtaPortfolio.mq5                     |
//|   Backtest: 2018-2026 lev4.5x CAGR~36%, DD~-39%; gần đây ~23%/năm.|
//|   Khung khuyến nghị: H4. Dùng cho LIVE/DEMO (xem ghi chú cuối).   |
//+------------------------------------------------------------------+
#property copyright "tradingbot"
#property version   "1.00"
#property strict

//--- Tham số ---
// Mặc định theo TÊN DUKASCOPY MT (hàng hóa đuôi .CMD, WTI = LIGHT).
// Broker khác -> sửa cho khớp Market Watch (verify tên crypto: BTC/USD hay BTCUSD).
extern string InpSymbols     = "XAUUSD,GBPJPY,LIGHT.CMD,COFFEE.CMD,BTCUSD,ETHUSD";
extern int    InpEntryPeriod = 5;     // phá đỉnh/đáy N nến
extern int    InpAtrPeriod   = 14;
extern double InpSlAtr       = 3.0;   // stop ban đầu = 3*ATR
extern double InpTrailAtr    = 5.0;   // trailing = 5*ATR
extern double InpRiskPct     = 1.0;   // % rủi ro mỗi lệnh mỗi symbol (CALIBRATE trên demo!)
extern bool   InpAllowLong   = true;
extern bool   InpAllowShort  = true;
extern int    InpMagic       = 990010;
extern int    InpSlippage    = 30;    // điểm (points)

string   gSym[];           // danh sách symbol
datetime gLastBar[];       // thời gian nến cuối đã xử lý cho mỗi symbol
double   gHW[], gLW[];     // đỉnh/đáy kể từ khi vào lệnh
bool     gWasIn[];

//+------------------------------------------------------------------+
int OnInit()
{
   int n = StringSplit(InpSymbols, ',', gSym);
   if(n <= 0) { Print("Danh sách symbol rỗng"); return(INIT_FAILED); }
   ArrayResize(gLastBar, n);
   ArrayResize(gHW, n);  ArrayResize(gLW, n); ArrayResize(gWasIn, n);
   for(int i = 0; i < n; i++)
   {
      gSym[i] = TrimStr(gSym[i]);
      // "khởi động" symbol để broker nạp lịch sử (MarketWatch)
      double tmp = MarketInfo(gSym[i], MODE_BID);
      if(tmp <= 0)
         PrintFormat("Cảnh báo: không lấy được giá %s (kiểm tra tên broker / MarketWatch)", gSym[i]);
      gLastBar[i] = 0; gWasIn[i] = false; gHW[i] = 0; gLW[i] = 0;
   }
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {}

//+------------------------------------------------------------------+
//| Tiện ích                                                         |
//+------------------------------------------------------------------+
string TrimStr(string s)
{
   StringTrimLeft(s); StringTrimRight(s);
   return(s);
}

double ATRval(string sym)
{
   // ATR của nến đã đóng gần nhất (shift 1)
   return(iATR(sym, PERIOD_H4, InpAtrPeriod, 1));
}

// Tìm ticket lệnh của symbol do EA này quản lý (-1 nếu không có)
int FindOrder(string sym)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol() == sym && OrderMagicNumber() == InpMagic &&
         (OrderType() == OP_BUY || OrderType() == OP_SELL))
         return(OrderTicket());
   }
   return(-1);
}

// Chiều của lệnh đang chọn: +1 buy, -1 sell, 0 không có
int DirOfTicket(int ticket)
{
   if(ticket < 0) return(0);
   if(!OrderSelect(ticket, SELECT_BY_TICKET)) return(0);
   return(OrderType() == OP_BUY ? 1 : -1);
}

double NormLots(string sym, double lots)
{
   double step = MarketInfo(sym, MODE_LOTSTEP);
   double mn   = MarketInfo(sym, MODE_MINLOT);
   double mx   = MarketInfo(sym, MODE_MAXLOT);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step) * step;
   if(lots < mn) lots = mn;
   if(lots > mx) lots = mx;
   return(lots);
}

double LotsForRisk(string sym, double stop_dist)
{
   double risk_money = AccountEquity() * (InpRiskPct / 100.0);
   double tv = MarketInfo(sym, MODE_TICKVALUE);   // giá trị 1 tick / 1 lot (tiền tài khoản)
   double ts = MarketInfo(sym, MODE_TICKSIZE);
   if(stop_dist <= 0 || tv <= 0 || ts <= 0) return(0.0);
   double money_per_price_per_lot = tv / ts;       // tự quy đổi tiền tệ
   return(NormLots(sym, risk_money / (stop_dist * money_per_price_per_lot)));
}

//+------------------------------------------------------------------+
//| Xử lý 1 symbol khi có nến H4 mới                                 |
//+------------------------------------------------------------------+
void ProcessSymbol(int i)
{
   string sym = gSym[i];
   if(iBars(sym, PERIOD_H4) < InpEntryPeriod + InpAtrPeriod + 3) return;
   double atr = ATRval(sym);
   if(atr <= 0) return;
   int digits = (int)MarketInfo(sym, MODE_DIGITS);

   int ticket = FindOrder(sym);
   int dir    = DirOfTicket(ticket);
   bool isIn  = (dir != 0);

   // Vừa mới vào lệnh -> khởi tạo đỉnh/đáy theo dõi trailing
   if(isIn && !gWasIn[i])
   {
      gHW[i] = iHigh(sym, PERIOD_H4, 1);
      gLW[i] = iLow(sym, PERIOD_H4, 1);
   }

   if(isIn)
   {
      // --- Trailing stop theo đỉnh/đáy đã đạt ---
      if(!OrderSelect(ticket, SELECT_BY_TICKET)) { gWasIn[i] = isIn; return; }
      double openP = OrderOpenPrice();
      double curSL = OrderStopLoss();
      double newSL;
      if(dir > 0)
      {
         gHW[i] = MathMax(gHW[i], iHigh(sym, PERIOD_H4, 1));
         newSL  = NormalizeDouble(gHW[i] - InpTrailAtr * atr, digits);
         if(curSL == 0 || newSL > curSL)
            OrderModify(ticket, openP, newSL, OrderTakeProfit(), 0, clrNONE);
      }
      else
      {
         gLW[i] = MathMin(gLW[i], iLow(sym, PERIOD_H4, 1));
         newSL  = NormalizeDouble(gLW[i] + InpTrailAtr * atr, digits);
         if(curSL == 0 || newSL < curSL)
            OrderModify(ticket, openP, newSL, OrderTakeProfit(), 0, clrNONE);
      }
   }
   else
   {
      // --- Tín hiệu breakout N nến (xét trên các nến đã đóng, từ shift 2) ---
      int hi = iHighest(sym, PERIOD_H4, MODE_HIGH, InpEntryPeriod, 2);
      int lo = iLowest (sym, PERIOD_H4, MODE_LOW,  InpEntryPeriod, 2);
      if(hi < 0 || lo < 0) return;
      double upper = iHigh(sym, PERIOD_H4, hi);
      double lower = iLow (sym, PERIOD_H4, lo);
      double c1    = iClose(sym, PERIOD_H4, 1);

      if(InpAllowLong && c1 > upper)
      {
         double ask  = MarketInfo(sym, MODE_ASK);
         double sl   = NormalizeDouble(c1 - InpSlAtr * atr, digits);
         double lots = LotsForRisk(sym, InpSlAtr * atr);
         if(lots > 0 && ask > 0)
            OrderSend(sym, OP_BUY, lots, ask, InpSlippage, sl, 0,
                      "CTA", InpMagic, 0, clrDodgerBlue);
      }
      else if(InpAllowShort && c1 < lower)
      {
         double bid  = MarketInfo(sym, MODE_BID);
         double sl   = NormalizeDouble(c1 + InpSlAtr * atr, digits);
         double lots = LotsForRisk(sym, InpSlAtr * atr);
         if(lots > 0 && bid > 0)
            OrderSend(sym, OP_SELL, lots, bid, InpSlippage, sl, 0,
                      "CTA", InpMagic, 0, clrTomato);
      }
   }

   gWasIn[i] = isIn;
}

//+------------------------------------------------------------------+
void OnTick()
{
   for(int i = 0; i < ArraySize(gSym); i++)
   {
      datetime t = iTime(gSym[i], PERIOD_H4, 0);   // nến H4 hiện tại của symbol i
      if(t == 0) continue;                          // chưa có data
      if(t != gLastBar[i]) { gLastBar[i] = t; ProcessSymbol(i); }
   }
}
//+------------------------------------------------------------------+
//| GHI CHÚ TRIỂN KHAI                                              |
//| 1. Gắn EA vào 1 chart bất kỳ khung H4; bật AutoTrading.         |
//| 2. Mọi symbol trong InpSymbols phải hiện trong Market Watch và  |
//|    có lịch sử H4 (mở chart H4 từng cái 1 lần để broker nạp data).|
//| 3. Tên symbol PHẢI khớp broker. Dukascopy: WTI=LIGHT.CMD,        |
//|    cà phê=COFFEE.CMD; verify crypto BTC/USD hay BTCUSD.          |
//| 4. InpRiskPct mặc định 1%/lệnh/symbol -> với 6 symbol rủi ro     |
//|    tổng cộng dồn. BẮT ĐẦU 0.5-1%, HIỆU CHỈNH trên demo.          |
//| 5. Đòn bẩy hiệu dụng do risk% + số symbol active quyết định;     |
//|    backtest Python dùng lev ~4.5x (risk-parity). Bản EA này phân |
//|    bổ risk% bằng nhau (xấp xỉ equal-weight), không inverse-vol.  |
//| 6. CẢNH BÁO: crypto chiếm 1/3 rổ -> phụ thuộc nặng crypto.       |
//|    Kỳ vọng forward thực tế ~20-25%/năm, KHÔNG phải 36%.          |
//+------------------------------------------------------------------+
