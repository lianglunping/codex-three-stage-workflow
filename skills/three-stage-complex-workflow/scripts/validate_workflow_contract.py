#!/usr/bin/env python3
"""Validate prose and legacy prompt-route diagnostics; new routing uses model_routing."""

from __future__ import annotations

import argparse
import csv
from fixture_cases import load_cases
import json
import os
import pathlib
import sys
import unicodedata
from typing import Dict, List, Tuple


REQUIRED_COLUMNS = [
    "case_id",
    "task_kind",
    "invocation_text",
    "explicit_invocation",
    "prior_stage",
    "workflow_task_id",
    "current_task_id",
    "run_status",
    "autonomy_mode",
    "authority_envelope",
    "selected_option",
    "approval_evidence",
    "material_drift",
    "stop_condition",
    "requested_action",
    "expected_route",
    "expected_stage",
    "expected_autonomy_mode",
    "expected_transition",
    "expected_specialist",
    "expected_model",
    "expected_model_role",
]
STATE_CASE_COLUMNS = [
    "case_id",
    "task_id",
    "current_task_id",
    "workflow_stage",
    "run_status",
    "autonomy_mode",
    "selected_option",
    "approved_scope",
    "approval_evidence",
    "approval_scope_fingerprint",
    "current_scope_fingerprint",
    "acceptance_status",
    "transition_receipt_status",
    "material_drift",
    "issue_repair_attempts",
    "max_repair_attempts",
    "total_repair_attempts",
    "max_total_repair_attempts",
    "expected_decision",
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
PRIOR_STAGES = {"NONE", "ANALYZE", "REFINE", "EXECUTE"}
RUN_STATUSES = {"NONE", "ACTIVE", "CLOSED"}
AUTONOMY_MODES = {"NONE", "MANUAL", "BOUNDED_AUTO"}
STOP_CONDITIONS = {
    "none",
    "authority_missing",
    "destructive_or_irreversible",
    "outside_authority_envelope",
    "external_side_effect",
    "global_environment_change",
    "credential_or_security_boundary",
    "scientific_evidence_conflict",
    "acceptance_cannot_be_verified",
    "model_role_unavailable",
    "repeated_failure",
    "resource_budget_exhausted",
}
POLICY_KEYS = {
    "version",
    "activation",
    "autonomy_modes",
    "stop_conditions",
    "model_roles",
    "invariants",
    "limitations",
    "stage_model_defaults",
    "subagent_selection",
}
REFERENCE_FILES = (
    "repair-policy.md",
    "stage-deliverables.md",
    "composition-contract.md",
    "validation-guide.md",
    "persistence-policy.md",
    "state-contract.md",
)
AUTO_TERMS = (
    "自动完成",
    "自动推进",
    "全自主完成",
    "全自主",
    "全自主推进",
    "自主完成",
    "自主推进",
    "无需逐阶段确认",
    "不要中途询问",
    "自动走完",
    "自动跑完",
    "全程自动",
    "一口气完成",
    "automatically complete",
    "automatically advance",
    "fully autonomous",
    "bounded_auto",
    "without stage-by-stage confirmation",
)
WORKFLOW_TERMS = (
    "$three-stage-complex-workflow",
    "三阶段工作流",
    "3阶段工作流",
    "三步工作流",
    "3步工作流",
    "三阶段流程",
    "3阶段流程",
    "three-stage workflow",
    "three stage workflow",
)
META_TERMS = (
    "是否可以",
    "是否能",
    "能否",
    "可不可以",
    "怎么使用",
    "如何使用",
    "怎么调用",
    "如何调用",
    "为什么",
    "请介绍",
    "请解释",
    "请说明",
    "我想了解",
    "讲讲",
    "怎么用",
    "有什么作用",
    "只告诉我",
    "先不要启动",
    "how to use",
    "how does",
    "what does",
    "explain",
    "describe",
    "do not start",
    "don't start",
)
AUTO_NEGATION_TERMS = (
    "不要自动",
    "不自动",
    "禁止自动",
    "改为手动",
    "手动模式",
    "do not automatically",
    "don't automatically",
    "manual mode",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate workflow prose, global routing, and regression cases."
    )
    parser.add_argument("--skill-root", required=True, type=pathlib.Path)
    parser.add_argument("--agents", required=True, type=pathlib.Path)
    parser.add_argument("--cases", required=True, type=pathlib.Path)
    parser.add_argument(
        "--state-cases",
        type=pathlib.Path,
        help="State-integrity cases (defaults to <skill-root>/references/state_integrity_cases.json)",
    )
    parser.add_argument(
        "--policy",
        type=pathlib.Path,
        default=pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex")) / "policies/three-stage-runtime-v1.json",
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
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        errors.append(
            "invalid policy schema: expected version, activation, autonomy_modes, "
            "stop_conditions, model_roles, invariants, limitations, stage_model_defaults, subagent_selection"
        )
        return {}, errors
    from model_routing import validate_routing_policy
    errors.extend(validate_routing_policy(policy))
    model_roles = policy["model_roles"]
    if not isinstance(policy["version"], str) or not policy["version"]:
        errors.append("invalid policy schema: version must be a nonempty string")
    if policy.get("activation") != "explicit_skill_natural_autonomy_or_active_run":
        errors.append(
            "invalid policy schema: activation must be "
            "explicit_skill_natural_autonomy_or_active_run"
        )
    autonomy_modes = policy["autonomy_modes"]
    if not isinstance(autonomy_modes, dict) or set(autonomy_modes) != {
        "MANUAL",
        "BOUNDED_AUTO",
    }:
        errors.append(
            "invalid policy schema: autonomy_modes must define MANUAL and BOUNDED_AUTO"
        )
    elif (
        autonomy_modes.get("MANUAL") != "explicit_each_gate"
        or autonomy_modes.get("BOUNDED_AUTO")
        != "automatic_within_authority_envelope"
    ):
        errors.append("invalid policy schema: unexpected autonomy mode semantics")
    stop_conditions = policy["stop_conditions"]
    if (
        not isinstance(stop_conditions, list)
        or any(not isinstance(item, str) or not item for item in stop_conditions)
        or not {
            "DESTRUCTIVE_OR_IRREVERSIBLE",
            "OUTSIDE_AUTHORITY_ENVELOPE",
            "ACCEPTANCE_CANNOT_BE_VERIFIED",
            "REPEATED_FAILURE",
            "RESOURCE_BUDGET_EXHAUSTED",
        }.issubset(set(stop_conditions))
    ):
        errors.append("invalid policy schema: incomplete stop_conditions string list")
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


def validate_content(
    skill_text: str,
    agents_text: str,
    ui_text: str,
    reference_texts: Dict[str, str] | None = None,
) -> List[str]:
    failures: List[str] = []
    validate_frontmatter(skill_text, failures)
    if "TODO" in skill_text:
        failures.append("SKILL.md contains TODO")

    normalized_skill = " ".join(skill_text.split())
    reference_texts = reference_texts or {}
    normalized_contract = " ".join(
        [skill_text, *(reference_texts.get(name, "") for name in REFERENCE_FILES)]
    )
    normalized_contract = " ".join(normalized_contract.split())
    normalized_agents = " ".join(agents_text.split())

    # Stable interfaces only; behavior is checked with routing and real-state cases.
    required_core_tokens = [
        "$three-stage-complex-workflow", "MANUAL", "BOUNDED_AUTO",
        "【分析问题】", "【细化方案】", "【执行方案】", "AUTO_REFINE", "AUTO_EXECUTE",
        "Automatic stage progression does not authorize subagents or delegation.",
        "Never install globally.", "Do not commit or push", "gpt-6.1-sol",
        "three-stage-runtime-v1.json",
    ]
    for token in required_core_tokens:
        if " ".join(token.split()) not in normalized_skill:
            failures.append(f"SKILL.md missing contract token: {token}")

    required_composed_tokens = [
        "job-monitor-loop",
        "orchestrate-chatgpt-pro-development",
        "writing-plans",
        "executing-plans",
        "staged-agent-run-protocol",
        "Never record hidden chain-of-thought.",
        "The proposal alone does not authorize a write",
    ]
    for token in required_composed_tokens:
        if " ".join(token.split()) not in normalized_contract:
            failures.append(f"composed Skill contract missing token: {token}")
    for name in REFERENCE_FILES:
        if f"references/{name}" not in skill_text:
            failures.append(f"SKILL.md lacks direct reference link: {name}")
        if not reference_texts.get(name, "").strip():
            failures.append(f"missing or empty Skill reference: {name}")

    required_agents_tokens = [
        "## 复杂任务三阶段工作流",
        "$three-stage-complex-workflow",
        "【分析问题】",
        "【细化方案】",
        "【执行方案】",
        "task_id",
        "current_task_id",
        "状态为 `ACTIVE`",
        "approval_evidence",
        "scope_fingerprint",
        "自动完成三阶段工作流",
        "`BOUNDED_AUTO`",
        "`authority_envelope`",
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


def normalize_invocation_text(text: str) -> str:
    """Normalize compatible Unicode forms and whitespace for stable matching."""
    return " ".join(unicodedata.normalize("NFKC", text).strip().lower().split())


def is_activation_suppressed(text: str, task_kind: str) -> bool:
    """Give explicit meta/explanatory intent priority over trigger tokens."""
    normalized = normalize_invocation_text(text)
    workflow_named = any(term in normalized for term in WORKFLOW_TERMS)
    return task_kind in {"workflow_meta_question", "workflow_maintenance"} or (
        workflow_named and any(term in normalized for term in META_TERMS)
    )


def detect_invocation_mode(text: str, task_kind: str) -> str:
    """Detect an explicit manual or bounded-autonomous workflow request."""
    normalized = normalize_invocation_text(text)
    if is_activation_suppressed(normalized, task_kind):
        return "NONE"
    explicit_skill = "$three-stage-complex-workflow" in normalized
    autonomy_negated = any(term in normalized for term in AUTO_NEGATION_TERMS)
    autonomous = (
        any(term in normalized for term in AUTO_TERMS) and not autonomy_negated
    )
    workflow_named = any(term in normalized for term in WORKFLOW_TERMS)
    if autonomous and (explicit_skill or workflow_named):
        return "BOUNDED_AUTO"
    if explicit_skill:
        return "MANUAL"
    return "NONE"


def validate_active_run_enumerations(row: Dict[str, str]) -> None:
    case_id = row["case_id"]
    prior_stage = row["prior_stage"].strip()
    run_status = row["run_status"].strip()
    if prior_stage not in PRIOR_STAGES:
        raise ValueError(
            f"{case_id}: invalid prior_stage {prior_stage!r}; "
            f"expected one of {sorted(PRIOR_STAGES)}"
        )
    if run_status not in RUN_STATUSES:
        raise ValueError(
            f"{case_id}: invalid run_status {run_status!r}; "
            f"expected one of {sorted(RUN_STATUSES)}"
        )
    autonomy_mode = row["autonomy_mode"].strip()
    if autonomy_mode not in AUTONOMY_MODES:
        raise ValueError(
            f"{case_id}: invalid autonomy_mode {autonomy_mode!r}; "
            f"expected one of {sorted(AUTONOMY_MODES)}"
        )
    stop_condition = row["stop_condition"].strip()
    if stop_condition not in STOP_CONDITIONS:
        raise ValueError(
            f"{case_id}: invalid stop_condition {stop_condition!r}; "
            f"expected one of {sorted(STOP_CONDITIONS)}"
        )


def has_active_three_stage_run(row: Dict[str, str]) -> bool:
    """Accept continuation only for a live run bound to this task identity."""
    workflow_task_id = row["workflow_task_id"].strip()
    current_task_id = row["current_task_id"].strip()
    prior_stage = row["prior_stage"].strip()
    autonomy_mode = row["autonomy_mode"].strip()
    selected = row["selected_option"].strip().lower() != "none"
    envelope = row["authority_envelope"].strip().lower() != "none"
    approval = row["approval_evidence"].strip()
    structurally_active = (
        row["prior_stage"].strip() != "NONE"
        and workflow_task_id.lower() != "none"
        and current_task_id.lower() != "none"
        and bool(workflow_task_id)
        and workflow_task_id == current_task_id
        and row["run_status"].strip() == "ACTIVE"
        and autonomy_mode in {"MANUAL", "BOUNDED_AUTO"}
    )
    if not structurally_active:
        return False
    if prior_stage == "REFINE":
        return selected
    if prior_stage == "EXECUTE":
        approval_valid = (
            autonomy_mode == "MANUAL" and approval == "approved"
        ) or (
            autonomy_mode == "BOUNDED_AUTO" and approval == "auto-authorized"
        )
        return selected and envelope and approval_valid
    return prior_stage == "ANALYZE"


def _is_missing(value: object) -> bool:
    return value is None or str(value).strip().lower() in {"", "none", "null"}


def evaluate_state_snapshot(snapshot: Dict[str, object]) -> str:
    """Return a conservative recovery/continuation decision for persisted state."""
    required = set(STATE_CASE_COLUMNS) - {"case_id", "expected_decision"}
    if any(field not in snapshot for field in required):
        return "INVALID_MISSING_FIELDS"
    if snapshot["run_status"] == "CLOSED":
        return "CLOSED_ROUTE_ORDINARY"
    if (
        _is_missing(snapshot["task_id"])
        or _is_missing(snapshot["current_task_id"])
        or snapshot["task_id"] != snapshot["current_task_id"]
    ):
        return "INVALID_TASK_IDENTITY"
    stage = str(snapshot["workflow_stage"])
    mode = str(snapshot["autonomy_mode"])
    if (
        snapshot["run_status"] != "ACTIVE"
        or stage not in {"ANALYZE", "REFINE", "EXECUTE"}
        or mode not in {"MANUAL", "BOUNDED_AUTO"}
    ):
        return "INVALID_ENUM_OR_STATUS"
    if bool(snapshot["material_drift"]) or (
        not _is_missing(snapshot["approval_scope_fingerprint"])
        and snapshot["approval_scope_fingerprint"]
        != snapshot["current_scope_fingerprint"]
    ):
        return "RETURN_TO_AFFECTED_PLANNING"
    try:
        issue_repairs = int(snapshot["issue_repair_attempts"])
        max_issue_repairs = int(snapshot["max_repair_attempts"])
        total_repairs = int(snapshot["total_repair_attempts"])
        max_total_repairs = int(snapshot["max_total_repair_attempts"])
    except (TypeError, ValueError):
        return "INVALID_REPAIR_COUNTER"
    if min(issue_repairs, max_issue_repairs, total_repairs, max_total_repairs) < 0:
        return "INVALID_REPAIR_COUNTER"
    if issue_repairs >= max_issue_repairs:
        return "PAUSE_REPEATED_FAILURE"
    if total_repairs >= max_total_repairs:
        return "PAUSE_RESOURCE_BUDGET_EXHAUSTED"
    if stage == "ANALYZE":
        return "CONTINUE_ANALYZE"
    if _is_missing(snapshot["selected_option"]):
        return "INVALID_MISSING_SELECTION"
    if stage == "REFINE":
        return "CONTINUE_REFINE"
    if (
        _is_missing(snapshot["approved_scope"])
        or _is_missing(snapshot["approval_evidence"])
        or _is_missing(snapshot["approval_scope_fingerprint"])
        or _is_missing(snapshot["current_scope_fingerprint"])
    ):
        return "RETURN_TO_REFINE_INCOMPLETE_AUTHORITY"
    approval = str(snapshot["approval_evidence"])
    if mode == "MANUAL":
        if approval != "approved" and not approval.startswith("explicit:"):
            return "RETURN_TO_REFINE_INVALID_APPROVAL"
        return "CONTINUE_EXECUTE"
    if approval != "auto-authorized" and not approval.startswith("auto:"):
        return "RETURN_TO_REFINE_INVALID_APPROVAL"
    if snapshot["acceptance_status"] not in {"READY", "PASS"}:
        return "RETURN_TO_REFINE_ACCEPTANCE_NOT_READY"
    if snapshot["transition_receipt_status"] != "CURRENT":
        return "REGENERATE_RECEIPT_AND_CONTINUE"
    return "CONTINUE_EXECUTE"


def resolve_case(row: Dict[str, str], model_roles=None, current_model=None) -> Tuple[str, str, str, str, str, str, str]:
    case_id = row["case_id"]
    explicit = parse_bool(row["explicit_invocation"], case_id)
    drift = parse_bool(row["material_drift"], case_id)
    task_kind = row["task_kind"]

    active_run = has_active_three_stage_run(row)
    detected_mode = detect_invocation_mode(row["invocation_text"], task_kind)
    suppressed = is_activation_suppressed(row["invocation_text"], task_kind)
    effective_explicit = explicit and not suppressed
    if effective_explicit and detected_mode == "NONE":
        detected_mode = "MANUAL"
    if active_run:
        autonomy_mode = row["autonomy_mode"].strip()
        if autonomy_mode == "NONE":
            autonomy_mode = "MANUAL"
    else:
        autonomy_mode = detected_mode

    if effective_explicit or detected_mode != "NONE" or active_run:
        route = "three-stage"
    elif task_kind == "routine_monitor":
        route = "specialist"
    elif task_kind in SPECIALISTS:
        route = "specialist"
    else:
        route = "ordinary"

    if route != "three-stage":
        stage = "NONE"
    elif drift:
        stage = "AFFECTED_PLANNING_STAGE"
    elif not active_run:
        stage = "ANALYZE"
    else:
        prior_stage = row["prior_stage"].strip()
        if prior_stage == "ANALYZE":
            stage = "REFINE" if row["selected_option"] != "none" else "ANALYZE"
        elif prior_stage == "REFINE":
            approval_valid = row["approval_evidence"] == "approved" or (
                autonomy_mode == "BOUNDED_AUTO"
                and row["approval_evidence"] == "auto-authorized"
            )
            stage = (
                "EXECUTE"
                if row["requested_action"] in {"execute", "continue", "resume"}
                and approval_valid
                else "REFINE"
            )
        else:
            stage = "EXECUTE"

    if route != "three-stage":
        transition = "NONE"
    elif row["stop_condition"] != "none":
        transition = "PAUSE_STOP_CONDITION"
    elif drift:
        transition = "PAUSE_SCOPE_DRIFT"
    elif autonomy_mode == "BOUNDED_AUTO":
        if row["authority_envelope"].strip().lower() == "none":
            transition = "PAUSE_AUTHORITY"
        else:
            transition = "AUTO_CONTINUE"
    elif stage == "ANALYZE":
        transition = "REQUEST_SELECTION"
    elif stage == "REFINE":
        transition = "REQUEST_EXECUTION_APPROVAL"
    else:
        transition = "EXECUTE"

    specialist = SPECIALISTS.get(task_kind, "none")
    if stage in {"ANALYZE", "REFINE", "AFFECTED_PLANNING_STAGE"}:
        model_role = "READ_ONLY_PLANNER" if stage == "ANALYZE" else "PLAN_REFINER"
    elif stage == "EXECUTE":
        model_role = "EXECUTION_WORKER"
    else:
        model_role = "ORDINARY"
    model = "runtime-default"
    if model_role != "ORDINARY":
        if model_roles is None:
            policy_path = pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex")) / "policies/three-stage-runtime-v1.json"
            model_roles = json.loads(policy_path.read_text())["model_roles"]
        policy_role = ROLE_ALIASES[model_role]
        # Runtime identity is an input, never inferred from policy insertion order.
        model = current_model if policy_role in model_roles.get(current_model, []) else "unavailable"
        if current_model is None:
            transition = "PAUSE_CURRENT_MODEL_UNKNOWN"
        elif model == "unavailable":
            transition = "PAUSE_MODEL_ROLE_UNAVAILABLE"
    return (
        route,
        stage,
        autonomy_mode,
        transition,
        specialist,
        model,
        model_role,
    )


def validate_cases(path: pathlib.Path, model_roles: Dict[str, List[str]]) -> Tuple[List[str], List[str], int]:
    failures: List[str] = []
    input_failures: List[str] = []
    if not path.is_file():
        return failures, [f"missing cases file: {path}"], 0
    try:
        columns, rows = load_cases(path)
        if columns != REQUIRED_COLUMNS:
            return failures, [f"unexpected case columns: {columns}"], 0
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
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
            validate_active_run_enumerations(row)
            actual = resolve_case(row, model_roles, current_model="gpt-6.1-sol")
            # This is an explicit regression fixture, not a runtime fallback.
        except ValueError as exc:
            input_failures.append(str(exc))
            continue
        expected = (
            row["expected_route"],
            row["expected_stage"],
            row["expected_autonomy_mode"],
            row["expected_transition"],
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


def validate_state_cases(path: pathlib.Path) -> Tuple[List[str], List[str], int]:
    """Validate persisted-state recovery decisions independently of prompt routing."""
    failures: List[str] = []
    input_failures: List[str] = []
    if not path.is_file():
        return failures, [f"missing state cases file: {path}"], 0
    try:
        columns, rows = load_cases(path)
        if columns != STATE_CASE_COLUMNS:
            return failures, [f"unexpected state case columns: {columns}"], 0
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        return failures, [f"cannot parse state cases file {path}: {exc}"], 0
    if len(rows) < 12:
        failures.append(f"expected at least 12 state cases, found {len(rows)}")
    seen = set()
    for row in rows:
        case_id = row["case_id"]
        if not case_id or case_id in seen:
            input_failures.append(f"missing or duplicate state case_id: {case_id!r}")
            continue
        seen.add(case_id)
        try:
            snapshot: Dict[str, object] = dict(row)
            snapshot["material_drift"] = parse_bool(row["material_drift"], case_id)
            actual = evaluate_state_snapshot(snapshot)
        except ValueError as exc:
            input_failures.append(str(exc))
            continue
        if actual != row["expected_decision"]:
            failures.append(
                f"{case_id}: expected {row['expected_decision']}, resolved {actual}"
            )
    return failures, input_failures, len(rows)


def main() -> int:
    args = parse_args()
    failures: List[str] = []
    input_failures: List[str] = []
    skill_text = require_file(args.skill_root / "SKILL.md", input_failures)
    ui_text = require_file(args.skill_root / "agents/openai.yaml", input_failures)
    agents_text = require_file(args.agents, input_failures)
    reference_texts = {
        name: require_file(args.skill_root / "references" / name, input_failures)
        for name in REFERENCE_FILES
    }
    if not input_failures:
        failures.extend(
            validate_content(skill_text, agents_text, ui_text, reference_texts)
        )
    model_roles, policy_errors = load_policy(args.policy)
    input_failures.extend(policy_errors)
    case_failures, case_input_failures, case_count = validate_cases(args.cases, model_roles)
    failures.extend(case_failures)
    input_failures.extend(case_input_failures)
    state_cases_path = args.state_cases or (
        args.skill_root / "references" / "state_integrity_cases.json"
    )
    state_failures, state_input_failures, state_case_count = validate_state_cases(
        state_cases_path
    )
    failures.extend(state_failures)
    input_failures.extend(state_input_failures)

    if input_failures:
        for failure in input_failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        print(
            f"SUMMARY: {len(input_failures)} input error(s), {case_count} route case(s), "
            f"{state_case_count} state case(s)",
            file=sys.stderr,
        )
        return 2

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(
            f"SUMMARY: {len(failures)} failure(s), {case_count} route case(s), "
            f"{state_case_count} state case(s)",
            file=sys.stderr,
        )
        return 1

    print(
        f"PASS: workflow contract, {case_count} route cases, and "
        f"{state_case_count} state-integrity cases validated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
