"""Validate renewable repair ledgers and create an evidence-backed next cycle.

Pure record operations: callers persist the returned copy in their existing
task ledger only after reviewing actual authority, progress and resource limits.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def assess_budget(state):
    """Return None or a structural error/review decision; never reset counters."""
    fields = ("repair_attempts", "max_repair_attempts", "total_repair_attempts",
              "max_total_repair_attempts")
    values = [state.get(k) for k in fields]
    if any(type(v) is not int for v in values):
        return "INVALID_REPAIR_COUNTER"
    issue, issue_max, total, cycle_max = values
    if issue < 0 or total < 0 or not 1 <= issue_max <= 3 or not 1 <= cycle_max <= 6 or issue > total:
        return "INVALID_REPAIR_COUNTER"
    mode = state.get("repair_budget_mode", "FIXED")
    if mode not in ("FIXED", "RENEWABLE"):
        return "INVALID_REPAIR_BUDGET_MODE"
    if mode == "FIXED":
        if any(k in state for k in ("repair_cycle_attempts", "repair_cycle_log", "repair_renewal_authority")):
            return "INVALID_REPAIR_BUDGET_MODE"
        if issue >= issue_max:
            return "PAUSE_REPEATED_FAILURE"
        return "PAUSE_RESOURCE_BUDGET_EXHAUSTED" if total >= cycle_max else None

    cycle, receipts = state.get("repair_cycle_attempts"), state.get("repair_cycle_log")
    if type(cycle) is not int or cycle < 0 or issue > cycle:
        return "INVALID_REPAIR_COUNTER"
    if not isinstance(receipts, list):
        return "INVALID_REPAIR_RENEWAL"
    if not nonempty(state.get("repair_renewal_authority")):
        return "PAUSE_REPAIR_RENEWAL_AUTHORITY"
    if cycle and not nonempty(state.get("issue_fingerprint")):
        return "INVALID_REPAIR_RENEWAL"
    archived, approaches = 0, set()
    for index, receipt in enumerate(receipts, 1):
        if not isinstance(receipt, dict):
            return "INVALID_REPAIR_RENEWAL"
        if not all(nonempty(receipt.get(k)) for k in (
                "task_id", "scope_fingerprint", "issue_fingerprint", "reason",
                "diagnosis", "next_approach", "evidence", "authority_evidence", "recorded_at")):
            return "INVALID_REPAIR_RENEWAL"
        numbers = [receipt.get(k) for k in ("cycle_id", "cycle_attempts", "issue_attempts", "total_repair_attempts")]
        if any(type(v) is not int for v in numbers):
            return "INVALID_REPAIR_RENEWAL"
        cycle_id, spent, issue_spent, running_total = numbers
        if (cycle_id != index or receipt["task_id"] != state["task_id"] or
                not 1 <= spent <= cycle_max or not 0 <= issue_spent <= min(issue_max, spent)):
            return "INVALID_REPAIR_RENEWAL"
        archived += spent
        if running_total != archived:
            return "INVALID_REPAIR_RENEWAL"
        signature = tuple(receipt[k].strip() for k in
                          ("issue_fingerprint", "diagnosis", "next_approach", "evidence"))
        if signature in approaches:
            return "PAUSE_REPAIR_STALLED"
        approaches.add(signature)
    if archived + cycle != total:
        return "INVALID_REPAIR_COUNTER"
    if issue >= issue_max or cycle >= cycle_max:
        return "REVIEW_REPAIR_CYCLE"
    return None


def renew_cycle(state, *, current_task_id, current_scope_fingerprint,
                current_model, model_roles, reason, diagnosis, next_approach, evidence,
                runtime_evidence=None, capability_evidence=None, routing_policy=None,
                delegation_authorized=False, delegation_evidence=None,
                user_override=None, require_model_routing=False):
    """Return a validated copy; history, lifetime totals and scope stay intact."""
    from validate_run_state import assess_state

    if not isinstance(state, dict) or state.get("repair_budget_mode") != "RENEWABLE":
        raise ValueError("Renewal requires an explicitly recorded RENEWABLE run")
    context = dict(current_task_id=current_task_id,
                   current_scope_fingerprint=current_scope_fingerprint,
                   current_model=current_model, model_roles=model_roles,
                   runtime_evidence=runtime_evidence, capability_evidence=capability_evidence,
                   routing_policy=routing_policy, delegation_authorized=delegation_authorized,
                   delegation_evidence=delegation_evidence, user_override=user_override,
                   require_model_routing=require_model_routing)
    decision = assess_state(state, **context)["decision"]
    if decision not in ("REVIEW_REPAIR_CYCLE", "REPAIR_WITHIN_SCOPE", "CONTINUE_EXECUTE"):
        raise ValueError("Cannot renew: " + decision)
    if state["workflow_stage"] != "EXECUTE" or state["repair_cycle_attempts"] < 1:
        raise ValueError("Renewal requires an executed repair cycle")
    if assess_state(state, completion=True, **context)["decision"] == "COMPLETE_READY":
        raise ValueError("Required target already achieved; close without another renewal")
    if any(not nonempty(v) for v in (reason, diagnosis, next_approach, evidence)):
        raise ValueError("Renewal needs reason, diagnosis, next approach and progress or new evidence")
    updated = copy.deepcopy(state)
    updated["repair_cycle_log"].append({
        "cycle_id": len(updated["repair_cycle_log"]) + 1,
        "task_id": current_task_id, "scope_fingerprint": current_scope_fingerprint,
        "issue_fingerprint": updated["issue_fingerprint"],
        "cycle_attempts": updated["repair_cycle_attempts"],
        "issue_attempts": updated["repair_attempts"],
        "total_repair_attempts": updated["total_repair_attempts"],
        "reason": reason, "diagnosis": diagnosis, "next_approach": next_approach,
        "evidence": evidence, "authority_evidence": updated["repair_renewal_authority"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    updated["repair_attempts"] = 0
    updated["repair_cycle_attempts"] = 0
    decision = assess_state(updated, **context)["decision"]
    if decision not in ("CONTINUE_EXECUTE", "REPAIR_WITHIN_SCOPE"):
        raise ValueError("Invalid renewed cycle: " + decision)
    return updated
