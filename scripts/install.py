#!/usr/bin/env python3
"""Install the public workflow suite into an isolated Codex home."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "three-stage-complex-workflow",
    "staged-agent-run-protocol",
    "dispatching-parallel-agents",
    "project-audit",
)
RUNTIME_FILES = (
    ("runtime/policies/three-stage-runtime-v1.json", "policies/three-stage-runtime-v1.json"),
    ("runtime/agents/three_stage_analyzer.toml", "agents/three_stage_analyzer.toml"),
    ("runtime/agents/three_stage_refiner.toml", "agents/three_stage_refiner.toml"),
    ("runtime/agents/revision_auditor.toml", "agents/revision_auditor.toml"),
    ("runtime/agents/deterministic_validator.toml", "agents/deterministic_validator.toml"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--apply", action="store_true", help="perform writes")
    return parser.parse_args()


def source_manifest() -> List[Tuple[Path, Path]]:
    manifest: List[Tuple[Path, Path]] = []
    for skill in SKILLS:
        source_root = REPO_ROOT / "skills" / skill
        if source_root.is_dir():
            for source in sorted(source_root.rglob("*")):
                if source.is_file() and "__pycache__" not in source.parts:
                    manifest.append(
                        (source, Path("skills") / skill / source.relative_to(source_root))
                    )
        else:
            manifest.append((source_root, Path("skills") / skill))
    manifest.extend((REPO_ROOT / source, Path(target)) for source, target in RUNTIME_FILES)
    return manifest


def validate_sources(manifest: Iterable[Tuple[Path, Path]]) -> List[Path]:
    return [source for source, _ in manifest if not source.is_file()]


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    args = parse_args()
    codex_home = args.codex_home.expanduser().resolve()
    if codex_home == Path(codex_home.anchor) or codex_home == Path.home().resolve():
        print("UNSAFE_CODEX_HOME", file=sys.stderr)
        return 2
    manifest = source_manifest()
    missing = validate_sources(manifest)
    if missing:
        for path in missing:
            print(f"MISSING_SOURCE {path.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "DRY_RUN"
    print(f"{mode} codex_home={codex_home}")
    for _, relative in manifest:
        print(f"{mode} {relative}")
    print(f"MANUAL_MERGE {REPO_ROOT / 'examples' / 'config.toml'}")
    print(f"MANUAL_MERGE {REPO_ROOT / 'examples' / 'AGENTS.md'}")
    if not args.apply:
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_root = codex_home / "backups" / "codex-three-stage-workflow" / timestamp
    existing = [
        (codex_home / relative, backup_root / relative)
        for _, relative in manifest
        if (codex_home / relative).exists()
    ]
    for target, backup in existing:
        if target.is_symlink():
            print(f"UNSAFE_TARGET_SYMLINK {target}", file=sys.stderr)
            return 3
        atomic_copy(target, backup)
    for source, relative in manifest:
        target = codex_home / relative
        if target.is_symlink():
            print(f"UNSAFE_TARGET_SYMLINK {target}", file=sys.stderr)
            return 3
        atomic_copy(source, target)
    print(f"INSTALLED {len(manifest)} files")
    if existing:
        print(f"BACKUP {backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
