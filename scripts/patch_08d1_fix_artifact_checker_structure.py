from __future__ import annotations

import re
from pathlib import Path


def fix_artifact_checker(project_root: Path) -> None:
    """Repair smoke artifact registration as proper RequiredArtifact objects."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    pattern = re.compile(
        r"RequiredArtifact\(\s*"
        r'path="reports/build_walk_forward_oos_equity_run\.log",\s*'
        r'"reports/factor_rotation_grid_smoke\.json",\s*'
        r'"reports/factor_rotation_grid_smoke_summary\.md",\s*'
        r'"reports/factor_rotation_grid_smoke_run\.log",\s*'
        r'category="stitched_oos_equity",\s*'
        r'description="Run log for stitched OOS equity generation\.",\s*'
        r"\),",
        flags=re.MULTILINE,
    )

    replacement = """RequiredArtifact(
        path="reports/build_walk_forward_oos_equity_run.log",
        category="stitched_oos_equity",
        description="Run log for stitched OOS equity generation.",
    ),
    RequiredArtifact(
        path="reports/factor_rotation_grid_smoke.json",
        category="factor_rotation_smoke",
        description="Train-only deterministic factor-rotation grid smoke JSON report.",
    ),
    RequiredArtifact(
        path="reports/factor_rotation_grid_smoke_summary.md",
        category="factor_rotation_smoke",
        description="Markdown summary for factor-rotation grid smoke evaluation.",
    ),
    RequiredArtifact(
        path="reports/factor_rotation_grid_smoke_run.log",
        category="factor_rotation_smoke",
        description="Run log for factor-rotation grid smoke evaluation.",
    ),"""

    new_text, replacement_count = pattern.subn(replacement, text)

    if replacement_count == 0:
        required_fragments = [
            'path="reports/factor_rotation_grid_smoke.json"',
            'path="reports/factor_rotation_grid_smoke_summary.md"',
            'path="reports/factor_rotation_grid_smoke_run.log"',
        ]

        if all(fragment in text for fragment in required_fragments):
            return

        raise ValueError("Broken artifact checker block was not found.")

    path.write_text(new_text, encoding="utf-8")


def fix_patch_script_line_lengths(project_root: Path) -> None:
    """Rewrite the 0.8D patch helper with Ruff-clean strings."""
    path = project_root / "scripts" / "patch_08d_register_smoke_artifacts.py"
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")

    long_start = '    section = """\\n## Factor Rotation Smoke Evaluation'
    if long_start not in text:
        return

    section_start = text.find(long_start)
    section_end = text.find('"""', section_start + len('    section = """'))

    if section_end == -1:
        raise ValueError("Could not find end of long report-index section.")

    section_end += 3

    replacement = """    section = (
        "\\n## Factor Rotation Smoke Evaluation\\n\\n"
        "- `reports/factor_rotation_grid_smoke.json` — deterministic "
        "train-window factor-rotation parameter grid smoke report.\\n"
        "- `reports/factor_rotation_grid_smoke_summary.md` — Markdown "
        "summary of candidate metrics and leaders.\\n"
        "- `reports/factor_rotation_grid_smoke_run.log` — command output "
        "for the smoke evaluation run.\\n\\n"
        "Interpretation rule: this is train-only smoke evidence. It verifies "
        "that the objective function works on real ETF data, but it is not "
        "optimizer search and not out-of-sample performance evidence.\\n"
    )"""

    text = text[:section_start] + replacement + text[section_end:]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    fix_artifact_checker(project_root)
    fix_patch_script_line_lengths(project_root)


if __name__ == "__main__":
    main()
