# Evolutionary Quant Finance Research Pipeline

## Overview

This project is a reproducible quantitative finance research pipeline for ETF tactical allocation.

The system evaluates allocation strategies across a diversified ETF universe using:

- leakage-safe feature engineering;
- walk-forward validation;
- transaction-cost-aware backtesting;
- evolutionary multi-objective optimization.

The project does not try to predict individual stock prices directly. Instead, it searches for robust allocation rules and evaluates them out of sample.

## Problem

Many quant finance notebooks look impressive but are not reliable because they often include:

- look-ahead bias;
- weak validation;
- no transaction costs;
- manual data fixes;
- parameter tuning on the full historical period;
- weak benchmark comparison.

This project is designed to avoid those issues.

## Final Status

Project status: complete and GitHub-ready.

Completed:
  * D-drive-safe research environment and reproducible project structure;
  * yfinance OHLCV ingestion with canonical schema and Pandera validation;
  * leakage-safe technical feature generation;
  * transaction-cost-aware backtesting engine;
  * SPY, equal-weight, momentum, and factor-rotation baselines;
  * NSGA-II evolutionary train-window optimizer;
  * one-split and full walk-forward optimizer selection;
  * stitched out-of-sample equity analysis;
  * final research notebook with visible mixed/negative results;
  * artifact inventory, final hygiene checks, and reproducibility verification.

Final quality gates:
  * pytest: 191 passed;
  * artifact inventory: 34 required artifacts, 0 missing;
  * final hygiene check: passed;
  * reproducibility check: passed with difference_count = 0;
  * forbidden files check: no secrets, caches, checkpoints, or generated raw data committed.

Research conclusion:
  * The optimizer did not outperform SPY on stitched final equity, stitched CAGR, stitched Sharpe, or Calmar.
  * The optimizer did reduce stitched maximum drawdown.
  * The correct interpretation is a risk-control trade-off, not a broad performance advantage.

## Reports and Artifacts

The main report index is available in [`docs/report_index.md`](docs/report_index.md).

Generated metrics in `reports/*.json` and their generated Markdown summaries are the source of truth. README text should not override those artifacts.

Key reviewer-facing artifacts:

- [`docs/experimental_protocol.md`](docs/experimental_protocol.md)  -  experimental integrity protocol.
- [`reports/baseline_metrics_summary.md`](reports/baseline_metrics_summary.md)  -  full-period baseline sanity check.
- [`reports/walk_forward_baseline_summary.md`](reports/walk_forward_baseline_summary.md)  -  walk-forward split-level OOS baseline summary.
- [`reports/walk_forward_baseline_oos_equity_summary.md`](reports/walk_forward_baseline_oos_equity_summary.md)  -  stitched OOS baseline equity summary.
- `reports/factor_rotation_grid_smoke_summary.md` — train-only deterministic smoke check for the optimizer-ready factor-rotation objective. Not OOS evidence.
- `reports/nsga2_train_smoke_summary.md` — train-only NSGA-II optimizer smoke report. Validates optimizer plumbing; not OOS evidence.
- `reports/one_split_optimizer_selection_summary.md` — first one-split train-to-test optimizer selection report. OOS smoke only; not final walk-forward evidence.
- `reports/walk_forward_optimizer_selection_summary.md` — full walk-forward optimizer-selection report across all OOS splits. Main optimizer evidence; risk-control trade-off, not broad outperformance.
- `reports/walk_forward_optimizer_stitched_oos_equity_summary.md` — stitched 2017-2025 OOS equity report. SPY leads CAGR/final equity; optimizer improves max drawdown, so the result is a risk-control trade-off.
- `notebooks/01_research_results_review.ipynb` — final research-results notebook with visible mixed/negative results and risk-control trade-off interpretation.
- [`reports/report_artifact_inventory.json`](reports/report_artifact_inventory.json)  -  required artifact inventory.

Baseline evidence currently has three layers:

1. Full-period baseline sanity check.
2. Walk-forward annual OOS split evaluation.
3. Stitched continuous OOS equity curve.

Interpretation rule: a lower-CAGR strategy with better Sharpe or lower drawdown is a risk-return trade-off, not overall outperformance.

<!-- REPORT_ARTIFACTS_END -->

<!-- FINAL_README_POLISH_START -->

## Final Research Summary

This project is a reproducible quantitative finance research pipeline
for walk-forward ETF allocation. It evaluates simple baselines,
a factor-rotation strategy, and an NSGA-II evolutionary optimizer
under a fixed out-of-sample protocol.

The final result is intentionally reported as a mixed result.
The optimizer did not outperform SPY on stitched final equity,
stitched CAGR, or stitched Sharpe. It did reduce stitched max
drawdown. The correct interpretation is a risk-control trade-off,
not a broad performance advantage.

### Architecture

```text
configs/
  universe, features, walk-forward protocol, optimizer search space

src/
  config/        pydantic configuration loading and validation
  ingestion/     yfinance OHLCV download and canonicalization
  validation/    pandera data-quality checks
  features/      momentum, volatility, drawdown, cross-sectional ranks
  backtesting/   execution lag, long-only weights, turnover, costs
  strategies/    SPY, equal-weight, momentum, factor rotation
  optimization/  NSGA-II train-window objective evaluation
  risk/          CAGR, Sharpe, Sortino, MaxDD, Calmar
  reporting/     generated report artifacts

scripts/
  report generation, optimizer selection, stitched OOS equity,
  reproducibility checks, artifact inventory checks

notebooks/
  final research review notebook with visible mixed results
```

### Evaluation Protocol

- Universe: ETF tactical allocation universe from
  `configs/universe_etf.yaml`.
- Walk-forward design: 6-year train windows and 1-year OOS test
  windows.
- Evaluated OOS splits: 9.
- Stitched OOS window:
  2017-02-01 to 2025-12-31.
- Optimization: NSGA-II is run only on train windows.
- Selection rule: fixed train Sharpe selection before test evaluation.
- Execution: one-day lag between target weights and realized returns.
- Costs: transaction-cost-aware net returns for optimizer and net
  momentum.
- Comparison: strategies are aligned on exact common OOS dates.
- Reproducibility: generated reports are compared against a reference
  snapshot.

### Final Stitched OOS Results

| Strategy | Final Equity | CAGR | Sharpe | Max Drawdown | Calmar |
|---|---:|---:|---:|---:|---:|
| SPY buy-and-hold | 2.920 | 13.87% | 0.785 | -33.72% | 0.411 |
| Equal weight | 2.054 | 9.12% | 0.746 | -25.66% | 0.355 |
| Momentum top-5 gross | 2.522 | 11.87% | 0.825 | -22.54% | 0.526 |
| Momentum top-5 net 10 bps | 2.421 | 11.31% | 0.793 | -22.57% | 0.501 |
| Optimizer selected net | 1.633 | 6.13% | 0.642 | -18.52% | 0.331 |

### Optimizer vs SPY

| Metric | Optimizer - SPY |
|---|---:|
| CAGR delta | -7.74% |
| Sharpe delta | -0.143 |
| Max drawdown delta | 15.20% |
| Calmar delta | -0.080 |
| Final equity delta | -1.286 |

### Full Walk-Forward Selection Summary

| Strategy | Mean OOS CAGR | Mean OOS Sharpe | Mean OOS Max Drawdown |
|---|---:|---:|---:|
| SPY buy-and-hold | 15.00% | 1.215 | -14.07% |
| Optimizer selected net | 6.44% | 0.864 | -8.25% |

### Interpretation

The optimizer selected net strategy produced the least severe stitched
max drawdown, but it did not exceed SPY on final equity, CAGR, Sharpe,
or Calmar. Momentum gross produced the best stitched Sharpe and
Calmar. SPY produced the best stitched final equity and CAGR.

This is a useful negative/mixed research result: the optimizer worked
as a defensive allocation mechanism, but the defensive profile came
with a large return sacrifice.

### Key Artifacts

| Artifact | Purpose |
|---|---|
| `docs/experimental_protocol.md` | Research-integrity rules |
| `docs/report_index.md` | Index of generated evidence artifacts |
| `reports/walk_forward_optimizer_selection_summary.md` | Full WF OOS |
| `reports/walk_forward_optimizer_stitched_oos_equity_summary.md` |
Final stitched OOS summary |
| `reports/walk_forward_optimizer_stitched_oos_equity.parquet` |
Daily stitched OOS equity curves |
| `notebooks/01_research_results_review.ipynb` |
Final notebook with visible mixed results |
| `reports/report_artifact_inventory.json` | Artifact inventory |

Current artifact inventory: 32 required
artifacts, 0 missing.

### Reproducibility Commands

```powershell
python -m pytest
python -m scripts.verify_report_reproducibility `
    --mode compare `
    --project-root . `
    --reference reports\recovery_reproducibility_reference.json `
    --output reports\recovery_reproducibility_check.json `
    --tolerance 1e-12
python -m scripts.check_documentation_integrity --project-root .
python -m scripts.check_report_artifacts `
    --project-root . `
    --output reports\report_artifact_inventory.json
```

### Limitations

- Historical backtests are not live trading evidence.
- ETF universe design can introduce instrument-selection and
  survivorship bias.
- yfinance data is suitable for research, not institutional execution.
- Transaction costs are simplified; taxes, borrow costs, market impact,
  and detailed slippage are not modeled.
- The optimizer can overfit train windows.
- Selection by train Sharpe may favor overly defensive portfolios.
- Residual cash is treated as zero-return cash in the implemented
  strategy.
- No macro regime model, nested validation, or multi-seed optimizer
  robustness study is included yet.

### Next Steps

- Add volatility-targeting and drawdown-constrained baselines.
- Compare candidate selection by Sharpe, Calmar, constrained CAGR,
  and turnover.
- Add multi-seed NSGA-II robustness analysis.
- Add parameter-stability plots across walk-forward splits.
- Add regime-aware features such as rates, inflation, VIX, and trend
  filters.
- Add stricter transaction-cost and slippage stress tests.
- Add Streamlit reporting dashboard for interactive inspection.

<!-- FINAL_README_POLISH_END -->
