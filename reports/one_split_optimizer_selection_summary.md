# One-Split Optimizer Train-to-Test Selection

## Protocol

- Evaluation type: `one_split_optimizer_train_test_selection`.
- NSGA-II is fit only on the train window.
- Selection rule is fixed before test evaluation.
- Test data is not used for candidate selection.
- This is one OOS split only, not final walk-forward evidence.
- Split index: `0`.
- Train window: `2011-01-04` to `2016-12-31`.
- Test window: `2017-01-01` to `2017-12-31`.
- Selection metric: `sharpe`.
- Transaction cost for selected strategy: `10.0` bps.

## Selected Candidate

- Candidate ID: `evaluation_0022`.
- Strategy: `factor_rotation_m126_v126_d252_mw1.26333_vw1.51618_dw0.746887_top6_maxw0.280131`.
- Train CAGR: 10.39%.
- Train Sharpe: 1.326.
- Train Max Drawdown: -8.85%.

## Selected Candidate OOS Test Metrics

- Test valid: `True`.
- Test CAGR: 16.48%.
- Test Sharpe: 2.603.
- Test Max Drawdown: -1.81%.
- Test observations: `231`.

## Train-to-Test Degradation

- CAGR test-minus-train: 6.09%.
- Sharpe test-minus-train: 1.277.
- MaxDD test-minus-train: 7.04%.

## Common Test-Window Comparison

- Common window: `2017-02-01` to `2017-12-29`.
- Common observations: `231`.

| Strategy | CAGR | Sharpe | Max Drawdown | Calmar | Final Equity |
|---|---:|---:|---:|---:|---:|
| `optimizer_selected_net` | 16.48% | 2.603 | -1.81% | 9.104 | 1.150 |
| `buy_hold_SPY` | 21.52% | 2.915 | -2.61% | 8.247 | 1.196 |
| `equal_weight` | 15.92% | 3.032 | -2.00% | 7.972 | 1.145 |

## Test Metric Leaders

- highest_test_cagr: `buy_hold_SPY`, value `0.215240`
- highest_test_sharpe: `equal_weight`, value `3.032176`
- least_severe_test_max_drawdown: `optimizer_selected_net`, value `-0.018103`
- highest_test_calmar: `optimizer_selected_net`, value `9.104189`

## Interpretation Rule

This is one-split OOS evidence only. It can reveal obvious overfitting or degradation, but it must not be treated as final strategy performance. Final conclusions require full walk-forward optimizer selection across all available splits and comparison against the complete baseline suite.
