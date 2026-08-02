#!/usr/bin/env python3
"""Audit a release tree for public-boundary and manifest violations."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    line: int = 0


def patterns() -> Sequence[tuple[str, re.Pattern[str]]]:
    slash = "/"
    codex = "." + "codex"
    return (
        (
            "PERSONAL_ABSOLUTE_PATH",
            re.compile(re.escape(slash + "Users" + slash) + r"[^/<\s]+/"),
        ),
        (
            "PERSONAL_ABSOLUTE_PATH",
            re.compile(re.escape(slash + "home" + slash) + r"[^/<\s]+/"),
        ),
        (
            "CODEX_SESSION_PATH",
            re.compile(re.escape(codex + slash + "sessions" + slash)),
        ),
        (
            "CODEX_BACKUP_PATH",
            re.compile(re.escape(codex + slash + "backups" + slash)),
        ),
        (
            "SESSION_IDENTIFIER",
            re.compile(r"\b019[a-f0-9]{5}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b"),
        ),
        ("POSSIBLE_SECRET", re.compile(r"ghp" + r"_[A-Za-z0-9]{36,}")),
        ("POSSIBLE_SECRET", re.compile(r"github" + r"_pat_[A-Za-z0-9_]{20,}")),
        ("POSSIBLE_SECRET", re.compile(r"AKIA[A-Z0-9]{16}")),
        (
            "POSSIBLE_SECRET",
            re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE" + r" KEY"),
        ),
    )


def release_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.name != "MANIFEST.sha256":
            yield path


def scan_tree(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for path in sorted(root.rglob("*")):
        relative_parts = path.relative_to(root).parts
        if any(part in IGNORED_PARTS for part in relative_parts):
            continue
        relative = str(path.relative_to(root))
        if path.is_symlink():
            if not path.exists():
                findings.append(Finding("BROKEN_SYMLINK", relative))
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for code, pattern in patterns():
                if pattern.search(line):
                    findings.append(Finding(code, relative, line_number))
    return findings


def verify_manifest(root: Path) -> List[Finding]:
    path = root / "MANIFEST.sha256"
    if not path.is_file():
        return [Finding("MISSING_MANIFEST", "MANIFEST.sha256")] if (root / ".git").exists() else []
    expected: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [Finding("UNREADABLE_MANIFEST", "MANIFEST.sha256")]
    for number, line in enumerate(lines, start=1):
        parts = line.split("  ", 1)
        if len(parts) != 2 or not re.fullmatch(r"[a-f0-9]{64}", parts[0]):
            return [Finding("INVALID_MANIFEST", "MANIFEST.sha256", number)]
        if parts[1] in expected:
            return [Finding("DUPLICATE_MANIFEST_PATH", "MANIFEST.sha256", number)]
        expected[parts[1]] = parts[0]
    actual = {
        str(item.relative_to(root)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in release_files(root)
    }
    findings: List[Finding] = []
    for relative in sorted(set(expected) - set(actual)):
        findings.append(Finding("MANIFEST_MISSING_FILE", relative))
    for relative in sorted(set(actual) - set(expected)):
        findings.append(Finding("MANIFEST_UNLISTED_FILE", relative))
    for relative in sorted(set(actual) & set(expected)):
        if actual[relative] != expected[relative]:
            findings.append(Finding("MANIFEST_HASH_MISMATCH", relative))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    findings: List[Finding] = []
    if not (root / "LICENSE").is_file():
        findings.append(Finding("MISSING_LICENSE", "LICENSE"))
    if not (root / "VERSION").is_file():
        findings.append(Finding("MISSING_VERSION", "VERSION"))
    findings.extend(scan_tree(root))
    findings.extend(verify_manifest(root))
    if findings:
        for finding in sorted(findings, key=lambda item: (item.code, item.path, item.line)):
            suffix = f":{finding.line}" if finding.line else ""
            print(f"{finding.code} {finding.path}{suffix}", file=sys.stderr)
        print(f"FAIL PUBLIC_RELEASE_AUDIT findings={len(findings)}", file=sys.stderr)
        return 1
    print(f"PASS PUBLIC_RELEASE_AUDIT files={sum(1 for _ in release_files(root))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
