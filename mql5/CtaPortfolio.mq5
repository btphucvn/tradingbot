//+------------------------------------------------------------------+
//|                                               CtaPortfolio.mq5    |
//|   Danh mục CTA ĐA THỊ TRƯỜNG: breakout trend + trailing + risk%   |
//|   Một EA gắn 1 chart -> giao dịch CẢ DANH SÁCH symbol (10 TT).    |
//|   Port từ cta_portfolio.py (đạt CAGR~37%, DD~-39%, Calmar 0.95).  |
//|   Khung khuyến nghị: H4. Dùng cho LIVE/DEMO (xem ghi chú cuối).   |
//+------------------------------------------------------------------+
#property copyright "tradingbot"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//--- Tham số ---
// Sửa danh sách cho ĐÚNG ký hiệu của broker bạn (vd US500, USOIL, XAUUSD, BTCUSD...)
input string InpSymbols   = "XAUUSD,GBPJPY,USOIL,COFFEE,BTCUSD,ETHUSD,SUGAR,SOYBEAN,US500,NATGAS";
input int    InpEntryPeriod = 5;     // phá đỉnh/đáy N nến
input int    InpAtrPeriod   = 14;
input double InpSlAtr        = 3.0;  // stop ban đầu = 3*ATR
input double InpTrailAtr     = 5.0;  // trailing = 5*ATR
input double InpRiskPct      = 1.5;  // % rủi ro mỗi lệnh mỗi symbol (CALIBRATE trên demo!)
input bool   InpAllowLong    = true;
input bool   InpAllowShort   = true;
input ulong  InpMagic        = 990010;
input int    InpSlippage     = 30;

CTrade   trade;
string   gSym[];           // danh sách symbol
int      gAtr[];           // handle ATR mỗi symbol
datetime gLastBar[];       // thời gian nến cuối đã xử lý
double   gHW[], gLW[];     // đỉnh/đáy kể từ khi vào lệnh
bool     gWasIn[];

//+------------------------------------------------------------------+
int OnInit()
{
   int n = StringSplit(InpSymbols, ',', gSym);
   if(n <= 0) { Print("Danh sách symbol rỗng"); return(INIT_FAILED); }
   ArrayResize(gAtr, n); ArrayResize(gLastBar, n);
   ArrayResize(gHW, n);  ArrayResize(gLW, n); ArrayResize(gWasIn, n);
   for(int i = 0; i < n; i++)
   {
      StringTrimLeft(gSym[i]); StringTrimRight(gSym[i]);
      if(!SymbolSelect(gSym[i], true))
         PrintFormat("Cảnh báo: không chọn được symbol %s (kiểm tra tên broker)", gSym[i]);
      gAtr[i] = iATR(gSym[i], PERIOD_H4, InpAtrPeriod);
      gLastBar[i] = 0; gWasIn[i] = false; gHW[i] = 0; gLW[i] = 0;
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   for(int i = 0; i < ArraySize(gAtr); i++)
      if(gAtr[i] != INVALID_HANDLE) IndicatorRelease(gAtr[i]);
}

//+------------------------------------------------------------------+
double ATRval(int i)
{
   double b[];
   if(CopyBuffer(gAtr[i], 0, 1, 1, b) != 1) return(0.0);
   return(b[0]);
}

int DirOf(string sym)
{
   if(!PositionSelect(sym)) return(0);
   if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) return(0);
   return(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1);
}

double NormLots(string sym, double lots)
{
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double mn = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double mx = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step) * step;
   if(lots < mn) lots = mn;
   if(lots > mx) lots = mx;
   return(lots);
}

double LotsForRisk(string sym, double stop_dist)
{
   double risk_money = AccountInfoDouble(ACCOUNT_EQUITY) * (InpRiskPct / 100.0);
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(stop_dist <= 0 || tv <= 0 || ts <= 0) return(0.0);
   double money_per_price_per_lot = tv / ts;   // tự quy đổi tiền tệ
   return(NormLots(sym, risk_money / (stop_dist * money_per_price_per_lot)));
}

//+------------------------------------------------------------------+
//| Xử lý 1 symbol khi có nến H4 mới                                 |
//+------------------------------------------------------------------+
void ProcessSymbol(int i)
{
   string sym = gSym[i];
   if(Bars(sym, PERIOD_H4) < InpEntryPeriod + InpAtrPeriod + 3) return;
   double atr = ATRval(i);
   if(atr <= 0) return;
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);

   int dir = DirOf(sym);
   bool isIn = (dir != 0);
   if(isIn && !gWasIn[i]) { gHW[i] = iHigh(sym,PERIOD_H4,1); gLW[i] = iLow(sym,PERIOD_H4,1); }

   if(isIn)
   {
      double newSL;
      if(dir > 0) { gHW[i] = MathMax(gHW[i], iHigh(sym,PERIOD_H4,1)); newSL = gHW[i] - InpTrailAtr*atr; }
      else        { gLW[i] = MathMin(gLW[i], iLow(sym,PERIOD_H4,1));  newSL = gLW[i] + InpTrailAtr*atr; }
      newSL = NormalizeDouble(newSL, digits);
      double curSL = PositionGetDouble(POSITION_SL);
      if(dir > 0 && (curSL == 0 || newSL > curSL)) trade.PositionModify(sym, newSL, 0);
      if(dir < 0 && (curSL == 0 || newSL < curSL)) trade.PositionModify(sym, newSL, 0);
   }
   else
   {
      int hi = iHighest(sym, PERIOD_H4, MODE_HIGH, InpEntryPeriod, 2);
      int lo = iLowest (sym, PERIOD_H4, MODE_LOW,  InpEntryPeriod, 2);
      if(hi < 0 || lo < 0) return;
      double upper = iHigh(sym,PERIOD_H4,hi), lower = iLow(sym,PERIOD_H4,lo);
      double c1 = iClose(sym,PERIOD_H4,1);
      if(InpAllowLong && c1 > upper)
      {
         double sl = NormalizeDouble(c1 - InpSlAtr*atr, digits);
         double lots = LotsForRisk(sym, InpSlAtr*atr);
         if(lots > 0) trade.Buy(lots, sym, 0, sl, 0);
      }
      else if(InpAllowShort && c1 < lower)
      {
         double sl = NormalizeDouble(c1 + InpSlAtr*atr, digits);
         double lots = LotsForRisk(sym, InpSlAtr*atr);
         if(lots > 0) trade.Sell(lots, sym, 0, sl, 0);
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
