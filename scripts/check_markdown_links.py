"""Check relative links in tracked Markdown files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


def tracked_markdown(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", "*.md"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [root / name for name in result.stdout.splitlines()]


def markdown_links(content: str) -> list[str]:
    content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    content = re.sub(r"`[^`\n]*`", "", content)
    return re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    problems: list[str] = []
    checked = 0

    for document in tracked_markdown(root):
        if not document.is_file():
            continue
        checked += 1
        content = document.read_text(encoding="utf-8")
        for link in markdown_links(content):
            destination = link.split()[0]
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            if not target.exists():
                relative_document = document.relative_to(root)
                problems.append(f"{relative_document}: {destination}")

    if problems:
        print(
            f"Found {len(problems)} broken relative Markdown links "
            f"in {checked} files:"
        )
        print("\n".join(problems))
        return 1

    print(f"Checked relative Markdown links in {checked} files: all targets exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
