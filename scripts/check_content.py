#!/usr/bin/env python3
"""Repository-local checks for textbook structure and references."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_FILES = sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").rglob("*.md"))
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
TABLE_SEPARATOR_RE = re.compile(
    r"^\|\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", re.MULTILINE
)
FENCE_START_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
REQUIRED = {
    "README.md",
    "LICENSE",
    "NOTICE",
    "CONTRIBUTING.md",
    "references.yml",
    "docs/index.md",
    "docs/guide/syllabus-map.md",
    "docs/guide/coverage.md",
    "docs/guide/visual-review.md",
    "docs/exercises/subject-a.md",
    "docs/exercises/subject-b.md",
    "docs/glossary.md",
}


def analyze_markdown(text: str) -> tuple[str, list[str], bool]:
    """Return unfenced Markdown, complete text diagrams, and unclosed-fence state."""
    outside: list[str] = []
    text_diagrams: list[str] = []
    marker_char: str | None = None
    marker_length = 0
    info = ""
    block: list[str] = []

    for line in text.splitlines():
        if marker_char is None:
            match = FENCE_START_RE.match(line)
            if not match:
                outside.append(line)
                continue
            marker, rest = match.groups()
            if marker[0] == "`" and "`" in rest:
                outside.append(line)
                continue
            marker_char = marker[0]
            marker_length = len(marker)
            info = rest.strip().split(maxsplit=1)[0].lower() if rest.strip() else ""
            block = []
            continue

        closing = re.fullmatch(
            rf" {{0,3}}{re.escape(marker_char)}{{{marker_length},}}[ \t]*", line
        )
        if closing:
            if info == "text" and any(part.strip() for part in block):
                text_diagrams.append("\n".join(block))
            marker_char = None
            marker_length = 0
            info = ""
            block = []
        else:
            block.append(line)

    return "\n".join(outside), text_diagrams, marker_char is not None


errors: list[str] = []
for rel in sorted(REQUIRED):
    if not (ROOT / rel).exists():
        errors.append(f"missing required file: {rel}")

for path in MD_FILES:
    text = path.read_text(encoding="utf-8")
    outside_text, _, has_unclosed_fence = analyze_markdown(text)
    if not text.startswith("# "):
        errors.append(f"missing H1 at first line: {path.relative_to(ROOT)}")
    if has_unclosed_fence:
        errors.append(f"unbalanced fenced code block: {path.relative_to(ROOT)}")
    for target in LINK_RE.findall(outside_text):
        target = target.strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            errors.append(
                f"broken local link: {path.relative_to(ROOT)} -> {target}"
            )

chapter_files = sorted((ROOT / "docs/chapters").glob("*.md"))
if len(chapter_files) != 12:
    errors.append(f"docs/chapters must contain exactly 12 chapters: {len(chapter_files)}")
for path in chapter_files:
    text = path.read_text(encoding="utf-8")
    outside_text, diagram_blocks, _ = analyze_markdown(text)
    table_count = len(TABLE_SEPARATOR_RE.findall(outside_text))
    diagram_count = len(diagram_blocks)
    question_count_in_chapter = len(
        re.findall(r"^### 問\d+", outside_text, re.MULTILINE)
    )
    answer_count_in_chapter = len(
        re.findall(r"^\*\*解答(?:例)?(?:：|:|\s|\.)", outside_text, re.MULTILINE)
    )
    if table_count < 6:
        errors.append(f"chapter must contain at least 6 tables: {path.name}")
    if diagram_count < 5:
        errors.append(f"chapter must contain at least 5 non-empty text diagrams: {path.name}")
    if question_count_in_chapter < 4:
        errors.append(
            f"chapter must contain at least 4 confirmation questions: {path.name}"
        )
    if answer_count_in_chapter != question_count_in_chapter:
        errors.append(
            f"chapter answer count must match question count: {path.name} "
            f"({answer_count_in_chapter}/{question_count_in_chapter})"
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
subject_a_outside, _, _ = analyze_markdown(subject_a)
question_numbers = [
    int(value)
    for value in re.findall(r"^\*\*問(\d+)\*\*", subject_a_outside, re.MULTILINE)
]
question_count = len(question_numbers)
answer_numbers = [
    int(value)
    for value in re.findall(
        r"^\|\s*(\d+)\s*\|\s*[1-4]\s*\|", subject_a_outside, re.MULTILINE
    )
]
if question_count < 60:
    errors.append(f"subject-a must contain at least 60 questions: {question_count}")
if question_numbers != list(range(1, question_count + 1)):
    errors.append("subject-a question numbers must be unique and sequential")
if answer_numbers != question_numbers:
    errors.append("subject-a answer rows must match all question numbers in order")
for chapter in range(1, 13):
    match = re.search(
        rf"^### 第{chapter}章：.*?$(.*?)(?=^### 第\d+章：|^## 解答・解説)",
        subject_a_outside,
        re.MULTILINE | re.DOTALL,
    )
    chapter_questions = (
        len(re.findall(r"^\*\*問\d+\*\*", match.group(1), re.MULTILINE))
        if match
        else 0
    )
    if chapter_questions != 5:
        errors.append(
            f"subject-a chapter {chapter} must contain exactly 5 questions: "
            f"{chapter_questions}"
        )

subject_b = (ROOT / "docs/exercises/subject-b.md").read_text(encoding="utf-8")
subject_b_outside, _, _ = analyze_markdown(subject_b)
case_count = len(re.findall(r"^## ケース\d+：", subject_b_outside, re.MULTILINE))
case_question_count = len(re.findall(r"^### 問\d+$", subject_b_outside, re.MULTILINE))
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
