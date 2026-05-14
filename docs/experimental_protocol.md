# Experimental Protocol

This project is a quantitative finance research pipeline, not a trading signal marketing demo. The goal is to evaluate portfolio strategies under a reproducible and honest protocol.

## Core rule

We do not change the experiment to make a strategy look better after seeing results.

Bad results, weak baselines, optimizer failures, overfitting, and unstable parameters must remain visible in the final report.

## What is allowed

Protocol changes are allowed only when they fix a methodological issue and are made before final optimizer evaluation.

Allowed examples:

- Excluding incomplete final out-of-sample windows when annual OOS metrics are compared.
- Aligning strategies to the exact common date intersection before comparing metrics.
- Preventing implicit price forward-fill when calculating returns.
- Adding a missing baseline before optimizer evaluation.
- Adding tests that lock the corrected protocol.

## What is not allowed

The following are prohibited:

- Removing a baseline because it outperforms the proposed strategy.
- Changing metrics after seeing that the optimizer performs poorly.
- Reporting only the best split or best seed.
- Hiding train/test degradation.
- Calling a risk trade-off "outperformance" when CAGR or total return is lower.
- Silently changing transaction costs, rebalance frequency, lookback windows, or universe membership to improve results.
- Using future information in features, weights, or model selection.

## Required baselines

The final report must include at least:

- SPY buy-and-hold.
- Equal-weight ETF universe.
- 12-month momentum top-K strategy.
- Evolutionary optimized strategy.

If a baseline performs better than the optimizer, it remains in the report.

## Required metrics

The final report must include:

- Cumulative return.
- CAGR.
- Annualized volatility.
- Sharpe ratio.
- Sortino ratio.
- Max drawdown.
- Calmar ratio.
- Monthly win rate.
- Observation count.
- Transaction cost assumptions.
- Train/test degradation for optimized strategies.
- Walk-forward out-of-sample split summary.

## Current baseline protocol

Current full-period baseline sanity checks use:

- Exact common date intersection across all strategy return series.
- Adjusted close prices.
- No implicit forward-fill when calculating returns.
- 252-trading-day momentum lookback.
- Monthly rebalance using actual trading dates.
- Top-5 long-only equal-weight momentum allocation.
- Transaction costs are included for the momentum net baseline at 10 bps in the full-period baseline sanity report.

The full-period baseline report is a sanity check. It is not the final proof of optimizer quality.

## Walk-forward protocol

Final optimized strategy evaluation must use walk-forward testing:

- Train window: 6 years.
- Test window: 1 complete calendar year.
- Step: 1 year.
- Incomplete final test windows are excluded from annual OOS evaluation.
- Optimizer may only use train-window information.
- Test-window metrics are calculated once using fixed selected parameters.
- Failed or weak test splits are not removed.

## Interpretation rules

Use precise language:

- If CAGR is lower but drawdown improves, report this as a risk-return trade-off.
- If Sharpe improves but total return decreases, report this explicitly.
- If the optimizer beats equal-weight but loses to SPY, report both facts.
- If performance is unstable across splits, report instability.
- If transaction costs erase gains, report that.

## Reproducibility requirements

Every major result should be reproducible through scripts in this repository.

Reports must be generated from saved artifacts, not manually edited numbers.

Quality gates before reporting:

    python -m black src scripts tests
    python -m ruff check src scripts tests
    python -m pytest

## Current known limitations

- Historical ETF data does not guarantee future performance.
- yfinance data is research-grade, not institutional-grade.
- ETF universe can introduce survivorship and selection bias.
- Full-period baseline report currently excludes transaction costs.
- Slippage and market impact are not yet modeled.
- Momentum baseline has fixed parameters and is not tuned.
- Evolutionary optimizer is not yet implemented.

<!-- CURRENT_BASELINE_EVIDENCE_START -->
## Current Baseline Evidence

The baseline stage currently has three generated evidence layers:

1. Full-period baseline sanity check:
   - `reports/baseline_metrics.json`
   - `reports/baseline_metrics_summary.md`

2. Walk-forward split-level OOS baseline evaluation:
   - `reports/walk_forward_baseline_metrics.json`
   - `reports/walk_forward_baseline_summary.md`

3. Stitched continuous OOS baseline equity:
   - `reports/walk_forward_baseline_oos_equity.parquet`
   - `reports/walk_forward_baseline_oos_equity_summary.json`
   - `reports/walk_forward_baseline_oos_equity_summary.md`

Current baseline strategies:

- `buy_hold_SPY`
- `equal_weight`
- `momentum_top_5_252d_gross`
- `momentum_top_5_252d_net_10bps`

Current transaction cost convention:

- Momentum net returns use `net_return = gross_return - turnover * bps / 10000`.
- Transaction cost assumption: 10 bps.
- Turnover convention: `sum_abs_weight_change`.
- Gross momentum is retained only to show transaction-cost impact.
- Net momentum should be preferred when discussing implementability.

Current interpretation:

- SPY remains the benchmark for return and final equity.
- Momentum gross/net may improve Sharpe or drawdown, but lower CAGR must be described as a risk-return trade-off, not overall outperformance.
- Mean split CAGR and stitched OOS CAGR are different quantities and must not be mixed.
<!-- CURRENT_BASELINE_EVIDENCE_END -->
