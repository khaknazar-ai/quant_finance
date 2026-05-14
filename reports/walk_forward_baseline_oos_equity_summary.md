# Stitched Walk-Forward OOS Equity Summary

This report is generated from `reports/walk_forward_baseline_oos_equity_summary.json`.
Do not manually edit metric values in this file.

## Evaluation protocol

- Evaluation type: `walk_forward_baseline_oos_stitched_equity`
- Benchmark: `SPY`
- Strategy count: 4
- Evaluated split count: 9
- Return alignment: `exact_common_date_intersection_per_split`
- Equity base: 1.0
- Transaction cost bps: 10.0
- Cost model: `net_return = gross_return - turnover * bps / 10000`
- Turnover convention: `sum_abs_weight_change`
- Momentum lookback: 252 trading days
- Momentum top-K: 5
- Momentum rebalance frequency: `ME`

## Stitched OOS metrics

| Strategy | Final Equity | CAGR | Sharpe | Max Drawdown | Calmar | Cumulative Return | Observations |
|---|---:|---:|---:|---:|---:|---:|---:|
| buy_hold_SPY | 3.524 | 15.06% | 0.852 | -33.72% | 0.447 | 252.38% | 2262 |
| equal_weight | 2.444 | 10.47% | 0.856 | -25.66% | 0.408 | 144.36% | 2262 |
| momentum_top_5_252d_gross | 3.081 | 13.35% | 0.924 | -22.54% | 0.592 | 208.06% | 2262 |
| momentum_top_5_252d_net_10bps | 2.960 | 12.85% | 0.894 | -22.57% | 0.569 | 196.03% | 2262 |

## Stitched OOS leaders

- Highest stitched CAGR: `buy_hold_SPY`
- Highest stitched Sharpe: `momentum_top_5_252d_gross`
- Least severe stitched max drawdown: `momentum_top_5_252d_gross`
- Highest final equity: `buy_hold_SPY`

## OOS split windows

| Split | Common OOS Window | Observations |
|---:|---|---:|
| 0 | 2017-01-03 -> 2017-12-29 | 251 |
| 1 | 2018-01-02 -> 2018-12-31 | 251 |
| 2 | 2019-01-02 -> 2019-12-31 | 252 |
| 3 | 2020-01-02 -> 2020-12-31 | 253 |
| 4 | 2021-01-04 -> 2021-12-31 | 252 |
| 5 | 2022-01-03 -> 2022-12-30 | 251 |
| 6 | 2023-01-03 -> 2023-12-29 | 250 |
| 7 | 2024-01-02 -> 2024-12-31 | 252 |
| 8 | 2025-01-02 -> 2025-12-31 | 250 |

## Interpretation rule

This stitched equity report compounds all non-overlapping OOS test-window returns into one continuous OOS equity curve.
It complements the split-level report, where mean split CAGR is the arithmetic average of annual OOS CAGRs.
A strategy can have lower CAGR but higher Sharpe or lower drawdown. That must be described as a risk-return trade-off, not overall outperformance.
