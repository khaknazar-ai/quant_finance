# Final Release Checklist

This file is the final repository-level readiness checklist for the Quant
Finance Pipeline project.

## Release Status

- [x] README contains final research summary.
- [x] Evaluation protocol is documented.
- [x] Final research notebook is registered as an artifact.
- [x] Report artifact inventory is complete.
- [x] Reproducibility comparison passes.
- [x] Final hygiene check passes.
- [x] Mixed/negative result interpretation is visible.
- [x] No resume-specific section is included in the project docs.

## Final Evidence Summary

The optimizer did not outperform SPY on stitched final equity, stitched
CAGR, or stitched Sharpe. It improved stitched max drawdown. The correct
framing is a risk-control trade-off, not a broad performance advantage.

| Metric | SPY | Optimizer selected net |
|---|---:|---:|
| Final equity | 2.920 | 1.633 |
| CAGR | 13.87% | 6.13% |
| Sharpe | 0.785 | 0.642 |
| Max drawdown | -33.72% | -18.52% |

## Required Final Checks

```powershell
python -m pytest
python -m scripts.check_final_project_hygiene `
    --project-root . `
    --output reports\final_project_hygiene_check.json
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

## Current Final Check Results

| Check | Result |
|---|---:|
| Artifact count | 34 |
| Missing artifacts | 0 |
| Final hygiene passed | True |
| Reproducibility passed | True |
| Reproducibility difference count | 0 |

## Main Artifacts to Review

- `README.md`
- `docs/experimental_protocol.md`
- `docs/report_index.md`
- `docs/final_release_checklist.md`
- `notebooks/01_research_results_review.ipynb`
- `reports/walk_forward_optimizer_selection_summary.md`
- `reports/walk_forward_optimizer_stitched_oos_equity_summary.md`
- `reports/walk_forward_optimizer_stitched_oos_equity.parquet`
- `reports/final_project_hygiene_check.json`
- `reports/report_artifact_inventory.json`

## Final Interpretation

This project should be presented as a reproducible research pipeline for
walk-forward ETF allocation and optimizer evaluation. The final result is
valuable because it is transparent: the optimizer reduced drawdown but
paid for that defense with materially lower return than SPY.
