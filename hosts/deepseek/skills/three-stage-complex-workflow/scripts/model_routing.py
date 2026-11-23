#!/usr/bin/env python3
"""Stage routing from independent runtime and task-capability evidence.

Evidence is supplied by the caller after observing runtime tools and reviewing
actual task requirements. This structural check cannot authenticate provenance
or confer authority. Never substitute run-state self declarations for evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

STAGE_ROLES = {"ANALYZE": "READ_ONLY_REVIEWER", "REFINE": "READ_ONLY_REVIEWER",
               "EXECUTE": "STAGING_WRITER"}
ROLE_CAPABILITIES = {"READ_ONLY_REVIEWER": "planning", "AUDITOR": "audit",
                     "STAGING_WRITER": "implementation",
                     "CANONICAL_INTEGRATOR": "canonical_integration"}
DEFAULTS = {"ANALYZE": "deepseek-v4-pro", "REFINE": "deepseek-v4-pro", "EXECUTE": "deepseek-v4-pro"}


def present(value):
    return isinstance(value, str) and bool(value.strip())


def validate_routing_policy(policy):
    if not isinstance(policy, dict):
        return ["routing policy must be an object"]
    errors = []
    defaults = policy.get("stage_model_defaults")
    if not isinstance(defaults, dict) or set(defaults) != set(STAGE_ROLES) or not all(present(v) for v in defaults.values()):
        errors.append("stage_model_defaults must define three nonempty full model IDs")
    selection = policy.get("subagent_selection")
    expected = {"mode": "runtime_evidence", "fixed_model_allowlist": False,
                "availability_source": "current_runtime",
                "role_source": "independent_task_capability_assessment",
                "delegation_requires_explicit_authority": True}
    if selection != expected:
        errors.append("subagent_selection must separate availability, task capability and delegation authority")
    return errors


def model_supports_role(model, role, runtime_evidence, capability_evidence):
    """No model-name inference: availability and task suitability are separate."""
    if not present(model) or role not in ROLE_CAPABILITIES:
        return False
    if not isinstance(runtime_evidence, dict) or not isinstance(capability_evidence, dict):
        return False
    if not all(present(e.get(k)) for e in (runtime_evidence, capability_evidence)
               for k in ("source", "observed_at")):
        return False
    available = runtime_evidence.get("available_models")
    assessments = capability_evidence.get("models")
    return (isinstance(available, list) and model in available
            and isinstance(assessments, dict)
            and isinstance(assessments.get(model), list)
            and ROLE_CAPABILITIES[role] in assessments[model])


def resolve_stage(policy, stage, current_model, runtime_evidence, capability_evidence,
                  *, user_override=None, delegation_authorized=False,
                  delegation_evidence=None):
    def out(decision, **details):
        return {"decision": decision, **details}
    if validate_routing_policy(policy):
        return out("INVALID_ROUTING_POLICY")
    if stage not in STAGE_ROLES:
        return out("INVALID_ROUTING_STAGE")
    if not present(current_model):
        return out("PAUSE_CURRENT_MODEL_UNKNOWN")
    if not isinstance(runtime_evidence, dict) or runtime_evidence.get("current_model") != current_model:
        return out("PAUSE_RUNTIME_EVIDENCE", reason="independent root identity must match current_model")
    preferred = policy["stage_model_defaults"][stage]
    selected = preferred
    if user_override is not None:
        if not isinstance(user_override, dict) or not all(present(user_override.get(k)) for k in ("model", "evidence")):
            return out("PAUSE_OVERRIDE_EVIDENCE")
        selected = user_override["model"]
    if not model_supports_role(selected, STAGE_ROLES[stage], runtime_evidence, capability_evidence):
        return out("PAUSE_MODEL_ROLE_UNAVAILABLE", preferred_model=preferred, selected_model=selected)
    delegated = selected != current_model
    if delegated:
        if delegation_authorized is not True or not present(delegation_evidence):
            return out("PAUSE_DELEGATION_UNAUTHORIZED", preferred_model=preferred, selected_model=selected)
        if runtime_evidence.get("delegation_tool_available") is not True:
            return out("PAUSE_DELEGATION_UNAVAILABLE", preferred_model=preferred, selected_model=selected)
    return out("ROUTE_DELEGATE" if delegated else "ROUTE_CURRENT",
               preferred_model=preferred, selected_model=selected, stage=stage)


def validate_stage_assignment(state, policy, current_model, runtime_evidence,
                              capability_evidence, *, delegation_authorized=False,
                              delegation_evidence=None, user_override=None):
    """Bind the recorded lead to independently observed actual agent identity."""
    routing = state.get("model_routing")
    if not isinstance(routing, dict) or routing.get("version") != 1:
        return {"decision": "INVALID_MODEL_ROUTING"}
    # Explicit overrides come from the caller's verified user evidence, not state.
    if routing.get("user_override") != user_override:
        return {"decision": "PAUSE_OVERRIDE_EVIDENCE"}
    route = resolve_stage(policy, state.get("workflow_stage"), current_model,
                          runtime_evidence, capability_evidence, user_override=user_override,
                          delegation_authorized=delegation_authorized,
                          delegation_evidence=delegation_evidence)
    if route["decision"] not in {"ROUTE_CURRENT", "ROUTE_DELEGATE"}:
        return route
    lead = routing.get("stage_lead")
    if not isinstance(lead, dict) or not present(lead.get("agent_path")) or lead.get("model") != route["selected_model"] or routing.get("preferred_model") != route["preferred_model"]:
        return {"decision": "PAUSE_STAGE_LEAD_MISMATCH"}
    agents = runtime_evidence.get("agents")
    if not isinstance(agents, list) or lead not in agents:
        return {"decision": "PAUSE_STAGE_LEAD_UNVERIFIED"}
    is_root = lead["agent_path"] in {"root", "/root"}
    if is_root != (route["decision"] == "ROUTE_CURRENT"):
        return {"decision": "PAUSE_STAGE_LEAD_MISMATCH"}
    return {**route, "stage_lead": lead}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--stage", choices=STAGE_ROLES, required=True)
    parser.add_argument("--current-model", required=True)
    parser.add_argument("--runtime-evidence", type=Path, required=True)
    parser.add_argument("--capability-evidence", type=Path, required=True)
    parser.add_argument("--user-override", type=Path)
    parser.add_argument("--delegation-authorized", action="store_true")
    parser.add_argument("--delegation-evidence")
    args = parser.parse_args()
    try:
        read = lambda p: json.loads(p.read_text(encoding="utf-8"))
        route = resolve_stage(read(args.policy), args.stage, args.current_model,
                              read(args.runtime_evidence), read(args.capability_evidence),
                              user_override=read(args.user_override) if args.user_override else None,
                              delegation_authorized=args.delegation_authorized,
                              delegation_evidence=args.delegation_evidence)
    except (OSError, ValueError, TypeError) as exc:
        route = {"decision": "INVALID_ROUTING_INPUT", "issues": [str(exc)]}
    print(json.dumps(route, ensure_ascii=False, indent=2))
    return 0 if route["decision"] in {"ROUTE_CURRENT", "ROUTE_DELEGATE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
