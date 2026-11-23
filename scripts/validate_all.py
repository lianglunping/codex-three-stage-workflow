#!/usr/bin/env python3
"""Run the dependency-free public release validation suite."""

from __future__ import annotations

import subprocess
import sys
import os
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str]) -> bool:
    print(f"== {label} ==", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        print(f"FAIL {label} exit={result.returncode}", file=sys.stderr)
        return False
    print(f"PASS {label}")
    return True


def main() -> int:
    python = sys.executable
    commands = (
        (
            "unittest",
            [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        ),
    )
    # Exercise the delivered installer and bundle in an isolated home. Never read
    # personal AGENTS, policies, credentials or task records during release QA.
    with tempfile.TemporaryDirectory(prefix="three-stage-validation-") as temporary:
        home = Path(temporary) / "codex-home"
        os.environ["CODEX_HOME"] = str(home)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        if not run("isolated-install", [python, "-B", "scripts/install.py",
                                      "--codex-home", str(home), "--apply"]):
            return 1
        shutil.copy2(ROOT / "examples/AGENTS.md", home / "AGENTS.md")
        results = [run(label, command) for label, command in commands]
        results.append(run("installed-bundle", [python, "-B",
            str(home / "skills/three-stage-complex-workflow/scripts/validate_bundle.py"),
            "--codex-home", str(home), "--agents-skills-root", str(home / "skills")]))
        dsh = Path(temporary) / "dsh-home"
        if not run("isolated-deepseek-install", [python, "-B", "scripts/install.py",
                                                 "--dsh-home", str(dsh), "--apply"]):
            return 1
        shutil.copy2(ROOT / "hosts/deepseek/examples/AGENTS.md", dsh / "AGENTS.md")
        results.append(run("installed-deepseek-bundle", [python, "-B",
            str(dsh / "skills/three-stage-complex-workflow/scripts/validate_bundle.py"),
            "--dsh-home", str(dsh), "--skills-root", str(dsh / "skills")]))
        return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
