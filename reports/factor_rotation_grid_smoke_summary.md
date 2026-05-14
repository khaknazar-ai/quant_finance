# Factor Rotation Grid Smoke Evaluation

## Protocol

- Evaluation type: `factor_rotation_grid_smoke_train_only`.
- This is a deterministic smoke grid, not evolutionary optimization.
- Results are train-window only and must not be reported as OOS performance.
- Train window: `2011-01-04` to `2016-12-31`.
- Transaction cost: `10.0` bps.
- Candidate count: `8`.
- Valid candidates: `8`.
- Invalid candidates: `0`.

## Leaders

- highest_train_sharpe: `candidate_001` (`factor_rotation_m126_v63_d126_mw1_vw0.5_dw0.5_top5_maxw0.4`), value `1.085185`
- highest_train_cagr: `candidate_001` (`factor_rotation_m126_v63_d126_mw1_vw0.5_dw0.5_top5_maxw0.4`), value `0.105461`
- least_severe_train_max_drawdown: `candidate_003` (`factor_rotation_m126_v21_d63_mw0.5_vw1_dw1_top5_maxw0.4`), value `-0.096827`
- lowest_average_turnover: `candidate_002` (`factor_rotation_m252_v63_d126_mw1_vw1_dw0.5_top5_maxw0.4`), value `0.022779`

## Candidate Metrics

| Candidate | Valid | CAGR | Sharpe | Max Drawdown | Avg Turnover | Top-K | Windows | Factor Weights |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `candidate_001` | True | 10.55% | 1.085 | -12.62% | 0.028 | 5 | m=126, v=63, d=126 | mw=1.0, vw=0.5, dw=0.5 |
| `candidate_005` | True | 7.90% | 0.866 | -16.36% | 0.043 | 3 | m=126, v=126, d=126 | mw=1.0, vw=1.0, dw=1.0 |
| `candidate_002` | True | 7.25% | 0.861 | -12.20% | 0.023 | 5 | m=252, v=63, d=126 | mw=1.0, vw=1.0, dw=0.5 |
| `candidate_007` | True | 7.60% | 0.829 | -13.42% | 0.041 | 2 | m=126, v=63, d=126 | mw=1.0, vw=0.5, dw=0.5 |
| `candidate_003` | True | 5.74% | 0.767 | -9.68% | 0.032 | 5 | m=126, v=21, d=63 | mw=0.5, vw=1.0, dw=1.0 |
| `candidate_006` | True | 6.20% | 0.614 | -16.91% | 0.045 | 3 | m=252, v=126, d=252 | mw=1.0, vw=0.5, dw=1.0 |
| `candidate_000` | True | 4.58% | 0.443 | -24.76% | 0.038 | 5 | m=63, v=21, d=63 | mw=1.0, vw=0.0, dw=0.0 |
| `candidate_004` | True | 1.70% | 0.203 | -22.69% | 0.051 | 3 | m=63, v=63, d=63 | mw=1.0, vw=0.5, dw=0.0 |

## Interpretation Rule

This report only verifies that the objective function behaves sensibly on real data. It must not be used to claim outperformance. Final conclusions require walk-forward optimizer selection and out-of-sample evaluation against baselines.
