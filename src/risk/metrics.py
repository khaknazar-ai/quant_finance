from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class PerformanceMetrics:
    cumulative_return: float
    cagr: float
    annualized_volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    monthly_win_rate: float
    observation_count: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def calculate_equity_curve(
    returns: pd.Series,
    initial_capital: float = 1.0,
) -> pd.Series:
    """Convert periodic returns into an equity curve."""
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive.")

    clean_returns = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    return initial_capital * (1.0 + clean_returns).cumprod()


def calculate_drawdown_series(equity_curve: pd.Series) -> pd.Series:
    """Calculate drawdown series from an equity curve."""
    clean_equity = pd.to_numeric(equity_curve, errors="coerce").dropna().astype(float)

    if clean_equity.empty:
        return pd.Series(dtype=float)

    if (clean_equity <= 0).any():
        raise ValueError("equity_curve must be strictly positive.")

    running_max = clean_equity.cummax()
    return clean_equity / running_max - 1.0


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Return maximum drawdown as a negative number."""
    drawdowns = calculate_drawdown_series(equity_curve)

    if drawdowns.empty:
        return math.nan

    return float(drawdowns.min())


def calculate_cagr(
    equity_curve: pd.Series,
    initial_capital: float = 1.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate compound annual growth rate from an equity curve.

    The equity curve produced by calculate_equity_curve starts after the first
    return is applied. Therefore CAGR is measured from the known initial capital
    to the final equity value, not from the first equity row.
    """
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive.")

    clean_equity = pd.to_numeric(equity_curve, errors="coerce").dropna().astype(float)

    if clean_equity.empty:
        return math.nan

    end_value = float(clean_equity.iloc[-1])

    if end_value <= 0:
        return math.nan

    years = len(clean_equity) / periods_per_year
    if years <= 0:
        return math.nan

    return float((end_value / initial_capital) ** (1.0 / years) - 1.0)


def calculate_annualized_volatility(
    returns: pd.Series,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate annualized volatility from periodic returns."""
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna().astype(float)

    if len(clean_returns) < 2:
        return math.nan

    return float(clean_returns.std(ddof=1) * np.sqrt(periods_per_year))


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate annualized Sharpe ratio."""
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna().astype(float)

    if len(clean_returns) < 2:
        return math.nan

    daily_risk_free_rate = risk_free_rate / periods_per_year
    excess_returns = clean_returns - daily_risk_free_rate
    volatility = excess_returns.std(ddof=1)

    if volatility == 0 or math.isnan(volatility):
        return math.nan

    return float(excess_returns.mean() / volatility * np.sqrt(periods_per_year))


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate annualized Sortino ratio using downside volatility."""
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna().astype(float)

    if len(clean_returns) < 2:
        return math.nan

    daily_risk_free_rate = risk_free_rate / periods_per_year
    excess_returns = clean_returns - daily_risk_free_rate
    downside_returns = excess_returns[excess_returns < 0.0]

    if len(downside_returns) < 2:
        return math.nan

    downside_deviation = downside_returns.std(ddof=1) * np.sqrt(periods_per_year)

    if downside_deviation == 0 or math.isnan(downside_deviation):
        return math.nan

    annualized_excess_return = excess_returns.mean() * periods_per_year
    return float(annualized_excess_return / downside_deviation)


def calculate_monthly_win_rate(returns: pd.Series) -> float:
    """Calculate the fraction of months with positive compounded returns."""
    if not isinstance(returns.index, pd.DatetimeIndex):
        return math.nan

    clean_returns = pd.to_numeric(returns, errors="coerce").dropna().astype(float)

    if clean_returns.empty:
        return math.nan

    monthly_returns = (1.0 + clean_returns).resample("ME").prod() - 1.0

    if monthly_returns.empty:
        return math.nan

    return float((monthly_returns > 0.0).mean())


def calculate_performance_metrics(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> PerformanceMetrics:
    """Calculate common portfolio performance metrics."""
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna().astype(float)

    if clean_returns.empty:
        raise ValueError("returns must contain at least one non-null value.")

    equity_curve = calculate_equity_curve(clean_returns)
    cumulative_return = float(equity_curve.iloc[-1] - 1.0)
    cagr = calculate_cagr(
        equity_curve,
        initial_capital=1.0,
        periods_per_year=periods_per_year,
    )
    annualized_volatility = calculate_annualized_volatility(
        clean_returns,
        periods_per_year=periods_per_year,
    )
    sharpe = calculate_sharpe_ratio(
        clean_returns,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )
    sortino = calculate_sortino_ratio(
        clean_returns,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )
    max_drawdown = calculate_max_drawdown(equity_curve)

    if max_drawdown < 0 and not math.isnan(cagr):
        calmar = float(cagr / abs(max_drawdown))
    else:
        calmar = math.nan

    monthly_win_rate = calculate_monthly_win_rate(clean_returns)

    return PerformanceMetrics(
        cumulative_return=cumulative_return,
        cagr=cagr,
        annualized_volatility=annualized_volatility,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=max_drawdown,
        calmar=calmar,
        monthly_win_rate=monthly_win_rate,
        observation_count=int(len(clean_returns)),
    )
