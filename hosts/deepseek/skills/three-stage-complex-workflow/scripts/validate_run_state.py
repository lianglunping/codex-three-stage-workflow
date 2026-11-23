#!/usr/bin/env python3
"""Read-only structural checks of actual three-stage JSON run records.

This is not an authorization service: authenticity of user evidence, file
scope and scientific results still requires the agent's contextual review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_parallel_coordination_contract import load_policy
from repair_budget import assess_budget
from model_routing import validate_stage_assignment, model_supports_role

FIELDS = {
    "task_id", "current_task_id", "workflow_stage", "run_status",
    "selected_option", "approved_scope", "approval_evidence", "scope_fingerprint",
    "approval_scope_fingerprint", "autonomy_mode", "authority_envelope",
    "acceptance_contract", "repair_attempts", "max_repair_attempts",
    "total_repair_attempts", "max_total_repair_attempts", "auto_transition_log",
}
STAGES = ("ANALYZE", "REFINE", "EXECUTE")
ALLOWED_TRANSITIONS = {
    ("ANALYZE", "REFINE"), ("REFINE", "EXECUTE"),
    ("REFINE", "ANALYZE"), ("EXECUTE", "REFINE"), ("EXECUTE", "ANALYZE"),
}
SUCCESS = {
    "CONTINUE_ANALYZE", "CONTINUE_REFINE", "CONTINUE_EXECUTE",
    "REPAIR_WITHIN_SCOPE", "COMPLETE_READY",
}


def text_present(value):
    return isinstance(value, str) and bool(value.strip())


def record_present(value):
    return text_present(value) or (isinstance(value, dict) and bool(value))


def result(decision, *issues):
    return {"decision": decision, "issues": list(issues),
            "validation_scope": "Structural consistency only; does not authenticate authority or evidence."}


def assess_state(state, *, current_task_id, current_scope_fingerprint,
                 current_model, model_roles, completion=False, runtime_evidence=None,
                 capability_evidence=None, routing_policy=None,
                 delegation_authorized=False, delegation_evidence=None,
                 user_override=None, require_model_routing=False):
    if not isinstance(state, dict):
        return result("INVALID_STATE", "State must be an object")
    missing = FIELDS - state.keys()
    if missing:
        return result("INVALID_STATE", "Missing fields: " + ", ".join(sorted(missing)))
    if not all(text_present(v) for v in
               (current_task_id, state["task_id"], state["current_task_id"])):
        return result("INVALID_TASK_IDENTITY", "Task IDs must be nonempty strings")
    if not current_task_id == state["task_id"] == state["current_task_id"]:
        return result("INVALID_TASK_IDENTITY", "State does not belong to the current task")
    stage, mode = state["workflow_stage"], state["autonomy_mode"]
    if stage not in STAGES or mode not in ("MANUAL", "BOUNDED_AUTO"):
        return result("INVALID_STATE", "Invalid stage or autonomy mode")
    if state["run_status"] == "CLOSED":
        return result("CLOSED_ROUTE_ORDINARY", "Closed records cannot resume")
    if state["run_status"] != "ACTIVE":
        return result("INVALID_STATE", "Run must be ACTIVE")

    budget_decision = assess_budget(state)
    if budget_decision and budget_decision != "REVIEW_REPAIR_CYCLE":
        # Legacy fixed budgets retain their original stopping behavior.
        return result(budget_decision, "Repair budget or renewal ledger requires correction")

    if not all(text_present(v) for v in (state["scope_fingerprint"], current_scope_fingerprint)):
        return result("INVALID_SCOPE", "Independent current scope fingerprint is required")
    if state["scope_fingerprint"] != current_scope_fingerprint:
        return result("RETURN_TO_AFFECTED_PLANNING", "Recorded and actual scope disagree")
    if not text_present(current_model):
        return result("PAUSE_CURRENT_MODEL_UNKNOWN", "Provide current runtime model identity")
    role = "CANONICAL_INTEGRATOR" if stage == "EXECUTE" else "READ_ONLY_REVIEWER"
    uses_routing = (require_model_routing or "workflow_policy_version" in state
                    or "model_routing" in state)
    if uses_routing:
        if state.get("workflow_policy_version") != "2.1.0":
            return result("INVALID_MODEL_ROUTING", "New run requires workflow_policy_version 2.1.0")
        route = validate_stage_assignment(state, routing_policy or {}, current_model,
                                         runtime_evidence, capability_evidence,
                                         delegation_authorized=delegation_authorized,
                                         delegation_evidence=delegation_evidence,
                                         user_override=user_override)
        if route["decision"] not in {"ROUTE_CURRENT", "ROUTE_DELEGATE"}:
            return result(route["decision"], "Stage lead routing failed: " + str(route))
        if not model_supports_role(current_model, role, runtime_evidence, capability_evidence):
            return result("PAUSE_MODEL_ROLE_UNAVAILABLE", "Root coordination role lacks independent capability evidence")
    elif role not in model_roles.get(current_model, []):
        return result("PAUSE_MODEL_ROLE_UNAVAILABLE", "Current root model is incompatible with " + role)
    if stage != "ANALYZE" and not text_present(state["selected_option"]):
        return result("RETURN_TO_REFINE_MISSING_SELECTION", "Record a selected option")
    if mode == "BOUNDED_AUTO" or stage == "EXECUTE":
        if not text_present(state["approval_evidence"]) or not record_present(state["authority_envelope"]):
            return result("PAUSE_AUTHORITY", "Applicable user evidence and authority envelope are required")
    if stage == "EXECUTE":
        if not record_present(state["approved_scope"]):
            return result("RETURN_TO_REFINE_INCOMPLETE_AUTHORITY", "Approved scope is missing")
        if state["approval_scope_fingerprint"] != current_scope_fingerprint:
            return result("RETURN_TO_AFFECTED_PLANNING", "Approval does not match the current scope")

    gates, seen = state["acceptance_contract"], set()
    if not isinstance(gates, list):
        return result("INVALID_ACCEPTANCE", "Acceptance contract must be an array")
    for gate in gates:
        if not isinstance(gate, dict) or not all(text_present(gate.get(k)) for k in
                ("gate_id", "criterion", "verification_method", "pass_condition")):
            return result("INVALID_ACCEPTANCE", "Gate ID, criterion, method and pass condition are required")
        if gate["gate_id"] in seen:
            return result("INVALID_ACCEPTANCE", "Duplicate gate ID: " + gate["gate_id"])
        seen.add(gate["gate_id"])
        if type(gate.get("required")) is not bool or gate.get("status") not in ("PENDING", "PASS", "FAIL", "BLOCKED") or "evidence" not in gate:
            return result("INVALID_ACCEPTANCE", "Invalid gate required/status/evidence fields")
        if gate["status"] == "PASS" and not record_present(gate["evidence"]):
            return result("INVALID_ACCEPTANCE", "PASS needs evidence: " + gate["gate_id"])
    required = [gate for gate in gates if gate["required"]]
    if stage == "EXECUTE" and not required:
        return result("RETURN_TO_REFINE_ACCEPTANCE_NOT_READY", "At least one required executable gate is needed")

    receipts = state["auto_transition_log"]
    if not isinstance(receipts, list):
        return result("INVALID_TRANSITION_RECEIPT", "Transition log must be an array")
    if mode == "BOUNDED_AUTO":
        previous = "ANALYZE"
        for receipt in receipts:
            if not isinstance(receipt, dict) or not all(text_present(receipt.get(k)) for k in
                    ("from_stage", "to_stage", "scope_fingerprint", "evidence")):
                return result("INVALID_TRANSITION_RECEIPT", "Receipt fields are incomplete")
            edge = (receipt["from_stage"], receipt["to_stage"])
            if edge not in ALLOWED_TRANSITIONS or receipt["from_stage"] != previous:
                return result("INVALID_TRANSITION_ORDER", "Transition chain must start at ANALYZE and pass REFINE")
            if receipt.get("exit_contract_status") != "PASS" or receipt.get("authority_match") is not True:
                return result("INVALID_TRANSITION_RECEIPT", "Exit gate and authority must pass")
            previous = receipt["to_stage"]
        if previous != stage or (receipts and receipts[-1]["scope_fingerprint"] != current_scope_fingerprint):
            return result("REGENERATE_RECEIPT_IN_REFINE", "Recover current transition evidence before dependent writes")

    if stage == "EXECUTE" and mode == "MANUAL" and any(g["status"] == "FAIL" for g in gates):
        return result("PAUSE_CHECK_FAILED", "Report the failed check and await the user's repair decision")
    stop = state.get("stop_condition", "none")
    if not text_present(stop):
        return result("INVALID_STATE", "stop_condition must be a nonempty string when supplied")
    if stop.lower() != "none":
        return result("PAUSE_STOP_CONDITION", "Resolve the actual hard stop before further work: " + stop)
    if completion:
        if stage != "EXECUTE" or not required or any(g["status"] != "PASS" for g in required):
            return result("INCOMPLETE_ACCEPTANCE", "Completion requires EXECUTE and every required gate PASS")
        return result("COMPLETE_READY")
    if stage == "EXECUTE":
        if any(g["status"] == "BLOCKED" for g in required):
            return result("PAUSE_ACCEPTANCE_BLOCKED", "A required acceptance gate cannot currently be verified")
        if budget_decision:
            return result(budget_decision, "Review diagnosis, next approach and progress evidence; record renewal internally")
        if any(g["status"] == "FAIL" for g in required):
            return result("REPAIR_WITHIN_SCOPE", "Repair only the verified in-scope failure within the remaining budget")
    return result("CONTINUE_" + stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--current-task-id", required=True)
    parser.add_argument("--scope-fingerprint", required=True,
                        help="Independently reconstructed current scope digest")
    parser.add_argument("--current-model", required=True)
    parser.add_argument("--policy", type=Path,
                        default=Path(__file__).resolve().parents[1] / "policies" / "three-stage-runtime-v1.json")
    parser.add_argument("--completion", action="store_true")
    parser.add_argument("--runtime-evidence", type=Path)
    parser.add_argument("--capability-evidence", type=Path)
    parser.add_argument("--user-override", type=Path)
    parser.add_argument("--delegation-authorized", action="store_true")
    parser.add_argument("--delegation-evidence")
    parser.add_argument("--require-model-routing", action="store_true",
                        help="Require new-run model routing; legacy records otherwise stay compatible")
    args = parser.parse_args()
    roles, errors = load_policy(args.policy)
    if errors:
        output = result("INVALID_POLICY", *errors)
    else:
        try:
            state = json.loads(args.state.read_text(encoding="utf-8"))
            read_optional = lambda p: json.loads(p.read_text(encoding="utf-8")) if p else None
            runtime = read_optional(args.runtime_evidence)
            capabilities = read_optional(args.capability_evidence)
            override = read_optional(args.user_override)
            policy = json.loads(args.policy.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            output = result("INVALID_STATE", str(exc))
        else:
            output = assess_state(state, current_task_id=args.current_task_id,
                                  current_scope_fingerprint=args.scope_fingerprint,
                                  current_model=args.current_model, model_roles=roles,
                                  completion=args.completion, runtime_evidence=runtime,
                                  capability_evidence=capabilities, routing_policy=policy,
                                  delegation_authorized=args.delegation_authorized,
                                  delegation_evidence=args.delegation_evidence,
                                  user_override=override, require_model_routing=args.require_model_routing)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["decision"] in SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
