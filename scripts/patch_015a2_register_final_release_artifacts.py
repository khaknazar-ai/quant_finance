from __future__ import annotations

from pathlib import Path

FINAL_HYGIENE_REPORT = "reports/final_project_hygiene_check.json"
FINAL_RELEASE_CHECKLIST = "docs/final_release_checklist.md"


def register_final_artifacts(project_root: Path) -> None:
    """Register final hygiene report and release checklist."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    if f'path="{FINAL_HYGIENE_REPORT}"' in text:
        return

    anchor = (
        "    RequiredArtifact(\n"
        '        path="notebooks/01_research_results_review.ipynb",\n'
        '        category="final_research_notebook",\n'
        '        description="Final research notebook with visible mixed OOS results.",\n'
        "    ),"
    )

    if anchor not in text:
        raise ValueError("Could not find final notebook artifact anchor.")

    insertion = (
        anchor
        + "\n"
        + "    RequiredArtifact(\n"
        + f'        path="{FINAL_HYGIENE_REPORT}",\n'
        + '        category="final_quality_gate",\n'
        + '        description="Final repository hygiene check report.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + f'        path="{FINAL_RELEASE_CHECKLIST}",\n'
        + '        category="final_quality_gate",\n'
        + '        description="Final release checklist for GitHub readiness.",\n'
        + "    ),"
    )

    path.write_text(text.replace(anchor, insertion), encoding="utf-8")


def update_artifact_count_tests(project_root: Path) -> None:
    """Update expected artifact count from 32 to 34."""
    path = project_root / "tests" / "test_check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "artifact_count'] == 32": "artifact_count'] == 34",
        'artifact_count"] == 32': 'artifact_count"] == 34',
        "Required artifact count: 32": "Required artifact count: 34",
        "artifact_count: 32": "artifact_count: 34",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def update_report_index(project_root: Path) -> None:
    """Document final release artifacts in report index."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    if FINAL_RELEASE_CHECKLIST in text:
        return

    section = (
        "\n## Final Quality Gate\n\n"
        f"- `{FINAL_HYGIENE_REPORT}` — machine-readable final repository "
        "hygiene report.\n"
        f"- `{FINAL_RELEASE_CHECKLIST}` — final GitHub-readiness checklist "
        "with release status, final evidence summary, and required commands.\n\n"
        "Interpretation rule: these files do not change experiment results; "
        "they verify that the repository presents the mixed result clearly and "
        "without misleading claims.\n"
    )

    path.write_text(text.rstrip() + "\n" + section + "\n", encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    register_final_artifacts(project_root)
    update_artifact_count_tests(project_root)
    update_report_index(project_root)


if __name__ == "__main__":
    main()
