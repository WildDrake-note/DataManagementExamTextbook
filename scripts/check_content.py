#!/usr/bin/env python3
"""Repository-local checks for Markdown links and structure."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_FILES = sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").rglob("*.md"))
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
REQUIRED = {
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "docs/index.md",
    "docs/guide/syllabus-map.md",
    "docs/glossary.md",
}

errors: list[str] = []
for rel in sorted(REQUIRED):
    if not (ROOT / rel).exists():
        errors.append(f"missing required file: {rel}")

for path in MD_FILES:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# "):
        errors.append(f"missing H1 at first line: {path.relative_to(ROOT)}")
    for target in LINK_RE.findall(text):
        target = target.strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            errors.append(
                f"broken local link: {path.relative_to(ROOT)} -> {target}"
            )

if errors:
    print("CHECK FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(f"CHECK PASSED: {len(MD_FILES)} Markdown files")
