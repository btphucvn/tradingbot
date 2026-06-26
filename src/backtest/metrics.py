"""Các chỉ số đánh giá hiệu suất backtest.

Tất cả tính trên đường vốn (equity) đã trừ chi phí. Sharpe được annualize
dựa trên khoảng cách thời gian THẬT giữa các bar (suy ra từ index).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import BacktestResult

SECONDS_PER_YEAR = 365.25 * 24 * 3600


def _periods_per_year(index: pd.DatetimeIndex) -> float:
    """Số bar/năm, suy ra từ khoảng cách trung vị giữa các bar."""
    if len(index) < 3:
        return 252.0
    # Dùng total_seconds() để không phụ thuộc resolution (ns/us/ms) của index.
    deltas = index.to_series().diff().dropna().dt.total_seconds().to_numpy()
    median_sec = float(np.median(deltas))
    if median_sec <= 0:
        return 252.0
    return SECONDS_PER_YEAR / median_sec


def compute(result: BacktestResult) -> dict:
    eq = result.equity
    ret = result.returns
    idx = eq.index

    total_return = eq.iloc[-1] / result.initial_equity - 1.0

    # CAGR theo thời gian thực.
    years = (idx[-1] - idx[0]).total_seconds() / SECONDS_PER_YEAR
    cagr = (eq.iloc[-1] / result.initial_equity) ** (1 / years) - 1.0 if years > 0 else np.nan

    # Sharpe (rf = 0) annualized.
    ppy = _periods_per_year(idx)
    std = ret.std()
    sharpe = (ret.mean() / std) * np.sqrt(ppy) if std > 0 else 0.0

    # Sortino (chỉ phạt downside).
    downside = ret[ret < 0].std()
    sortino = (ret.mean() / downside) * np.sqrt(ppy) if downside > 0 else 0.0

    # Max drawdown.
    running_max = eq.cummax()
    drawdown = eq / running_max - 1.0
    max_dd = drawdown.min()

    # Calmar = CAGR / |maxDD|.
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan

    # Thống kê theo lệnh: P&L mỗi vòng đời vị thế (giữa các lần đổi hướng).
    trade_pnls = _trade_pnls(result)
    n_trades = len(trade_pnls)
    wins = trade_pnls[trade_pnls > 0]
    losses = trade_pnls[trade_pnls < 0]
    win_rate = len(wins) / n_trades if n_trades else 0.0
    gross_win = wins.sum()
    gross_loss = -losses.sum()
    profit_factor = gross_win / gross_loss if gross_loss > 0 else np.inf
    avg_trade = trade_pnls.mean() if n_trades else 0.0

    # Tỉ lệ thời gian có vị thế (exposure).
    exposure = float((result.position != 0).mean())

    return {
        "final_equity": float(eq.iloc[-1]),
        "total_return": float(total_return),
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": float(max_dd),
        "calmar": float(calmar),
        "n_trades": int(n_trades),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "avg_trade": float(avg_trade),
        "exposure": exposure,
        "years": float(years),
        "total_cost": float(result.trades["cost"].sum()) if not result.trades.empty else 0.0,
    }


def _trade_pnls(result: BacktestResult) -> pd.Series:
    """P&L thực của từng "vòng đời vị thế".

    Mỗi lần engine đổi hướng = đóng vị thế cũ. Lấy chênh lệch equity giữa
    các thời điểm đổi vị thế làm P&L mỗi lệnh (đã gồm chi phí).
    """
    if result.trades.empty:
        return pd.Series(dtype=float)
    # Engine cấp-lệnh (broker) ghi sẵn P&L thực mỗi lệnh -> dùng trực tiếp.
    if "pnl" in result.trades.columns:
        return result.trades["pnl"].reset_index(drop=True)
    # Engine signal-based: suy P&L từ chênh lệch equity giữa các lần đổi hướng.
    change_times = result.trades["time"].tolist()
    eq_at = result.equity.reindex(change_times).dropna()
    pnls = eq_at.diff().dropna()
    return pnls.reset_index(drop=True)


def report(metrics: dict, title: str = "Backtest") -> str:
    """Định dạng metrics thành bảng text dễ đọc."""
    pct = lambda x: f"{x * 100:+.2f}%"
    lines = [
        f"\n{'=' * 46}",
        f" {title}",
        f"{'=' * 46}",
        f" Vốn cuối kỳ      : ${metrics['final_equity']:,.0f}",
        f" Tổng lợi nhuận   : {pct(metrics['total_return'])}",
        f" CAGR             : {pct(metrics['cagr'])}",
        f" Sharpe (năm)     : {metrics['sharpe']:.2f}",
        f" Sortino (năm)    : {metrics['sortino']:.2f}",
        f" Max drawdown     : {pct(metrics['max_drawdown'])}",
        f" Calmar           : {metrics['calmar']:.2f}",
        f" Số lệnh          : {metrics['n_trades']}",
        f" Win rate         : {pct(metrics['win_rate'])}",
        f" Profit factor    : {metrics['profit_factor']:.2f}",
        f" Lãi/lệnh TB      : ${metrics['avg_trade']:,.2f}",
        f" Exposure         : {pct(metrics['exposure'])}",
        f" Tổng chi phí     : ${metrics['total_cost']:,.0f}",
        f" Số năm dữ liệu   : {metrics['years']:.2f}",
        f"{'=' * 46}",
    ]
    return "\n".join(lines)
