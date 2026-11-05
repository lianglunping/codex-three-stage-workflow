#!/usr/bin/env python3
"""Validate model routing, parallel-write isolation, seals, and audit binding."""

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import sys


COLUMNS = [
    "case_id", "stage", "model", "agent_path", "role", "base_matches",
    "write_scope", "overlaps_active", "active_work", "active_writer_count",
    "observations_match", "drift_class", "receipt_present", "receipt_current",
    "expected_decision",
]
READ_ONLY = {"READ_ONLY_REVIEWER", "AUDITOR"}
POLICY_KEYS = {
    "version", "activation", "autonomy_modes", "stop_conditions",
    "model_roles", "invariants", "limitations", "stage_model_defaults", "subagent_selection",
}

REQUIRED = {
    "workflow": [
        "gpt-6.1-sol", "StageExitContract", "sole canonical integrator",
        "at most one active writer", "same issue fingerprint", "three-stage-runtime-v1.json",
    ],
    "dispatch": [
        "READ_ONLY_REVIEWER", "STAGING_WRITER", "CANONICAL_INTEGRATOR",
        "AUDITOR", "coordination/staging/<assignment_id>/", "base_revision",
        "return_fingerprint", "root integrator", "metadata-only",
        "late write", "two identical canonical manifests", "three-stage-runtime-v1.json",
    ],
    "run": [
        "metadata/coordination.yaml", "coordination/agent_assignments.tsv",
        "coordination/integration_events.tsv", "coordination/audit_receipts.tsv",
        "register_agent_assignment.py", "record_integration.py",
        "snapshot_revision.py", "audit_receipt.py", "root is the sole canonical integrator",
        "revision_id + manifest_sha256 + scope_fingerprint + audit_cutoff", "three-stage-runtime-v1.json",
    ],
    "audit": [
        "quiescent sealed revision", "revision_id, manifest_sha256, scope_fingerprint, audit_cutoff",
        "role `AUDITOR`", "metadata-only", "late-write", "invalidates the receipt", "three-stage-runtime-v1.json",
    ],
}


def parse_bool(value: str, case_id: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{case_id}: invalid boolean {value!r}")


def parse_nonnegative_int(value: str, case_id: str, field: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{case_id}: invalid integer {field}={value!r}") from exc
    if parsed < 0 or str(parsed) != value.strip():
        raise ValueError(f"{case_id}: invalid nonnegative integer {field}={value!r}")
    return parsed


def load_policy(path: pathlib.Path) -> tuple[dict[str, list[str]], list[str]]:
    if not path.is_file():
        return {}, [f"missing policy: {path}"]
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, [f"cannot parse policy {path}: {exc}"]
    errors: list[str] = []
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        return {}, [
            "invalid policy schema: expected version, activation, autonomy_modes, "
            "stop_conditions, model_roles, invariants, limitations, stage_model_defaults, subagent_selection"
        ]
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
        "MANUAL", "BOUNDED_AUTO",
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


def resolve(row: dict[str, str], model_roles: dict[str, list[str]],
            runtime_evidence=None, capability_evidence=None) -> str:
    case_id = row["case_id"]
    base_matches = parse_bool(row["base_matches"], case_id)
    overlap = parse_bool(row["overlaps_active"], case_id)
    active = parse_bool(row["active_work"], case_id)
    active_writer_count = parse_nonnegative_int(row["active_writer_count"], case_id, "active_writer_count")
    stable = parse_bool(row["observations_match"], case_id)
    receipt = parse_bool(row["receipt_present"], case_id)
    receipt_current = parse_bool(row["receipt_current"], case_id)
    role = row["role"]
    scope = row["write_scope"]

    if runtime_evidence is not None or capability_evidence is not None:
        from model_routing import model_supports_role
        if not model_supports_role(row["model"], role, runtime_evidence, capability_evidence):
            return "REJECT_MODEL_ROLE"
    elif role not in model_roles.get(row["model"], []):
        return "REJECT_MODEL_ROLE"
    if role == "CANONICAL_INTEGRATOR" and row["agent_path"] not in {"root", "/root"}:
        return "REJECT_NONROOT_INTEGRATOR"
    if role in READ_ONLY and scope != "NONE":
        return "REJECT_READONLY_WRITE"
    if role == "STAGING_WRITER" and scope != "OWN_STAGING":
        return "REJECT_STAGING_SCOPE"
    if role in {"STAGING_WRITER", "CANONICAL_INTEGRATOR"} and active_writer_count > 0:
        return "REJECT_SECOND_ACTIVE_WRITER"
    if row["stage"] in {"ANALYZE", "REFINE"} and role not in READ_ONLY:
        return "REJECT_PLANNING_WRITE_ROLE"
    if not base_matches:
        return "REJECT_STALE_BASE"
    if overlap:
        return "REJECT_OVERLAP"
    if row["stage"] == "SEAL":
        if active:
            return "BLOCK_NOT_QUIESCENT"
        return "SEAL_REVISION" if stable else "BLOCK_UNSTABLE"
    if row["stage"] == "AUDIT":
        if not receipt:
            return "BLOCK_NO_RECEIPT"
        if not receipt_current:
            return "REJECT_STALE_RECEIPT"
        if row["drift_class"] in {"semantic", "late-write"}:
            return "INVALIDATE_RECEIPT"
        if row["drift_class"] == "metadata-only":
            return "REUSE_RECEIPT"
        if row["drift_class"] == "out-of-scope":
            return "ISOLATE_REVIEW"
        return "ACCEPT_RECEIPT"
    if row["stage"] in {"ANALYZE", "REFINE"}:
        return "ALLOW_BOUNDED_PLANNING"
    if row["stage"] == "EXECUTE" and role == "STAGING_WRITER":
        return "ALLOW_STAGING_EXECUTION"
    if row["stage"] == "EXECUTE" and role == "CANONICAL_INTEGRATOR":
        return "ALLOW_CANONICAL_EXECUTION"
    return "UNRESOLVED"


def read_text(path: pathlib.Path, label: str, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing {label}: {path}")
        return ""
    try:
        return " ".join(path.read_text(encoding="utf-8").split()).lower()
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {label}: {exc}")
        return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-skill", type=pathlib.Path, required=True)
    parser.add_argument("--dispatch-skill", type=pathlib.Path, required=True)
    parser.add_argument("--run-skill", type=pathlib.Path, required=True)
    parser.add_argument("--audit-skill", type=pathlib.Path, required=True)
    parser.add_argument("--cases", type=pathlib.Path, required=True)
    parser.add_argument(
        "--policy",
        type=pathlib.Path,
        default=pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex")) / "policies/three-stage-runtime-v1.json",
    )
    args = parser.parse_args()

    failures: list[str] = []
    inputs: list[str] = []
    model_roles, policy_errors = load_policy(args.policy)
    inputs.extend(policy_errors)
    paths = {
        "workflow": args.workflow_skill,
        "dispatch": args.dispatch_skill,
        "run": args.run_skill,
        "audit": args.audit_skill,
    }
    texts = {key: read_text(path, key, inputs) for key, path in paths.items()}
    for key, tokens in REQUIRED.items():
        for token in tokens:
            if " ".join(token.split()).lower() not in texts[key]:
                failures.append(f"{key} missing contract token: {token}")

    count = 0
    if not args.cases.is_file():
        inputs.append(f"missing cases: {args.cases}")
    else:
        try:
            with args.cases.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                if reader.fieldnames != COLUMNS:
                    inputs.append(f"unexpected case columns: {reader.fieldnames}")
                    rows = []
                else:
                    rows = list(reader)
        except (OSError, UnicodeError, csv.Error) as exc:
            inputs.append(f"cannot parse cases: {exc}")
            rows = []
        count = len(rows)
        if count < 16:
            failures.append(f"expected at least 16 cases, found {count}")
        seen: set[str] = set()
        for row in rows:
            case_id = row["case_id"]
            if not case_id or case_id in seen:
                inputs.append(f"missing or duplicate case_id: {case_id!r}")
                continue
            seen.add(case_id)
            try:
                actual = resolve(row, model_roles)
            except ValueError as exc:
                inputs.append(str(exc))
                continue
            if actual != row["expected_decision"]:
                failures.append(
                    f"{case_id}: expected {row['expected_decision']}, resolved {actual}"
                )

    if inputs:
        for item in inputs:
            print(f"ERROR: {item}", file=sys.stderr)
        return 2
    if failures:
        for item in failures:
            print(f"FAIL: {item}", file=sys.stderr)
        print(f"SUMMARY: {len(failures)} failure(s), {count} case(s)", file=sys.stderr)
        return 1
    print(f"PASS: cross-skill coordination contract and {count} cases validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
