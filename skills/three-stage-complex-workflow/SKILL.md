---
name: three-stage-complex-workflow
description: "Requested three-stage tasks: compare three detailed alternatives, refine the selected plan, then execute with MANUAL approvals or explicit BOUNDED_AUTO authority."
---

# Three-Stage Complex Workflow

Use three decision boundaries to deliver an authorized result. Give the user
three detailed, meaningfully different alternatives before selecting a plan.
This skill governs task identity, scope, approval and completion; it does not
require a fixed implementation recipe. Stage leads follow the model defaults below.

## Activate only for the intended task

- An explicit `$three-stage-complex-workflow` task starts in `MANUAL` unless
  the user authorizes autonomous progression.
- A concrete three-stage request with “自动完成”, “自动推进”, “全自主” or
  equivalent language starts in `BOUNDED_AUTO`. For example:
  `请你完善这个图,直到通过,自动完成3阶段工作流`.
- Resume only a verifiable `ACTIVE` run with matching nonempty `task_id` and
  `current_task_id`, valid stage and intact mode-specific authority.
- Complexity, multiple files, an explanation of this workflow, or a request to
  audit/edit the skill does not itself activate the state machine. A separate
  applicable task authorization may explicitly select this workflow.

Explicit opt-out and meta intent take precedence over token matches.
Read requests for meaning; regression phrase matching is a diagnostic aid, not
proof of user authorization. A closed run stays closed. A newly authorized
follow-up can reuse relevant decisions and evidence in a new bounded record.

## Keep one authoritative record

Record the objective, task identity, stage, mode, selected option, exact change
scope, user authorization, scope fingerprint, acceptance gates and repair budget.
Use an existing task ledger when available. A short in-session task may keep
these facts in the conversation; resumable or consequential work benefits from
one task-owned state file. Do not create parallel copies of the same plan,
approval and status solely to fill templates.

Read [the state contract](references/state-contract.md) when persisting,
resuming, recovering or mechanically validating a run. It defines the fields,
`AcceptanceGate`, `AutoTransitionReceipt`, and `StageExitContract`, including
scope drift and receipt recovery. Missing authority is never inferred from a
schema, a test result or the apparent usefulness of the next action.

## Route the actual stage lead

For new runs, default ANALYZE (investigation and design) and REFINE to
`gpt-6-astra`; default EXECUTE to `gpt-6.1-sol`. Explicit user model instructions
with recorded evidence override these preferences. Read
`three-stage-runtime-v1.json` and use `scripts/model_routing.py`; new records
require `workflow_policy_version: "2.1.0"` and `model_routing`.

Root coordination is distinct from the stage lead. Observe the actual root
model; never claim that policy text switches it. When the selected model differs,
use an authorized available delegation tool and record the actual stage lead.
Without delegation authority, a supported model, task capability evidence or
verified identity, pause with the specific missing requirement; never silently
fall back. Existing records without routing/version markers keep legacy semantics.

Subagent models have no fixed allowlist: select full model IDs from current
runtime availability and a separate task capability assessment. Static
`model_roles` only supports legacy/current-root compatibility. A model name or
runtime tool listing grants no role, stage, write scope or delegation authority.
ANALYZE and REFINE stay read-only. Root is the sole canonical integrator, with at
most one active writer. Automatic stage progression does not authorize subagents
or delegation. Use [the composition contract](references/composition-contract.md)
for evidence schemas, actual handoff and specialist methods.

## Analyze — make the decision ready

Begin with `【分析问题】`. Establish the requested outcome, current evidence,
inputs, host/project, constraints and observable acceptance criteria. Read enough
context to distinguish the cause from the symptom and identify consequential
unknowns. Do not mutate implementation files or install dependencies.

Read [stage-deliverables.md](references/stage-deliverables.md) for the required
analysis and refinement detail. Present **exactly three numbered alternatives**
with concrete mechanisms, affected files/components, benefits, drawbacks,
complexity, performance, scalability, invasiveness, maintenance cost, validation
and fit. Give a full explanation of each, then a comparison table and a reasoned
recommendation. Names, scores or a terse table alone do not support selection.
Do not fabricate feasibility, measured gains or superficial alternatives; label
conditional or rejected paths honestly. Reuse verified context, but complete
this comparison when a new decision is requested. An already selected, unchanged
plan can resume its recorded stage without reopening the same decision.

Ask only about missing facts that change the decision or authority. Continue
independent useful work while awaiting an answer. End planning when the decision
is supported; additional investigation needs a named uncertainty that could
change the next action, rather than a fixed number of research passes.

Exit with the selected recommendation, remaining limits and enough evidence to
refine. `MANUAL` waits for the user's selection. `BOUNDED_AUTO` records
`AUTO_REFINE` within its authority envelope and continues.

## Refine — make execution reviewable

Begin with `【细化方案】` only after mode-appropriate selection. List every planned
new, changed or deleted file with its core change in pseudocode or detailed prose.
Define changed function signatures, interfaces and data structures where applicable.
Specify dependencies, sequencing, failure handling, backups, rollback and concrete
test cases/acceptance. Name any task-owned temporary test directory and its cleanup
plan. Use [stage-deliverables.md](references/stage-deliverables.md); a file list
without per-file behavior is insufficient. Do not generate complete runnable code.

Keep implementation details flexible inside this contract. Record bounded
assumptions, and classify discovered issues as in-scope blockers, non-blockers
or out-of-scope findings. Reopen only decisions affected by material evidence.
Do not write implementation code in Refine; an authorized task-owned planning
record is permitted. Do not generate unneeded dashboards, reports or ledgers.

Exit when files, authority and acceptance are ready. `MANUAL` waits for approval
of this scope. `BOUNDED_AUTO` records `AUTO_EXECUTE` bound to the current scope.
ANALYZE must not jump directly to EXECUTE. Existing valid approval is reused;
internal receipt refresh or an unchanged plan does not require duplicate approval.

## Execute — deliver the verified outcome

Begin with `【执行方案】`. Check current files, user edits, task identity and
scope against the approved contract before material writes. Preserve originals,
use recoverable changes and reuse the project's existing environment.
Never install globally.
For Python, use the designated isolated environment; if none exists, plan and
create a project-local `venv` during Execute and use its interpreter or activate it
for each shell session. For Node.js, check the package manager, manifest and lock
file, then install missing declared dependencies in the approved project environment.
Do not rebuild a working environment or change dependency versions merely because
the stage began. Project execution, dependency, build and test commands belong in
the designated environment; read-only host/environment discovery is permitted.
Do not start a development server without a separate explicit user request.

Implement coherent deliverables inside the approved scope. Choose effective
local methods without expanding the goal. Report meaningful progress: what is
known, what remains uncertain and what the next check resolves. Do not repeatedly
dump state fields, complete plans or tool logs into the conversation.

Run the checks relevant to changed behavior and required project acceptance.
Discover established QA commands from applicable manifests, Makefile, CI or
contribution docs: formatting/style, lint/static analysis, configured type checks,
unit/integration tests and planned temporary checks. Run the applicable configured
checks, report each result, and distinguish unconfigured checks from checks not run.
Do not invent a new QA toolchain to fill a category.
Reuse evidence only while its input versions, relevant files, environment and
assumptions remain applicable. After changes, rerun affected checks. Inspect the
actual final artifact; exports, process IDs or static checks alone do not prove
scientific validity, correct rendering or successful publication.

In MANUAL, a failed executed check pauses dependent execution for a failure report
and the user's next decision; do not claim completion or submit failing code.
In BOUNDED_AUTO, repair verified in-scope failures and preserve their evidence.
A repair attempt
counts after an attempted correction of a demonstrated problem, not initial
implementation, routine validation or a progress update. Keep the same issue
fingerprint across equivalent failures. New runs default to `RENEWABLE` repair
budgets: three repairs for one issue or six in a cycle trigger a review and
evidence-backed cycle renewal, rather than automatic termination of the task.
Record diagnosis, the next approach and progress or new evidence before resetting
cycle counters; lifetime totals and failure history never reset. Continue within
unchanged authority until required acceptance passes, without a fixed renewal
count ceiling. Stop identical retries that add no evidence or method, and respect
actual resource limits and any smaller user-set fixed budget. Read
[the repair policy](references/repair-policy.md) for counters and renewal receipts.
Legacy records without an explicit repair mode retain `FIXED` limits; do not
silently migrate active runs or reopen closed tasks.
Scope drift returns only affected work to planning and requires refreshed scope
and transition evidence before dependent writes.

Stop the affected action for missing authority, destructive/irreversible changes,
raw-data or key-result overwrite, out-of-scope writes, credential/security or
global-environment changes, scientific evidence conflict, unverifiable required
acceptance, or model-role unavailability. Preserve completed work and report the
specific evidence and smallest missing decision. Do not turn an optional check
or an unrelated issue into a universal blocker.

Do not commit or push, send external messages, upload data, enable plugins,
delegate, or expand environments merely because this workflow is active.
Those actions need applicable independent task authority. Do not weaken a gate
to obtain PASS. “直到通过” means the required gates are met within scope and
budget, with evidence current for the delivered version.

Before presenting a stage result, perform the applicable critical self-checks in
`references/stage-deliverables.md`. Correct uncovered gaps or state the specific
unresolved limitation; never invent certainty or record hidden chain-of-thought.
In MANUAL, open each stage response with its marker, do only that stage, and wait
for explicit selection/approval before the next response advances. A recommendation
is not selection, and selection is not execution approval. In BOUNDED_AUTO, display
each marker at stage entry and continue within the same task under its authority;
still present the three alternatives and selected rationale before refining.
Completion reports state the outcome,
scope, meaningful checks and limitations; internal bookkeeping stays in the
authoritative record. Create temporary tests only in an exclusive task-owned
directory such as `temp_tests/<task_id>/`; after applicable checks pass, remove
that directory and verify removal. Never delete a shared/pre-existing temp_tests
directory, permanent regression tests or unrelated files. Preserve failure evidence
and unfinished test material when checks fail. Close the run only when the required
deliverable, applicable gates and planned cleanup are complete.

## Maintain this skill

After changing this skill, run `python3 scripts/validate_bundle.py` from its
directory or invoke that script by absolute path. Read
[the validation guide](references/validation-guide.md) for real-state checks and
their limits. Read [the persistence policy](references/persistence-policy.md)
only when a durable decision record would help continuation.
