# Validation Guide

Read after changing the skill or when validating an actual persisted run.

## Bundle maintenance

Run from any working directory:

```text
PYTHONDONTWRITEBYTECODE=1 python3 <skill-root>/scripts/validate_bundle.py
```

The bundle checks direct reference links, stable stage/authority interfaces,
48 routing cases, 18 legacy state summaries, 30 coordination cases, current-model
compatibility, actual JSON-state behavior, Python syntax, policy JSON and UI
metadata. Test counts can grow; they are not acceptance targets. The retained
400-line core budget is a local maintenance guard, not a product context limit.
Routing fixtures explicitly supply `gpt-6.1-sol` as their test runtime;
compatibility tests also exercise `gpt-5.6-sol` and `gpt-6-astra`. Production callers must supply
the actual current model, never select a policy entry as a runtime fallback.

When PyYAML is available in an existing or isolated environment, also run:

```text
python3 <skill-creator-root>/scripts/quick_validate.py <skill-root>
```

Do not install a global dependency just to run a validator. A failed required
check needs repair; a missing optional dependency must be reported accurately.

## Actual run readiness and completion

Use the fields in [state-contract.md](state-contract.md). Reconstruct the scope
digest from the actual scope contract separately from state.json; verify user
authority, scope membership and evidence authenticity in context. Then run:

```text
python3 <skill-root>/scripts/validate_run_state.py \
  --state <task-run>/state.json \
  --current-task-id <actual-task-id> \
  --scope-fingerprint <independently-computed-digest> \
  --current-model <actual-runtime-model>
```

Add `--completion` after the required gates have evidence and before marking
the run CLOSED. Default policy is `~/.codex/policies/three-stage-runtime-v1.json`;
`--policy` accepts an explicit local policy. Exit 0 means structurally ready to
continue, repair within scope, or close as named by the returned decision.
Nonzero requires the reported recovery, correction or missing decision first.
Read the decision: readiness with PENDING gates does not establish completion.

The checker does not alter records, authenticate approvals, discover arbitrary
scope changes or enforce filesystem access. A fabricated PASS string is not
real evidence. These deterministic tests establish local routing and schema
behavior; they do not measure model task success, latency or context usage.

## Failure regressions

For stage-output maintenance, also review the three alternatives and per-file
refinement requirements in [stage-deliverables.md](stage-deliverables.md). Static
link/schema tests cannot establish that a future agent produces sufficiently
distinct or detailed options. Use realistic author scenario review or an explicitly
authorized independent run, and report which level was actually performed.

The bundle exercises missing authority, task/scope mismatch, unknown models,
direct ANALYZE → EXECUTE jumps, stale/discontinuous receipts, missing references,
invalid gate types, empty PASS evidence, duplicate gates, fractional/Boolean
repair counters, exhausted budgets, optional-check failures and closed runs.
MANUAL failures pause for the user's decision; BOUNDED_AUTO retains bounded repair
and optional-check semantics. Exercise both modes when modifying this distinction.
CLI tests verify both success and nonzero rejection of malformed input.
Renewable-budget tests exercise multiple cycles beyond the old total cap,
append-only history, stalled identical renewals, legacy fixed budgets, authority
and scope rejection, and completion at a cycle threshold.

Use in-memory fixtures or task-owned temporary copies; never break live source
files for a negative test. Add tests for changed behavior and affected acceptance,
not for arbitrary exact prose. Remove task-owned temporary checks after required
verification passes; retain permanent regression tests and concise evidence.

## Stage model routing and dynamic assignments

`validate_bundle.py` runs `test_model_routing.py` as well as the historical
48 prompt-route diagnostics. Historical cases intentionally test legacy current
model compatibility; they do not establish new-run stage lead readiness.

For new records, run `validate_run_state.py --state <state.json>
--current-task-id <id> --scope-fingerprint <digest> --current-model <observed-root>
--runtime-evidence <runtime.json> --capability-evidence <capabilities.json>
--require-model-routing`, adding separate `--delegation-authorized
--delegation-evidence <human-authorization-reference>` when needed. Pass
`--user-override <reviewed-override.json>` only for explicit applicable user model
instructions. `model_routing.py` accepts these evidence and authority options,
`--policy <policy.json>` and `--stage ANALYZE|REFINE|EXECUTE` for pre-dispatch
resolution. Neither checker creates agents or changes the root model.

Dynamic registry registration uses `register_agent_assignment.py
--runtime-evidence <runtime.json> --capability-evidence <capabilities.json>
--workflow-stage <stage> --delegation-authorized
--delegation-evidence <human-authorization-reference>` plus the existing bounded
assignment arguments. Evidence paths and SHA256 hashes are retained in registry
notes. Role, stage, root-only integration, staging scope and one-writer checks
still apply. Missing evidence fails closed rather than consulting static fallback.
