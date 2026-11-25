"""Every relative link in the repo's Markdown points to a file or folder that exists.

`docs/archive/` is skipped: its documents are kept as they were written, links included.
Links inside fenced code blocks, web links and in-page anchors are not checked.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SKIPPED_DIRS = {"node_modules", "__pycache__", "SpaceVault"}
ARCHIVE = REPO / "docs" / "archive"
FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")


def markdown_files() -> list[Path]:
    """The Markdown files to check: hidden folders (.venv, .git, ...) and the archive left out."""
    files = []
    for path in sorted(REPO.rglob("*.md")):
        parts = path.relative_to(REPO).parts
        if any(p.startswith(".") or p in SKIPPED_DIRS for p in parts[:-1]):
            continue
        if path.is_relative_to(ARCHIVE):
            continue
        files.append(path)
    return files


def broken_links(path: Path) -> list[str]:
    """Relative link targets in `path` that don't exist on disk."""
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    broken = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
            continue  # https:, mailto:, ... or an anchor in the same page
        file_part = target.split("#", 1)[0]
        if not (path.parent / file_part).exists():
            broken.append(target)
    return broken


@pytest.mark.parametrize("path", markdown_files(), ids=lambda p: p.relative_to(REPO).as_posix())
def test_relative_links_point_to_existing_files(path):
    assert broken_links(path) == []


def test_markdown_files_finds_the_root_readme_and_skips_the_archive():
    files = markdown_files()
    assert REPO / "README.md" in files
    assert not any(f.is_relative_to(ARCHIVE) for f in files)
