# Persisted State Contract

Read when storing, resuming, recovering or validating a dedicated run. Use one
task-owned JSON record; extra project metadata is allowed. A record documents
authority and evidence. It cannot manufacture either or enforce tool permissions.

## Fields and stage readiness

| Field | Contract |
| --- | --- |
| `task_id`, `current_task_id` | Nonempty strings matching each other and the actual current task. |
| `workflow_stage` | `ANALYZE`, `REFINE`, or `EXECUTE`. |
| `run_status` | `ACTIVE` or `CLOSED`; closed records cannot resume. |
| `selected_option` | Nonempty decision from REFINE onward; null is allowed during ANALYZE. |
| `approved_scope` | Precise object or nonempty reference describing files, outputs and exclusions; required for EXECUTE. |
| `approval_evidence` | The actual applicable user statement or verifiable reference, required for EXECUTE and autonomous progression. Never replace it with an invented approval token. |
| `scope_fingerprint` | Nonempty digest of the scope contract, independently reconstructed when checking for drift. |
| `approval_scope_fingerprint` | Must match the current scope at EXECUTE. |
| `autonomy_mode` | `MANUAL` or `BOUNDED_AUTO`. |
| `authority_envelope` | Precise object or nonempty reference for allowed actions and exclusions; required for autonomous progression and EXECUTE. |
| `acceptance_contract` | Array of AcceptanceGate objects; at least one required, executable gate before EXECUTE. |
| `repair_attempts`, `total_repair_attempts` | Nonnegative integers: current issue count and lifetime count. Lifetime totals never reset. Booleans, floats and numeric strings are invalid. |
| `max_repair_attempts`, `max_total_repair_attempts` | Positive integers no larger than 3 and 6: review thresholds for renewable cycles, fixed limits for legacy/FIXED runs. Smaller user limits apply. |
| `repair_budget_mode` | `RENEWABLE` for new runs unless the user sets fixed limits; absent means legacy `FIXED`. |
| `repair_cycle_attempts`, `repair_cycle_log`, `repair_renewal_authority` | Required for RENEWABLE: current-cycle count, append-only renewal receipts and actual renewal authority. See [repair-policy.md](repair-policy.md). |
| `auto_transition_log` | Ordered array of AutoTransitionReceipt objects for BOUNDED_AUTO; may be empty before the first transition or for MANUAL. |

Keep all fields present. Stage-dependent fields may be null or empty until
needed. Additional fields such as timestamps, issue fingerprints and model
observations help provenance but do not override the current runtime identity.

## AcceptanceGate

Each gate has a unique nonempty `gate_id`, nonempty `criterion`,
`verification_method` and `pass_condition`, a Boolean `required`, a `status`
of `PENDING`, `PASS`, `FAIL` or `BLOCKED`, and `evidence`. PASS requires nonempty
evidence. Use artifact paths, measured results or verifiable observations, not
an unsupported assertion that the gate passed.

PENDING can be ready to execute, but is never completed. In BOUNDED_AUTO, an
in-scope required FAIL can be repaired within budget and an optional failure does
not prevent completion. In MANUAL, any executed FAIL pauses dependent execution
with `PAUSE_CHECK_FAILED`, including before completion; report it and obtain the
user's repair decision. After an authorized repair decision, retain the failed
evidence in history and mark the checks to rerun PENDING for the approved repair;
do not simply erase a failure to bypass the pause. A required BLOCKED gate pauses
the affected work in either mode. Reuse PASS evidence
only if the relevant inputs, code, environment and assumptions still match.
Completion requires all required gates to PASS, with the actual deliverable
verified. Structural validation cannot prove a gate's scientific truth.

## StageExitContract and AutoTransitionReceipt

The StageExitContract is the decision evidence at a stage boundary: three detailed,
differentiated alternatives and a mode-appropriate selected approach after ANALYZE;
per-file changes, interfaces, validation cases, environment, cleanup, exact scope
and authority after REFINE; current results, gate evidence and cleanup after
EXECUTE. Use [stage-deliverables.md](stage-deliverables.md) for content requirements.
Keep the comparison or its reference in the existing task record; it is not a new
mandatory JSON field, and these schema checks do not assess proposal quality.

Every autonomous transition receipt contains `from_stage`, `to_stage`,
`exit_contract_status: "PASS"`, `authority_match: true`, `scope_fingerprint`
and nonempty `evidence`. The chronological chain starts at ANALYZE. Forward
transitions are only ANALYZE → REFINE → EXECUTE. Replanning may return EXECUTE
to REFINE or ANALYZE, or REFINE to ANALYZE. Never jump ANALYZE → EXECUTE.
The latest receipt must end at the current stage and match the current scope.
Historical fingerprints can differ after a recorded replan.

For an unchanged approved scope with usable gates, a missing or stale internal
receipt is recovered in REFINE from actual recorded decisions. Do not ask the
user to approve the same scope again, invent missing history, or continue
dependent writes before recovery. Missing user authority remains a real blocker.
Material scope drift returns affected work to planning; update the scope and
bind applicable user authority before dependent execution. Preserve completed
unaffected work and all lifetime repair history. Scope drift does not authorize
budget renewal or erase smaller user-set limits.

## Validation and limits

`scripts/validate_run_state.py` reads the actual JSON schema above and takes
the current task ID, independently computed scope digest and runtime model as
separate arguments. Never pass a state field back as its own purported drift
check. It rejects malformed gates, counters and transition chains; it reports
recovery/repair decisions without editing files. `--completion` additionally
requires EXECUTE and every required gate to PASS before closing the run.

The legacy TSV snapshot tests remain routing/recovery diagnostics. They use
simplified evidence labels and are not the persisted JSON contract. Neither
validator proves user intent, authenticates evidence, detects arbitrary file
changes, assigns a model, or grants filesystem or external-action authority.

## Model routing in new records (policy 2.1.0)

New runs must set `workflow_policy_version: "2.1.0"` and record:

```json
{"model_routing": {"version": 1, "preferred_model": "gpt-6.1-sol",
  "stage_lead": {"agent_path": "/root/execution", "model": "gpt-6.1-sol"}}}
```

`preferred_model` is the policy default for the current stage, even when an
explicit user override changes the selected model. Optional `user_override` is
`{model, evidence}` and must match the independently supplied reviewed override.
Update the current stage lead on stage changes while retaining prior stage and
assignment evidence in the existing authoritative log. Record the observed root
identity separately. The stage lead must match independent runtime `agents` and
the resolved selected model; merely self-reporting a model in state is insufficient.
Runtime availability, task capabilities and delegation authorization come from
independent inputs described in `composition-contract.md`.

`validate_run_state.py --require-model-routing` enforces the new format for run
creation. A routing/version marker also enables these checks automatically.
Unmarked pre-2.1.0 records remain legacy and are not migrated implicitly. This
compatibility path must not be used to create new records. The checker cannot
infer when an unmarked historical record was created; callers creating a run
must supply `--require-model-routing`.
