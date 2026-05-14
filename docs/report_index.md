# Report Index

This file maps the main reproducible artifacts for the project.

Generated metric values in `reports/*.json` and their generated Markdown summaries are the source of truth. Do not manually rewrite numbers in README or portfolio text without regenerating the source reports.

## Protocol

- `docs/experimental_protocol.md`  -  experimental integrity rules, allowed protocol changes, prohibited cherry-picking, required baselines, required metrics, and interpretation rules.

## Data and feature quality

- `reports/data_quality_prices.json`  -  validated raw OHLCV data quality report.
- `reports/feature_quality_report.json`  -  technical feature generation quality report.
- `reports/walk_forward_splits.json`  -  complete walk-forward split definition.

## Full-period baseline sanity check

- `reports/baseline_metrics.json`  -  machine-readable full-period baseline metrics.
- `reports/baseline_metrics_summary.md`  -  generated Markdown summary of full-period baseline metrics.
- `reports/evaluate_baselines_run.log`  -  run log for full-period baseline evaluation.

This report is a sanity check, not final optimizer evidence.

## Walk-forward split-level OOS baselines

- `reports/walk_forward_baseline_metrics.json`  -  machine-readable split-level OOS baseline metrics.
- `reports/walk_forward_baseline_summary.md`  -  generated Markdown summary of split-level OOS baseline metrics.
- `reports/evaluate_walk_forward_baselines_run.log`  -  run log for walk-forward baseline evaluation.

This report compares strategies across complete annual OOS test windows.

## Stitched OOS baseline equity

- `reports/walk_forward_baseline_oos_equity.parquet`  -  stitched OOS equity curves for baseline strategies.
- `reports/walk_forward_baseline_oos_equity_summary.json`  -  machine-readable stitched OOS equity summary.
- `reports/walk_forward_baseline_oos_equity_summary.md`  -  generated Markdown summary of stitched OOS equity metrics.
- `reports/build_walk_forward_oos_equity_run.log`  -  run log for stitched OOS equity generation.

This report compounds non-overlapping OOS test-window returns into one continuous OOS equity curve.

## Artifact inventory

- `reports/report_artifact_inventory.json`  -  generated inventory of required report artifacts.

Generate or validate it with:

    python -m scripts.check_report_artifacts --output reports/report_artifact_inventory.json

## Interpretation rules

- Do not compare full-period, split-level, and stitched-equity metrics as if they were the same quantity.
- Mean split CAGR is the arithmetic average of annual OOS split CAGRs.
- Stitched OOS CAGR is calculated from one continuous compounded OOS return series.
- A strategy with lower CAGR but higher Sharpe or lower drawdown is a risk-return trade-off, not overall outperformance.
- Transaction-cost-aware results should be preferred over gross-only results when discussing implementability.

## Factor Rotation Smoke Evaluation

- `reports/factor_rotation_grid_smoke.json` — deterministic train-window factor-rotation parameter grid smoke report.
- `reports/factor_rotation_grid_smoke_summary.md` — Markdown summary of candidate metrics and leaders.
- `reports/factor_rotation_grid_smoke_run.log` — command output for the smoke evaluation run.

Interpretation rule: this is train-only smoke evidence. It verifies that the objective function works on real ETF data, but it is not optimizer search and not out-of-sample performance evidence.

## NSGA-II Train-Only Smoke Optimization

- `reports/nsga2_train_smoke.json` — train-only NSGA-II optimizer smoke JSON report.
- `reports/nsga2_train_smoke_summary.md` — Markdown summary with train leaders, top evaluations, and Pareto objectives.
- `reports/nsga2_train_smoke_run.log` — command output for the NSGA-II smoke run.

Interpretation rule: this validates optimizer plumbing on one train window. It is not walk-forward selection and not out-of-sample performance evidence.

## One-Split Optimizer Train-to-Test Selection

- `reports/one_split_optimizer_selection.json` — one-split train-to-test optimizer selection JSON report.
- `reports/one_split_optimizer_selection_summary.md` — Markdown summary with selected candidate, OOS test metrics, degradation, and baseline comparison.
- `reports/one_split_optimizer_selection_run.log` — command output for the one-split optimizer selection run.

Interpretation rule: this is one OOS split only. It is useful for checking train-to-test degradation, but it is not final walk-forward evidence and not an overall outperformance claim.

## Walk-Forward Optimizer Selection

- `reports/walk_forward_optimizer_selection.json` — full walk-forward optimizer-selection JSON report across all OOS splits.
- `reports/walk_forward_optimizer_selection_summary.md` — Markdown summary with aggregate OOS metrics, split winner counts, and train-to-test degradation.
- `reports/walk_forward_optimizer_selection_run.log` — command output for the full walk-forward optimizer-selection run.

Interpretation rule: this is the main walk-forward OOS optimizer evidence. The current result should be framed as a risk-control trade-off: optimizer selected net improved mean max drawdown versus SPY, but underperformed SPY on mean CAGR and mean Sharpe.

## Stitched Optimizer OOS Equity

- `reports/walk_forward_optimizer_stitched_oos_equity.parquet` — daily stitched OOS equity curves for optimizer and baselines.
- `reports/walk_forward_optimizer_stitched_oos_equity_summary.json` — machine-readable stitched OOS equity summary.
- `reports/walk_forward_optimizer_stitched_oos_equity_summary.md` — Markdown report with stitched CAGR, Sharpe, MaxDD, Calmar, final equity, and optimizer-vs-SPY deltas.
- `reports/build_walk_forward_optimizer_stitched_oos_equity_run.log` — command output for stitched optimizer OOS equity generation.

Interpretation rule: stitched OOS confirms a risk-control trade-off. SPY leads final equity and CAGR, while optimizer selected net has less severe max drawdown.

## Final Research Notebook

- `notebooks/01_research_results_review.ipynb` — notebook review of the final evidence chain, including baseline results, full walk-forward optimizer selection, stitched OOS equity curves, drawdown curves, and explicit mixed-result interpretation.

Interpretation rule: the notebook keeps inconvenient results visible. It states that the optimizer did not outperform SPY on final equity, stitched CAGR, or stitched Sharpe, while improving max drawdown.

## Final Quality Gate

- `reports/final_project_hygiene_check.json` — machine-readable final repository hygiene report.
- `docs/final_release_checklist.md` — final GitHub-readiness checklist with release status, final evidence summary, and required commands.

Interpretation rule: these files do not change experiment results; they verify that the repository presents the mixed result clearly and without misleading claims.

