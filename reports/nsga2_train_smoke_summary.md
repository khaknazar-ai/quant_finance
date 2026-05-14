# NSGA-II Train-Only Smoke Optimization

## Protocol

- Evaluation type: `nsga2_factor_rotation_train_smoke`.
- This validates optimizer plumbing on one train window.
- This is not walk-forward selection and not OOS evidence.
- Train window: `2011-01-04` to `2016-12-31`.
- Population size: `12`.
- Generations: `3`.
- Seed: `42`.
- Transaction cost: `10.0` bps.
- Evaluation count: `36`.
- Valid evaluations: `36`.
- Invalid evaluations: `0`.
- Pareto candidates: `9`.

## Train Leaders

- highest_train_sharpe: `evaluation_0022` (`factor_rotation_m126_v126_d252_mw1.26333_vw1.51618_dw0.746887_top6_maxw0.280131`), value `1.326024`
- highest_train_cagr: `evaluation_0019` (`factor_rotation_m126_v63_d126_mw0.333946_vw0.0350276_dw0.22656_top5_maxw0.338563`), value `0.127919`
- least_severe_train_max_drawdown: `evaluation_0007` (`factor_rotation_m126_v63_d63_mw0.22906_vw1.33681_dw0.942192_top4_maxw0.4295`), value `-0.079419`
- lowest_average_turnover: `evaluation_0029` (`factor_rotation_m126_v63_d63_mw0.22906_vw1.33681_dw0.713436_top6_maxw0.425202`), value `0.015140`

## Top Valid Evaluations by Train Sharpe

| Candidate | CAGR | Sharpe | Max Drawdown | Avg Turnover | Strategy |
|---|---:|---:|---:|---:|---|
| `evaluation_0022` | 10.39% | 1.326 | -8.85% | 0.016 | `factor_rotation_m126_v126_d252_mw1.26333_vw1.51618_dw0.746887_top6_maxw0.280131` |
| `evaluation_0019` | 12.79% | 1.234 | -13.00% | 0.027 | `factor_rotation_m126_v63_d126_mw0.333946_vw0.0350276_dw0.22656_top5_maxw0.338563` |
| `evaluation_0014` | 8.00% | 1.203 | -8.24% | 0.022 | `factor_rotation_m126_v21_d63_mw0.0147245_vw1.57385_dw0.69344_top6_maxw0.434523` |
| `evaluation_0033` | 9.51% | 1.146 | -9.61% | 0.020 | `factor_rotation_m126_v126_d252_mw1.23682_vw1.69976_dw1.72668_top6_maxw0.286498` |
| `evaluation_0027` | 7.39% | 1.137 | -9.89% | 0.017 | `factor_rotation_m126_v126_d252_mw0.651245_vw1.51618_dw0.746887_top4_maxw0.280131` |
| `evaluation_0031` | 7.36% | 1.109 | -8.24% | 0.022 | `factor_rotation_m126_v21_d63_mw0.0147245_vw1.69179_dw0.69344_top6_maxw0.438908` |
| `evaluation_0010` | 11.54% | 1.099 | -13.17% | 0.030 | `factor_rotation_m126_v63_d252_mw0.333946_vw0.0454241_dw0.180096_top5_maxw0.338563` |
| `evaluation_0002` | 8.77% | 1.091 | -8.85% | 0.023 | `factor_rotation_m126_v21_d252_mw1.26333_vw1.51618_dw0.709052_top6_maxw0.467936` |
| `evaluation_0024` | 8.77% | 1.091 | -8.85% | 0.023 | `factor_rotation_m126_v21_d252_mw1.26333_vw1.51618_dw0.746887_top6_maxw0.284517` |
| `evaluation_0026` | 11.67% | 1.087 | -13.17% | 0.028 | `factor_rotation_m126_v63_d252_mw1.28672_vw0.0350276_dw0.716781_top5_maxw0.458501` |

## Pareto Front Objectives

| Pareto ID | Negative Sharpe | Negative CAGR | MaxDD Abs | Avg Turnover | Strategy |
|---|---:|---:|---:|---:|---|
| `pareto_000` | -1.090648 | -0.087705 | 0.088534 | 0.022886 | `factor_rotation_m126_v21_d252_mw1.26333_vw1.51618_dw0.709052_top6_maxw0.467936` |
| `pareto_001` | -0.772965 | -0.047661 | 0.079419 | 0.024908 | `factor_rotation_m126_v63_d63_mw0.22906_vw1.33681_dw0.942192_top4_maxw0.4295` |
| `pareto_002` | -1.202691 | -0.080004 | 0.082399 | 0.021734 | `factor_rotation_m126_v21_d63_mw0.0147245_vw1.57385_dw0.69344_top6_maxw0.434523` |
| `pareto_003` | -1.234435 | -0.127919 | 0.129974 | 0.027399 | `factor_rotation_m126_v63_d126_mw0.333946_vw0.0350276_dw0.22656_top5_maxw0.338563` |
| `pareto_004` | -1.326024 | -0.103911 | 0.088534 | 0.016424 | `factor_rotation_m126_v126_d252_mw1.26333_vw1.51618_dw0.746887_top6_maxw0.280131` |
| `pareto_005` | -1.090648 | -0.087705 | 0.088534 | 0.022886 | `factor_rotation_m126_v21_d252_mw1.26333_vw1.51618_dw0.746887_top6_maxw0.284517` |
| `pareto_006` | -1.077679 | -0.106219 | 0.128203 | 0.026374 | `factor_rotation_m126_v63_d126_mw0.333946_vw0.03744_dw0.22656_top6_maxw0.337545` |
| `pareto_007` | -1.031412 | -0.069843 | 0.093684 | 0.015140 | `factor_rotation_m126_v63_d63_mw0.22906_vw1.33681_dw0.713436_top6_maxw0.425202` |
| `pareto_008` | -1.108558 | -0.073630 | 0.082399 | 0.022222 | `factor_rotation_m126_v21_d63_mw0.0147245_vw1.69179_dw0.69344_top6_maxw0.438908` |

## Interpretation Rule

This report confirms that NSGA-II can search the factor-rotation parameter space and produce Pareto candidates on train data. It must not be used to claim strategy outperformance. Final evidence requires walk-forward train selection and out-of-sample test-window evaluation against baselines.
