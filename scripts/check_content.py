#!/usr/bin/env python3
"""Repository-local checks for textbook structure and references."""
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
    "NOTICE",
    "CONTRIBUTING.md",
    "references.yml",
    "docs/index.md",
    "docs/guide/syllabus-map.md",
    "docs/guide/coverage.md",
    "docs/exercises/subject-a.md",
    "docs/exercises/subject-b.md",
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

registry = (ROOT / "references.yml").read_text(encoding="utf-8")
source_ids = re.findall(r"^  - id: (\S+)$", registry, re.MULTILINE)
source_urls = re.findall(r"^    url: (https://\S+)$", registry, re.MULTILINE)
if len(source_ids) < 10:
    errors.append("references.yml must contain at least 10 primary references")
if len(source_ids) != len(set(source_ids)):
    errors.append("duplicate source id in references.yml")
if len(source_urls) != len(set(source_urls)):
    errors.append("duplicate source URL in references.yml")
if len(source_ids) != len(source_urls):
    errors.append("every source in references.yml must have one HTTPS URL")
for digest in re.findall(r"^    sha256: (\S+)$", registry, re.MULTILINE):
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        errors.append(f"invalid SHA-256 in references.yml: {digest}")

subject_a = (ROOT / "docs/exercises/subject-a.md").read_text(encoding="utf-8")
question_count = len(re.findall(r"^\*\*問\d+\*\*", subject_a, re.MULTILINE))
if question_count < 24:
    errors.append(f"subject-a must contain at least 24 questions: {question_count}")

subject_b = (ROOT / "docs/exercises/subject-b.md").read_text(encoding="utf-8")
case_count = len(re.findall(r"^## ケース\d+：", subject_b, re.MULTILINE))
case_question_count = len(re.findall(r"^### 問\d+$", subject_b, re.MULTILINE))
if case_count < 8:
    errors.append(f"subject-b must contain at least 8 cases: {case_count}")
if case_question_count < 21:
    errors.append(
        f"subject-b must contain at least 21 case questions: {case_question_count}"
    )

coverage = (ROOT / "docs/guide/coverage.md").read_text(encoding="utf-8")
skill_rows = len(re.findall(r"^\| [1-4]-\d ", coverage, re.MULTILINE))
if skill_rows != 16:
    errors.append(f"coverage must list all 16 subject-B items: {skill_rows}")

if errors:
    print("CHECK FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(
    f"CHECK PASSED: {len(MD_FILES)} Markdown files, "
    f"{len(source_ids)} references, {question_count} subject-A questions, "
    f"{case_count} subject-B cases, {case_question_count} case questions, "
    f"{skill_rows} subject-B items"
)
