from __future__ import annotations

from pathlib import Path

DOCUMENTATION_PATHS = [
    Path("README.md"),
    Path("docs/report_index.md"),
    Path("docs/experimental_protocol.md"),
]

REPLACEMENTS = {
    "\u2014": " - ",
    "\u2013": "-",
    "\u0432\u0402\u201d": " - ",
    "\u0432\u0402\u201c": "-",
}


def normalize_documentation_text(project_root: Path = Path(".")) -> None:
    """Normalize terminal-hostile Unicode punctuation in documentation files."""
    for relative_path in DOCUMENTATION_PATHS:
        path = project_root / relative_path
        text = path.read_text(encoding="utf-8")

        for old, new in REPLACEMENTS.items():
            text = text.replace(old, new)

        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    normalize_documentation_text()
