# Stitched Walk-Forward OOS Equity Report

## Protocol

- Uses selected candidates from the frozen walk-forward optimizer report.
- No re-optimization is performed in this step.
- Each split is aligned to the exact common OOS date intersection.
- Daily OOS returns are stitched into continuous equity curves.
- Evaluated splits: `9`.
- Stitched window: `2017-02-01` to `2025-12-31`.
- Transaction cost: `10.0` bps.

## Stitched OOS Metrics

| Strategy | Stitched CAGR | Sharpe | Max Drawdown | Calmar | Final Equity | Observations |
|---|---:|---:|---:|---:|---:|---:|
| `buy_hold_SPY` | 13.87% | 0.785 | -33.72% | 0.411 | 2.920 | 2079 |
| `equal_weight` | 9.12% | 0.746 | -25.66% | 0.355 | 2.054 | 2079 |
| `momentum_top_5_252d_gross` | 11.87% | 0.825 | -22.54% | 0.526 | 2.522 | 2079 |
| `momentum_top_5_252d_net_10bps` | 11.31% | 0.793 | -22.57% | 0.501 | 2.421 | 2079 |
| `optimizer_selected_net` | 6.13% | 0.642 | -18.52% | 0.331 | 1.633 | 2079 |

## Stitched Metric Leaders

- highest_stitched_cagr: `buy_hold_SPY`, value `0.138689`
- highest_stitched_sharpe: `momentum_top_5_252d_gross`, value `0.825397`
- least_severe_stitched_max_drawdown: `optimizer_selected_net`, value `-0.185171`
- highest_stitched_calmar: `momentum_top_5_252d_gross`, value `0.526455`
- highest_final_equity: `buy_hold_SPY`, value `2.919728`

## Optimizer vs SPY Deltas

- cagr_optimizer_minus_spy: -7.74%
- sharpe_optimizer_minus_spy: -0.143
- max_drawdown_optimizer_minus_spy: 15.20%
- calmar_optimizer_minus_spy: -0.080
- final_equity_optimizer_minus_spy: -1.286

## Interpretation Rule

This report should not be framed as broad optimizer outperformance unless the optimizer wins the relevant return and risk-adjusted metrics. If it mainly improves drawdown while losing CAGR or final equity versus SPY, the correct interpretation is a risk-control trade-off.
