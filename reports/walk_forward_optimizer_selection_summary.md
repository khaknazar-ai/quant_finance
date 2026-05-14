# Walk-Forward Optimizer Selection OOS Report

## Protocol

- Evaluation type: `walk_forward_optimizer_selection_oos`.
- For each split, NSGA-II is fit only on the train window.
- Candidate selection uses a fixed train metric before test evaluation.
- Test data is not used for candidate selection.
- Selection metric: `sharpe`.
- Evaluated splits: `9`.
- Population size: `12`.
- Generations: `3`.
- Seed policy: `base_seed + split_index`.
- Transaction cost: `10.0` bps.

## Aggregate OOS Metrics

| Strategy | Mean CAGR | Mean Sharpe | Mean MaxDD | Mean Calmar | Positive CAGR Fraction | Splits |
|---|---:|---:|---:|---:|---:|---:|
| `buy_hold_SPY` | 15.00% | 1.215 | -14.07% | 2.619 | 77.78% | 9 |
| `equal_weight` | 9.65% | 1.110 | -10.10% | 2.322 | 77.78% | 9 |
| `momentum_top_5_252d_gross` | 12.62% | 1.038 | -11.88% | 1.826 | 77.78% | 9 |
| `momentum_top_5_252d_net_10bps` | 12.06% | 1.000 | -11.93% | 1.752 | 77.78% | 9 |
| `optimizer_selected_net` | 6.44% | 0.864 | -8.25% | 1.823 | 77.78% | 9 |

## Split Metric Winner Counts

- highest_test_cagr: `buy_hold_SPY`: 4, `momentum_top_5_252d_gross`: 4, `optimizer_selected_net`: 1
- highest_test_sharpe: `buy_hold_SPY`: 3, `equal_weight`: 2, `momentum_top_5_252d_gross`: 2, `optimizer_selected_net`: 2
- least_severe_test_max_drawdown: `equal_weight`: 3, `optimizer_selected_net`: 6
- highest_test_calmar: `buy_hold_SPY`: 4, `equal_weight`: 1, `momentum_top_5_252d_gross`: 2, `optimizer_selected_net`: 2

## Selected Candidate Train-to-Test Degradation

- mean_cagr_test_minus_train: -2.76%
- mean_calmar_test_minus_train: 1.079
- mean_max_drawdown_test_minus_train: 4.91%
- mean_sharpe_test_minus_train: -0.223

## Split-Level Selected Strategy Results

| Split | Test Window | Selected Candidate | Test CAGR | Test Sharpe | Test MaxDD | Common Window |
|---:|---|---|---:|---:|---:|---|
| 0 | `2017-01-01` to `2017-12-31` | `evaluation_0022` | 16.48% | 2.603 | -1.81% | `2017-02-01` to `2017-12-29` |
| 1 | `2018-01-01` to `2018-12-31` | `evaluation_0028` | -7.07% | -0.468 | -10.37% | `2018-02-01` to `2018-12-31` |
| 2 | `2019-01-01` to `2019-12-31` | `evaluation_0018` | 4.33% | 0.941 | -2.84% | `2019-02-01` to `2019-12-31` |
| 3 | `2020-01-01` to `2020-12-31` | `evaluation_0033` | 11.66% | 0.989 | -12.90% | `2020-02-03` to `2020-12-31` |
| 4 | `2021-01-01` to `2021-12-31` | `evaluation_0001` | 13.38% | 1.645 | -5.44% | `2021-02-01` to `2021-12-31` |
| 5 | `2022-01-01` to `2022-12-31` | `evaluation_0013` | -7.42% | -0.666 | -15.54% | `2022-02-01` to `2022-12-30` |
| 6 | `2023-01-01` to `2023-12-31` | `evaluation_0026` | 5.26% | 0.502 | -9.15% | `2023-02-01` to `2023-12-29` |
| 7 | `2024-01-01` to `2024-12-31` | `evaluation_0034` | 9.47% | 0.789 | -10.54% | `2024-02-01` to `2024-12-31` |
| 8 | `2025-01-01` to `2025-12-31` | `evaluation_0003` | 11.84% | 1.439 | -5.64% | `2025-02-03` to `2025-12-31` |

## Interpretation Rule

This report is the first full walk-forward optimizer-selection evidence. It must be interpreted against baselines. If the optimizer has lower CAGR but better drawdown or Calmar, describe that as a risk-control trade-off, not broad outperformance.
