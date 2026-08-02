#!/usr/bin/env python3
"""Validate the installed three-stage workflow contract without modifying it."""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from typing import Dict, List, Tuple


REQUIRED_COLUMNS = [
    "case_id",
    "task_kind",
    "explicit_invocation",
    "prior_stage",
    "selected_option",
    "approval_evidence",
    "material_drift",
    "requested_action",
    "expected_route",
    "expected_stage",
    "expected_specialist",
    "expected_model",
    "expected_model_role",
]

SPECIALISTS = {
    "routine_monitor": "job-monitor-loop",
    "complex_coding_pro": "orchestrate-chatgpt-pro-development",
    "scientific_planning": "multi-agent-bioinformatics-planner",
    "approved_research_execution": "staged-agent-run-protocol",
    "implementation_planning": "writing-plans",
    "approved_software_execution": "executing-plans",
}

ROLE_ALIASES = {
    "READ_ONLY_PLANNER": "READ_ONLY_REVIEWER",
    "PLAN_REFINER": "READ_ONLY_REVIEWER",
    "EXECUTION_WORKER": "STAGING_WRITER",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate workflow prose, global routing, and regression cases."
    )
    parser.add_argument("--skill-root", required=True, type=pathlib.Path)
    parser.add_argument("--agents", required=True, type=pathlib.Path)
    parser.add_argument("--cases", required=True, type=pathlib.Path)
    parser.add_argument(
        "--policy",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".codex/policies/three-stage-runtime-v1.json",
    )
    return parser.parse_args()


def load_policy(path: pathlib.Path) -> tuple[Dict[str, List[str]], List[str]]:
    errors: List[str] = []
    if not path.is_file():
        return {}, [f"missing policy: {path}"]
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, [f"cannot parse policy {path}: {exc}"]
    if not isinstance(policy, dict) or set(policy) != {"version", "model_roles", "invariants", "limitations"}:
        errors.append("invalid policy schema: expected version, model_roles, invariants, limitations")
        return {}, errors
    model_roles = policy["model_roles"]
    if not isinstance(policy["version"], str) or not policy["version"]:
        errors.append("invalid policy schema: version must be a nonempty string")
    if not isinstance(model_roles, dict) or not model_roles:
        errors.append("invalid policy schema: model_roles must be a nonempty object")
    elif any(not isinstance(model, str) or not model or not isinstance(roles, list) or not roles or any(not isinstance(role, str) or not role for role in roles) for model, roles in model_roles.items()):
        errors.append("invalid policy schema: model_roles values must be nonempty string lists")
    if not isinstance(policy["invariants"], list) or any(not isinstance(item, str) or not item for item in policy["invariants"]):
        errors.append("invalid policy schema: invariants must be a string list")
    if not isinstance(policy["limitations"], str):
        errors.append("invalid policy schema: limitations must be a string")
    return model_roles if not errors else {}, errors


def require_file(path: pathlib.Path, failures: List[str]) -> str:
    if not path.is_file():
        failures.append(f"missing file: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"cannot read {path}: {exc}")
        return ""


def validate_frontmatter(text: str, failures: List[str]) -> None:
    if not text.startswith("---\n"):
        failures.append("SKILL.md lacks YAML frontmatter opening")
        return
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        failures.append("SKILL.md lacks YAML frontmatter closing")
        return
    keys = [
        line.split(":", 1)[0]
        for line in parts[1].splitlines()
        if line and not line.startswith(" ") and ":" in line
    ]
    if keys != ["name", "description"]:
        failures.append(f"unexpected frontmatter keys: {keys}")


def validate_content(skill_text: str, agents_text: str, ui_text: str) -> List[str]:
    failures: List[str] = []
    validate_frontmatter(skill_text, failures)
    if "TODO" in skill_text:
        failures.append("SKILL.md contains TODO")

    normalized_skill = " ".join(skill_text.split())
    normalized_agents = " ".join(agents_text.split())

    required_skill_tokens = [
        "$three-stage-complex-workflow",
        "task_id: string | null",
        "workflow_stage: ANALYZE | REFINE | EXECUTE",
        "selected_option: string | null",
        "approved_scope: string | null",
        "approval_evidence: string | null",
        "scope_fingerprint: string | null",
        "【分析问题】",
        "【细化方案】",
        "【执行方案】",
        "job-monitor-loop",
        "orchestrate-chatgpt-pro-development",
        "writing-plans",
        "executing-plans",
        "staged-agent-run-protocol",
        "Never install globally.",
        "Do not commit or push",
        "Never record hidden chain-of-thought.",
        "The proposal alone does not authorize a write",
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "StageExitContract",
        "same issue fingerprint",
        "must not hold canonical write permission",
        "three-stage-runtime-v1.json",
    ]
    for token in required_skill_tokens:
        if " ".join(token.split()) not in normalized_skill:
            failures.append(f"SKILL.md missing contract token: {token}")

    required_agents_tokens = [
        "## 复杂任务三阶段工作流",
        "$three-stage-complex-workflow",
        "【分析问题】",
        "【细化方案】",
        "【执行方案】",
        "task_id",
        "approval_evidence",
        "scope_fingerprint",
        "专用 Skill 不得绕过三阶段批准边界",
    ]
    for token in required_agents_tokens:
        if " ".join(token.split()) not in normalized_agents:
            failures.append(f"AGENTS.md missing routing token: {token}")

    if '$three-stage-complex-workflow' not in ui_text:
        failures.append("agents/openai.yaml default prompt lacks explicit Skill invocation")
    return failures


def parse_bool(value: str, case_id: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{case_id}: expected boolean, got {value!r}")


def resolve_case(row: Dict[str, str]) -> Tuple[str, str, str, str, str]:
    case_id = row["case_id"]
    explicit = parse_bool(row["explicit_invocation"], case_id)
    drift = parse_bool(row["material_drift"], case_id)
    task_kind = row["task_kind"]

    if explicit:
        route = "three-stage"
    elif task_kind == "routine_monitor":
        route = "specialist"
    elif task_kind in {"simple_qa", "small_direct_change"}:
        route = "ordinary"
    else:
        route = "three-stage"

    if route != "three-stage":
        stage = "NONE"
    elif drift:
        stage = "AFFECTED_PLANNING_STAGE"
    elif (
        row["requested_action"] in {"execute", "continue", "resume"}
        and row["approval_evidence"] == "approved"
    ):
        stage = "EXECUTE"
    elif row["selected_option"] != "none":
        stage = "REFINE"
    else:
        stage = "ANALYZE"

    specialist = SPECIALISTS.get(task_kind, "none")
    if stage in {"ANALYZE", "REFINE", "AFFECTED_PLANNING_STAGE"}:
        model = "gpt-5.6-sol"
        model_role = "READ_ONLY_PLANNER" if stage == "ANALYZE" else "PLAN_REFINER"
    elif stage == "EXECUTE":
        model = "gpt-5.6-terra"
        model_role = "EXECUTION_WORKER"
    else:
        model = "runtime-default"
        model_role = "ORDINARY"
    return route, stage, specialist, model, model_role


def validate_cases(path: pathlib.Path, model_roles: Dict[str, List[str]]) -> Tuple[List[str], List[str], int]:
    failures: List[str] = []
    input_failures: List[str] = []
    if not path.is_file():
        return failures, [f"missing cases file: {path}"], 0
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != REQUIRED_COLUMNS:
                return failures, [f"unexpected case columns: {reader.fieldnames}"], 0
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        return failures, [f"cannot parse cases file {path}: {exc}"], 0

    if len(rows) < 12:
        failures.append(f"expected at least 12 regression cases, found {len(rows)}")
    seen = set()
    for row in rows:
        case_id = row["case_id"]
        if not case_id or case_id in seen:
            input_failures.append(f"missing or duplicate case_id: {case_id!r}")
            continue
        seen.add(case_id)
        try:
            actual = resolve_case(row)
        except ValueError as exc:
            input_failures.append(str(exc))
            continue
        expected = (
            row["expected_route"],
            row["expected_stage"],
            row["expected_specialist"],
            row["expected_model"],
            row["expected_model_role"],
        )
        if actual != expected:
            failures.append(f"{case_id}: expected {expected}, resolved {actual}")
        expected_model, expected_role = row["expected_model"], row["expected_model_role"]
        if expected_model != "runtime-default" and expected_role != "ORDINARY":
            policy_role = ROLE_ALIASES.get(expected_role, expected_role)
            if policy_role not in model_roles.get(expected_model, []):
                failures.append(
                    f"{case_id}: policy rejects expected model/role "
                    f"{expected_model}/{expected_role} (maps to {policy_role})"
                )
    return failures, input_failures, len(rows)


def main() -> int:
    args = parse_args()
    failures: List[str] = []
    input_failures: List[str] = []
    skill_text = require_file(args.skill_root / "SKILL.md", input_failures)
    ui_text = require_file(args.skill_root / "agents/openai.yaml", input_failures)
    agents_text = require_file(args.agents, input_failures)
    if not input_failures:
        failures.extend(validate_content(skill_text, agents_text, ui_text))
    model_roles, policy_errors = load_policy(args.policy)
    input_failures.extend(policy_errors)
    case_failures, case_input_failures, case_count = validate_cases(args.cases, model_roles)
    failures.extend(case_failures)
    input_failures.extend(case_input_failures)

    if input_failures:
        for failure in input_failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        print(
            f"SUMMARY: {len(input_failures)} input error(s), {case_count} case(s)",
            file=sys.stderr,
        )
        return 2

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"SUMMARY: {len(failures)} failure(s), {case_count} case(s)", file=sys.stderr)
        return 1

    print(f"PASS: workflow contract and {case_count} regression cases validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
