//+------------------------------------------------------------------+
//|                                          DonchianBreakout.mq5     |
//|   Trend-following Donchian Channel breakout (baseline)           |
//|   Port từ bản Python: vào lệnh khi giá đóng cửa bar vừa xong     |
//|   vượt kênh N bar trước đó. Không nhìn trộm tương lai.            |
//+------------------------------------------------------------------+
#property copyright "tradingbot"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//--- Tham số đầu vào (chỉnh trong Strategy Tester) ---
input int    InpEntryPeriod = 20;     // Donchian entry: số bar tính đỉnh/đáy vào lệnh
input int    InpExitPeriod  = 10;     // Donchian exit: số bar tính kênh thoát
input bool   InpAllowShort  = true;   // Cho phép bán khống
input double InpLots        = 0.10;   // Khối lượng cố định (lot)
input double InpRiskPercent = 0.0;    // >0 = size theo % equity (bỏ qua InpLots)
input ulong  InpMagic       = 990021; // Magic number nhận diện lệnh của EA
input int    InpSlippage    = 10;     // Slippage tối đa (points)

CTrade trade;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpExitPeriod >= InpEntryPeriod)
   {
      Print("Lỗi: InpExitPeriod phải nhỏ hơn InpEntryPeriod");
      return(INIT_PARAMETERS_INCORRECT);
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFillingBySymbol(_Symbol);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Chỉ xử lý 1 lần mỗi khi có BAR MỚI (giống logic close-of-bar)    |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   static datetime last_time = 0;
   datetime t = iTime(_Symbol, _Period, 0);
   if(t != last_time)
   {
      last_time = t;
      return(true);
   }
   return(false);
}

//+------------------------------------------------------------------+
//| Tính khối lượng giao dịch                                        |
//+------------------------------------------------------------------+
double CalcLots()
{
   if(InpRiskPercent <= 0.0)
      return(NormalizeLots(InpLots));

   // Size theo % equity / notional (đơn giản, không dùng stop khoảng cách).
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double price  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double contract = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(price <= 0 || contract <= 0) return(NormalizeLots(InpLots));
   double notional = equity * (InpRiskPercent / 100.0) * 100.0; // ~đòn bẩy
   double lots = notional / (price * contract);
   return(NormalizeLots(lots));
}

double NormalizeLots(double lots)
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minv = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxv = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step) * step;
   if(lots < minv) lots = minv;
   if(lots > maxv) lots = maxv;
   return(lots);
}

//+------------------------------------------------------------------+
//| Vị thế hiện tại của EA: +1 long, -1 short, 0 không có            |
//+------------------------------------------------------------------+
int CurrentDir()
{
   if(!PositionSelect(_Symbol)) return(0);
   if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) return(0);
   long type = PositionGetInteger(POSITION_TYPE);
   return(type == POSITION_TYPE_BUY ? 1 : -1);
}

void CloseIfAny()
{
   if(PositionSelect(_Symbol) && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic)
      trade.PositionClose(_Symbol);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!IsNewBar()) return;

   // Cần đủ bar lịch sử.
   if(Bars(_Symbol, _Period) < InpEntryPeriod + 2) return;

   // Bar vừa đóng = index 1. Kênh tính trên N bar TRƯỚC nó (start=2) -> no look-ahead.
   double close1 = iClose(_Symbol, _Period, 1);

   int hiE = iHighest(_Symbol, _Period, MODE_HIGH, InpEntryPeriod, 2);
   int loE = iLowest (_Symbol, _Period, MODE_LOW,  InpEntryPeriod, 2);
   int hiX = iHighest(_Symbol, _Period, MODE_HIGH, InpExitPeriod,  2);
   int loX = iLowest (_Symbol, _Period, MODE_LOW,  InpExitPeriod,  2);
   if(hiE < 0 || loE < 0 || hiX < 0 || loX < 0) return;

   double upperEntry = iHigh(_Symbol, _Period, hiE);
   double lowerEntry = iLow (_Symbol, _Period, loE);
   double upperExit  = iHigh(_Symbol, _Period, hiX);
   double lowerExit  = iLow (_Symbol, _Period, loX);

   int dir = CurrentDir();

   if(dir == 0)
   {
      if(close1 > upperEntry)
         trade.Buy(CalcLots(), _Symbol);
      else if(InpAllowShort && close1 < lowerEntry)
         trade.Sell(CalcLots(), _Symbol);
   }
   else if(dir > 0)            // đang long
   {
      if(close1 < lowerExit)   // thoát long
      {
         CloseIfAny();
         if(InpAllowShort && close1 < lowerEntry)
            trade.Sell(CalcLots(), _Symbol);
      }
   }
   else                       // đang short
   {
      if(close1 > upperExit)   // thoát short
      {
         CloseIfAny();
         if(close1 > upperEntry)
            trade.Buy(CalcLots(), _Symbol);
      }
   }
}
//+------------------------------------------------------------------+
