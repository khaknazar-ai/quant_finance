from scripts.check_documentation_integrity import (
    check_no_mojibake,
    check_no_stale_cost_claims,
    check_protocol_current_baseline_section,
    check_report_index_links,
    run_checks,
)


def write_minimal_docs(project_root) -> None:
    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True)

    (project_root / "README.md").write_text(
        "reports/baseline_metrics_summary.md\n"
        "reports/walk_forward_baseline_summary.md\n"
        "reports/walk_forward_baseline_oos_equity_summary.md\n",
        encoding="utf-8",
    )

    (docs_dir / "report_index.md").write_text(
        "reports/baseline_metrics_summary.md\n"
        "reports/walk_forward_baseline_summary.md\n"
        "reports/walk_forward_baseline_oos_equity_summary.md\n"
        "reports/report_artifact_inventory.json\n",
        encoding="utf-8",
    )

    (docs_dir / "experimental_protocol.md").write_text(
        "## Current Baseline Evidence\n"
        "momentum_top_5_252d_net_10bps\n"
        "Transaction cost assumption: 10 bps\n"
        "net_return = gross_return - turnover * bps / 10000\n"
        "risk-return trade-off\n"
        "Mean split CAGR and stitched OOS CAGR are different quantities\n",
        encoding="utf-8",
    )


def test_check_no_mojibake_passes_for_clean_docs(tmp_path) -> None:
    write_minimal_docs(tmp_path)

    result = check_no_mojibake(
        project_root=tmp_path,
        relative_paths=["README.md", "docs/report_index.md"],
    )

    assert result.passed is True


def test_check_no_mojibake_fails_for_bad_fragment(tmp_path) -> None:
    write_minimal_docs(tmp_path)
    (tmp_path / "README.md").write_text("bad \u0432\u0402\u201d text", encoding="utf-8")

    result = check_no_mojibake(
        project_root=tmp_path,
        relative_paths=["README.md"],
    )

    assert result.passed is False
    assert "README.md" in result.message


def test_check_protocol_current_baseline_section(tmp_path) -> None:
    write_minimal_docs(tmp_path)

    result = check_protocol_current_baseline_section(project_root=tmp_path)

    assert result.passed is True


def test_check_no_stale_cost_claims(tmp_path) -> None:
    write_minimal_docs(tmp_path)

    result = check_no_stale_cost_claims(project_root=tmp_path)

    assert result.passed is True

    (tmp_path / "README.md").write_text("no costs yet", encoding="utf-8")

    result = check_no_stale_cost_claims(project_root=tmp_path)

    assert result.passed is False


def test_check_report_index_links(tmp_path) -> None:
    write_minimal_docs(tmp_path)

    result = check_report_index_links(project_root=tmp_path)

    assert result.passed is True


def test_run_checks_returns_all_checks(tmp_path) -> None:
    write_minimal_docs(tmp_path)

    checks = run_checks(project_root=tmp_path)

    assert len(checks) == 4
    assert all(check.passed for check in checks)
