# Renewable Repair Policy

Read during run creation, recovery or repair-cycle renewal. This is a local user
preference, not an OpenAI-prescribed retry count. Keep the core instructions short;
load this schema only when a run needs durable repair bookkeeping.

## Modes and authority

New runs default to `repair_budget_mode: "RENEWABLE"`. A user-set fixed limit uses
`FIXED`. An absent mode means legacy FIXED semantics; never silently migrate an
active record or restart a closed task. A migration needs applicable user renewal
authority and an initial receipt accounting for all already spent repairs.

MANUAL stage and failed-check approval boundaries still apply. BOUNDED_AUTO may
renew internally under the original task authority and this configured renewal
preference; do not ask the user to approve an unchanged scope again. Record the
actual renewal instruction or its verifiable reference in `repair_renewal_authority`.

Renewal has no fixed count ceiling. Continue unfinished in-scope work until the
required acceptance gates and deliverable pass. Actual account, tool, cost, time
and user resource limits are independent and cannot be reset by this ledger.
Missing authority, scope drift, destructive actions, scientific conflicts and
unverifiable required acceptance still stop dependent work.

## Counters and renewal

- `repair_attempts`: repairs of the current issue in this cycle.
- `repair_cycle_attempts`: repairs of all issues in this cycle.
- `total_repair_attempts`: lifetime repairs, monotonically increasing.
- `max_repair_attempts`, `max_total_repair_attempts`: review thresholds, normally
  3 per issue and 6 per cycle; smaller user thresholds apply. In FIXED mode the
  latter remains the lifetime limit.
- `issue_fingerprint`: stable identity of the actual failure; preserve it across
  equivalent failures and budget renewals.
- `repair_cycle_log`: append-only array of receipts, initially empty.

At a threshold, `REVIEW_REPAIR_CYCLE` means review and record a next cycle before
further repair writes; it does not require a new user approval in BOUNDED_AUTO.
Inspect the actual failed attempt and saved effects. Identify a revised diagnosis
or approach supported by progress or new evidence. Do not repeat the identical
failed action without useful change. A passed checkpoint may also justify early
renewal; zero-attempt renewals are invalid.

Append a receipt with `cycle_id` (starting at 1), `task_id`, `scope_fingerprint`,
`issue_fingerprint`, `cycle_attempts`, `issue_attempts`, `total_repair_attempts`,
`reason`, `diagnosis`, `next_approach`, `evidence`, `authority_evidence`, and
`recorded_at`. Evidence must identify observed progress or a new diagnostic basis,
not an invented PASS. The receipt seals the spent counts before setting only
`repair_attempts` and `repair_cycle_attempts` to zero. Preserve all failed logs,
acceptance results, scope, authority and lifetime totals.

Every archived cycle's count plus the current cycle must equal the lifetime
total. Reused identical issue/diagnosis/approach/evidence combinations return
`PAUSE_REPAIR_STALLED`; diagnose the missing external input instead of relabeling
the same attempt. Structural checks cannot authenticate progress or prove that
two differently worded approaches are genuinely different; the agent must review
that evidence in context.

## Record helper and validation

`scripts/repair_budget.py` exposes `assess_budget(state)` and
`renew_cycle(state, ..., reason, diagnosis, next_approach, evidence)`. Supply the
actual task ID, independently computed scope fingerprint, runtime model and
policy roles. The helper returns a copy; it does not write files, dispatch work,
grant authority or change the live record. Persist the validated result through
the run's existing authoritative record mechanism.

`scripts/validate_run_state.py` checks this schema. A pending review is a nonzero
result until the internal renewal receipt is recorded. Reaching a threshold never
prevents completion when all required gates already PASS with current evidence;
no new cycle is needed after the target is achieved. A failed or pending gate
cannot become PASS through a budget reset.

Local task repairs are distinct from API request retries. For rate limits and
transient transport failures, inspect saved outcomes and use bounded backoff or
a deadline, as described in [OpenAI recovery guidance](https://developers.openai.com/api/docs/guides/agents-api/errors).
