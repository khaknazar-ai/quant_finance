# Walk-Forward Baseline Summary

This report is generated from `reports/walk_forward_baseline_metrics.json`.
Do not manually edit metric values in this file.

## Evaluation protocol

- Evaluation type: `walk_forward_baseline_oos`
- Benchmark: `SPY`
- Strategy count: 4
- Evaluated split count: 9
- Return alignment: `exact_common_date_intersection_per_split`
- Transaction cost bps: 10.0
- Cost model: `net_return = gross_return - turnover * bps / 10000`
- Turnover convention: `sum_abs_weight_change`
- Momentum lookback: 252 trading days
- Momentum top-K: 5
- Momentum rebalance frequency: `ME`

## Aggregate OOS metrics

| Strategy | Mean CAGR | Mean Sharpe | Mean MaxDD | Mean Calmar | Positive CAGR Splits | Worst CAGR Split | Best CAGR Split |
|---|---:|---:|---:|---:|---:|---:|---:|
| buy_hold_SPY | 16.26% | 1.289 | -14.34% | 2.757 | 77.78% | 5 | 2 |
| equal_weight | 11.01% | 1.254 | -10.15% | 2.588 | 77.78% | 5 | 2 |
| momentum_top_5_252d_gross | 13.83% | 1.135 | -11.88% | 1.882 | 88.89% | 1 | 8 |
| momentum_top_5_252d_net_10bps | 13.32% | 1.099 | -11.93% | 1.814 | 88.89% | 1 | 8 |

## Aggregate single-metric leaders

- Highest mean CAGR: `buy_hold_SPY`
- Highest mean Sharpe: `buy_hold_SPY`
- Least severe mean max drawdown: `equal_weight`
- Highest mean Calmar: `buy_hold_SPY`

## Split-level CAGR leaders

| Split | Test Window | Highest-CAGR Strategy |
|---:|---|---|
| 0 | 2017-01-01 -> 2017-12-31 | buy_hold_SPY |
| 1 | 2018-01-01 -> 2018-12-31 | buy_hold_SPY |
| 2 | 2019-01-01 -> 2019-12-31 | buy_hold_SPY |
| 3 | 2020-01-01 -> 2020-12-31 | momentum_top_5_252d_gross |
| 4 | 2021-01-01 -> 2021-12-31 | buy_hold_SPY |
| 5 | 2022-01-01 -> 2022-12-31 | momentum_top_5_252d_gross |
| 6 | 2023-01-01 -> 2023-12-31 | buy_hold_SPY |
| 7 | 2024-01-01 -> 2024-12-31 | buy_hold_SPY |
| 8 | 2025-01-01 -> 2025-12-31 | momentum_top_5_252d_gross |

## Interpretation rule

Mean split CAGR is the arithmetic average of annual OOS split CAGRs.
It is not the same as CAGR from one stitched equity curve.
A strategy with lower mean CAGR but lower drawdown should be described as a risk-return trade-off, not as overall outperformance.
