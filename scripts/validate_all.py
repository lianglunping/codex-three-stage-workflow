#!/usr/bin/env python3
"""Run the dependency-free public release validation suite."""

from __future__ import annotations

import subprocess
import sys
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
        (
            "workflow-contract",
            [
                python,
                "-B",
                "skills/three-stage-complex-workflow/scripts/validate_workflow_contract.py",
                "--skill-root",
                "skills/three-stage-complex-workflow",
                "--agents",
                "examples/AGENTS.md",
                "--cases",
                "skills/three-stage-complex-workflow/references/regression_cases.tsv",
                "--policy",
                "runtime/policies/three-stage-runtime-v1.json",
            ],
        ),
        (
            "coordination-contract",
            [
                python,
                "-B",
                "skills/three-stage-complex-workflow/scripts/validate_parallel_coordination_contract.py",
                "--workflow-skill",
                "skills/three-stage-complex-workflow/SKILL.md",
                "--dispatch-skill",
                "skills/dispatching-parallel-agents/SKILL.md",
                "--run-skill",
                "skills/staged-agent-run-protocol/SKILL.md",
                "--audit-skill",
                "skills/project-audit/SKILL.md",
                "--cases",
                "skills/three-stage-complex-workflow/references/parallel_coordination_cases.tsv",
                "--policy",
                "runtime/policies/three-stage-runtime-v1.json",
            ],
        ),
    )
    return 0 if all(run(label, command) for label, command in commands) else 1


if __name__ == "__main__":
    raise SystemExit(main())
