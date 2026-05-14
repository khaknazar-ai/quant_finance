# Baseline Metrics Summary

This report is generated from `reports/baseline_metrics.json`.
Do not manually edit metric values in this file.

## Evaluation protocol

- Benchmark: `SPY`
- Strategy count: 4
- Return alignment: `exact_common_date_intersection`
- Common date range: 2011-02-01 -> 2026-05-13
- Common observations: 3843
- Price column: `adjusted_close`
- Risk-free rate: 0.00%
- Momentum lookback: 252 trading days
- Momentum top-K: 5
- Momentum rebalance frequency: `ME`

## Metrics

| Strategy | CAGR | Sharpe | Max Drawdown | Calmar | Ann. Volatility | Monthly Win Rate | Cumulative Return | Observations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| buy_hold_SPY | 14.19% | 0.861 | -33.72% | 0.421 | 17.12% | 69.02% | 656.64% | 3843 |
| equal_weight | 9.47% | 0.827 | -25.66% | 0.369 | 11.79% | 67.39% | 297.58% | 3843 |
| momentum_top_5_252d_gross | 11.71% | 0.861 | -22.54% | 0.520 | 14.01% | 67.93% | 441.42% | 3843 |
| momentum_top_5_252d_net_10bps | 11.20% | 0.829 | -22.57% | 0.496 | 14.00% | 66.85% | 405.00% | 3843 |

## Single-metric leaders

- Highest CAGR: `buy_hold_SPY`
- Highest Sharpe: `momentum_top_5_252d_gross`
- Least severe max drawdown: `momentum_top_5_252d_gross`
- Highest Calmar: `momentum_top_5_252d_gross`

## Interpretation rule

A single-metric leader is not automatically the best overall strategy.
If one strategy has higher CAGR but another has lower drawdown, report it as a risk-return trade-off.
Do not describe a lower-return strategy as outperforming unless the metric being discussed is explicitly named.
