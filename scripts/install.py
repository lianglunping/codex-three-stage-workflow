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
    "academic-figure-skill",
    "bio-publication-figure-director",
    "bio-reporting-figure-export",
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
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    targets.add_argument("--dsh-home", type=Path, help="install the DeepSeek Harness bundle here")
    parser.add_argument("--apply", action="store_true", help="perform writes")
    return parser.parse_args()


def source_manifest(deepseek: bool = False) -> List[Tuple[Path, Path]]:
    manifest: List[Tuple[Path, Path]] = []
    for skill in SKILLS:
        source_root = REPO_ROOT / "skills" / skill
        if deepseek and skill == "three-stage-complex-workflow":
            source_root = REPO_ROOT / "hosts" / "deepseek" / "skills" / skill
        if source_root.is_dir():
            for source in sorted(source_root.rglob("*")):
                if source.is_file() and "__pycache__" not in source.parts:
                    manifest.append(
                        (source, Path("skills") / skill / source.relative_to(source_root))
                    )
        else:
            manifest.append((source_root, Path("skills") / skill))
    for name in ("WORKFLOW.md", "RESOURCE_INDEX.md"):
        relative = Path("research-workflow") / name
        manifest.append((REPO_ROOT / relative, relative))
    if deepseek:
        source = REPO_ROOT / "hosts/deepseek/examples/research-routing.yml"
        manifest.append((source, Path("research-workflow/research-routing.yml")))
    else:
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
    deepseek = args.dsh_home is not None
    target_home = (args.dsh_home if deepseek else args.codex_home).expanduser().resolve()
    if target_home == Path(target_home.anchor) or target_home == Path.home().resolve():
        print("UNSAFE_CODEX_HOME", file=sys.stderr)
        return 2
    manifest = source_manifest(deepseek)
    missing = validate_sources(manifest)
    if missing:
        for path in missing:
            print(f"MISSING_SOURCE {path.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "DRY_RUN"
    print(f"{mode} target_home={target_home}")
    for _, relative in manifest:
        print(f"{mode} {relative}")
    examples = REPO_ROOT / "examples"
    if deepseek:
        examples = REPO_ROOT / "hosts" / "deepseek" / "examples"
        print(f"RESEARCH_ROUTING {target_home / 'research-workflow/research-routing.yml'}")
    else:
        print(f"MANUAL_MERGE {examples / 'config.toml'}")
    print(f"MANUAL_MERGE {examples / 'AGENTS.md'}")
    if not args.apply:
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_root = target_home / "backups" / "codex-three-stage-workflow" / timestamp
    existing = [
        (target_home / relative, backup_root / relative)
        for _, relative in manifest
        if (target_home / relative).exists()
    ]
    for target, backup in existing:
        if target.is_symlink():
            print(f"UNSAFE_TARGET_SYMLINK {target}", file=sys.stderr)
            return 3
        atomic_copy(target, backup)
    for source, relative in manifest:
        target = target_home / relative
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
