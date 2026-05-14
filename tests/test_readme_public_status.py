from pathlib import Path

README_PATH = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_public_status_is_complete_not_scaffold() -> None:
    text = README_PATH.read_text(encoding="utf-8")

    forbidden_fragments = [
        "## Current Status",
        "## Planned Baselines",
        "## Planned Metrics",
        "pytest: 7 passed",
        "Implement yfinance data ingestion.",
        "Save raw OHLCV data as parquet.",
        "Validate raw price data.",
        "Generate leakage-safe features.",
        "Implement baseline strategies.",
        "Add evolutionary walk-forward optimization.",
        "Build reporting and dashboard.",
        "Current artifact inventory: 32 required artifacts",
        "32 required artifacts, 0 missing",
    ]

    stale_fragments = [fragment for fragment in forbidden_fragments if fragment in text]
    assert not stale_fragments, stale_fragments

    required_fragments = [
        "## Final Status",
        "Project status: complete and GitHub-ready.",
        "pytest: 191 passed",
        "artifact inventory: 34 required artifacts, 0 missing",
        "Current artifact inventory: 34 required artifacts, 0 missing",
        "The optimizer did not outperform SPY",
        "risk-control trade-off",
        "### Final Stitched OOS Results",
    ]

    missing_fragments = [fragment for fragment in required_fragments if fragment not in text]
    assert not missing_fragments, missing_fragments
