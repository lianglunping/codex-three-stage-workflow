#!/usr/bin/env python3
"""Run all bundled, read-only validations for the three-stage Skill."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    skill_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Validate the complete three-stage Skill bundle."
    )
    parser.add_argument("--skill-root", type=pathlib.Path, default=skill_root)
    parser.add_argument(
        "--codex-home", type=pathlib.Path, default=pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex"))
    )
    parser.add_argument(
        "--agents-skills-root",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".agents" / "skills",
    )
    parser.add_argument("--max-core-lines", type=int, default=400)
    return parser.parse_args()


def run_check(label: str, command: list[str], failures: list[str]) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if output:
        print(f"[{label}]\n{output}")
    if result.returncode != 0:
        failures.append(f"{label} exited {result.returncode}")


def validate_static_files(
    skill_root: pathlib.Path,
    policy_path: pathlib.Path,
    max_core_lines: int,
    failures: list[str],
) -> None:
    for script in skill_root.glob("scripts/*.py"):
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            failures.append(f"Python syntax error in {script}: {exc}")
    try:
        json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"runtime policy JSON error: {exc}")
    core_path = skill_root / "SKILL.md"
    try:
        core_text = core_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"cannot read core Skill: {exc}")
        return
    core_lines = len(core_text.splitlines())
    if core_lines > max_core_lines:
        failures.append(
            f"core Skill has {core_lines} lines; limit is {max_core_lines}"
        )
    ui_path = skill_root / "agents" / "openai.yaml"
    try:
        ui_text = ui_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"cannot read UI metadata: {exc}")
    else:
        for token in (
            "interface:",
            "display_name:",
            "short_description:",
            "default_prompt:",
            "$three-stage-complex-workflow",
        ):
            if token not in ui_text:
                failures.append(f"UI metadata missing {token}")


def main() -> int:
    args = parse_args()
    skill_root = args.skill_root.resolve()
    codex_home = args.codex_home.resolve()
    policy = codex_home / "policies" / "three-stage-runtime-v1.json"
    os.environ["CODEX_HOME"] = str(codex_home)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    failures: list[str] = []

    run_check(
        "workflow-contract",
        [
            sys.executable,
            str(skill_root / "scripts" / "validate_workflow_contract.py"),
            "--skill-root",
            str(skill_root),
            "--agents",
            str(codex_home / "AGENTS.md"),
            "--cases",
            str(skill_root / "references" / "regression_cases.tsv"),
            "--state-cases",
            str(skill_root / "references" / "state_integrity_cases.tsv"),
            "--policy",
            str(policy),
        ],
        failures,
    )
    audit_skill = args.agents_skills_root / "project-audit" / "SKILL.md"
    if not audit_skill.is_file():
        audit_skill = codex_home / "skills" / "project-audit" / "SKILL.md"
    run_check(
        "parallel-coordination",
        [
            sys.executable,
            str(skill_root / "scripts" / "validate_parallel_coordination_contract.py"),
            "--workflow-skill",
            str(skill_root / "SKILL.md"),
            "--dispatch-skill",
            str(codex_home / "skills" / "dispatching-parallel-agents" / "SKILL.md"),
            "--run-skill",
            str(codex_home / "skills" / "staged-agent-run-protocol" / "SKILL.md"),
            "--audit-skill",
            str(audit_skill),
            "--cases",
            str(skill_root / "references" / "parallel_coordination_cases.tsv"),
            "--policy",
            str(policy),
        ],
        failures,
    )
    validate_static_files(skill_root, policy, args.max_core_lines, failures)
    run_check(
        "stage-model-routing",
        [sys.executable, str(skill_root / "scripts" / "test_model_routing.py")],
        failures,
    )
    run_check(
        "model-compatibility",
        [sys.executable, str(skill_root / "scripts" / "test_model_compatibility.py")],
        failures,
    )
    run_check(
        "real-run-state",
        [sys.executable, str(skill_root / "scripts" / "test_run_state.py")],
        failures,
    )
    run_check(
        "renewable-repair-budget",
        [sys.executable, str(skill_root / "scripts" / "test_repair_budget.py")],
        failures,
    )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("PASS: complete bundled validation succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
