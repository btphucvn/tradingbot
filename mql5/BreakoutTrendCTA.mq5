//+------------------------------------------------------------------+
//|                                          BreakoutTrendCTA.mq5     |
//|   Breakout trend-following + trailing stop + sizing theo % rủi ro |
//|   Port từ Python (src/strategies/breakout.py + broker).          |
//|   Dùng cho GBP/JPY, XAU/USD, WTI, Coffee... (gắn mỗi chart 1 EA). |
//|   Khung khuyến nghị: H4.                                          |
//+------------------------------------------------------------------+
#property copyright "tradingbot"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//--- Tham số (mặc định = cấu hình đã verify) ---
input int    InpEntryPeriod = 5;      // Donchian: phá đỉnh/đáy N nến -> vào lệnh
input int    InpAtrPeriod   = 14;     // chu kỳ ATR
input double InpSlAtr        = 3.0;   // stop ban đầu = entry -/+ SlAtr*ATR
input double InpTrailAtr     = 5.0;   // trailing = đỉnh/đáy - TrailAtr*ATR
input double InpRiskPct      = 2.0;   // % rủi ro mỗi lệnh (2.0 = 2%)
input bool   InpAllowLong    = true;
input bool   InpAllowShort   = true;
input ulong  InpMagic        = 770055;
input int    InpSlippage     = 20;    // points

CTrade   trade;
int      atrHandle = INVALID_HANDLE;

//+------------------------------------------------------------------+
int OnInit()
{
   atrHandle = iATR(_Symbol, _Period, InpAtrPeriod);
   if(atrHandle == INVALID_HANDLE)
   {
      Print("Lỗi tạo ATR handle");
      return(INIT_FAILED);
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFillingBySymbol(_Symbol);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { IndicatorRelease(atrHandle); }

//+------------------------------------------------------------------+
//| Chỉ xử lý 1 lần mỗi nến mới (logic close-of-bar)                 |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   static datetime last = 0;
   datetime t = iTime(_Symbol, _Period, 0);
   if(t != last) { last = t; return(true); }
   return(false);
}

double ATRval()
{
   double buf[];
   if(CopyBuffer(atrHandle, 0, 1, 1, buf) != 1) return(0.0);  // ATR của nến vừa đóng
   return(buf[0]);
}

//+------------------------------------------------------------------+
//| Khối lượng theo % rủi ro: lots = risk_money / (stop_dist * $/giá/lot) |
//+------------------------------------------------------------------+
double LotsForRisk(double stop_dist)
{
   double equity   = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money = equity * (InpRiskPct / 100.0);
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE); // theo tiền tài khoản
   double tick_sz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(stop_dist <= 0 || tick_val <= 0 || tick_sz <= 0) return(0.0);
   double money_per_price_per_lot = tick_val / tick_sz;   // tự quy đổi tiền tệ
   double lots = risk_money / (stop_dist * money_per_price_per_lot);
   return(NormalizeLots(lots));
}

double NormalizeLots(double lots)
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step) * step;
   if(lots < mn) lots = mn;
   if(lots > mx) lots = mx;
   return(lots);
}

int CurrentDir()  // +1 long, -1 short, 0 flat (của EA này)
{
   if(!PositionSelect(_Symbol)) return(0);
   if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) return(0);
   return(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!IsNewBar()) return;
   if(Bars(_Symbol, _Period) < InpEntryPeriod + InpAtrPeriod + 3) return;

   double atr = ATRval();
   if(atr <= 0) return;

   int dir = CurrentDir();

   // theo dõi đỉnh/đáy kể từ khi vào lệnh (cho trailing)
   static bool   wasIn = false;
   static double hw = 0, lw = 0;
   bool isIn = (dir != 0);
   if(isIn && !wasIn) { hw = iHigh(_Symbol,_Period,1); lw = iLow(_Symbol,_Period,1); }

   if(isIn)
   {
      // --- Trailing stop: chỉ siết, không nới ---
      double newSL = 0;
      if(dir > 0)
      {
         hw = MathMax(hw, iHigh(_Symbol,_Period,1));
         newSL = hw - InpTrailAtr * atr;
      }
      else
      {
         lw = MathMin(lw, iLow(_Symbol,_Period,1));
         newSL = lw + InpTrailAtr * atr;
      }
      double curSL = PositionGetDouble(POSITION_SL);
      newSL = NormalizeDouble(newSL, _Digits);
      if(dir > 0 && (curSL == 0 || newSL > curSL))
         trade.PositionModify(_Symbol, newSL, 0);
      if(dir < 0 && (curSL == 0 || newSL < curSL))
         trade.PositionModify(_Symbol, newSL, 0);
   }
   else
   {
      // --- Vào lệnh khi phá kênh Donchian N nến (loại nến hiện tại) ---
      int hi = iHighest(_Symbol, _Period, MODE_HIGH, InpEntryPeriod, 2);
      int lo = iLowest (_Symbol, _Period, MODE_LOW,  InpEntryPeriod, 2);
      if(hi < 0 || lo < 0) return;
      double upper = iHigh(_Symbol, _Period, hi);
      double lower = iLow (_Symbol, _Period, lo);
      double close1 = iClose(_Symbol, _Period, 1);

      if(InpAllowLong && close1 > upper)
      {
         double sl = NormalizeDouble(close1 - InpSlAtr * atr, _Digits);
         double lots = LotsForRisk(InpSlAtr * atr);
         if(lots > 0) trade.Buy(lots, _Symbol, 0, sl, 0);
      }
      else if(InpAllowShort && close1 < lower)
      {
         double sl = NormalizeDouble(close1 + InpSlAtr * atr, _Digits);
         double lots = LotsForRisk(InpSlAtr * atr);
         if(lots > 0) trade.Sell(lots, _Symbol, 0, sl, 0);
      }
   }

   wasIn = isIn;
}
//+------------------------------------------------------------------+
