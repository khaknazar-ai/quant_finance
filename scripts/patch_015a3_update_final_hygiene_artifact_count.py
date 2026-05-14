from __future__ import annotations

from pathlib import Path


def patch_final_hygiene_checker(project_root: Path) -> None:
    """Update final hygiene checker to validate the 34-artifact final inventory."""
    path = project_root / "scripts" / "check_final_project_hygiene.py"
    text = path.read_text(encoding="utf-8")

    text = text.replace(
        "passed = artifact_count == 32 and missing_count == 0 and notebook_present",
        (
            "final_hygiene_present = any(\n"
            '        item.get("path") == "reports/final_project_hygiene_check.json"\n'
            "        for item in artifacts\n"
            "    )\n"
            "    final_release_checklist_present = any(\n"
            '        item.get("path") == "docs/final_release_checklist.md"\n'
            "        for item in artifacts\n"
            "    )\n\n"
            "    passed = (\n"
            "        artifact_count == 34\n"
            "        and missing_count == 0\n"
            "        and notebook_present\n"
            "        and final_hygiene_present\n"
            "        and final_release_checklist_present\n"
            "    )"
        ),
    )

    text = text.replace(
        'f"notebook_present={notebook_present}"',
        (
            'f"notebook_present={notebook_present}; "\n'
            '        f"final_hygiene_present={final_hygiene_present}; "\n'
            '        f"final_release_checklist_present={final_release_checklist_present}"'
        ),
    )

    if "artifact_count == 32" in text:
        raise ValueError("Old artifact_count == 32 expectation is still present.")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_final_hygiene_checker(Path("."))


if __name__ == "__main__":
    main()
