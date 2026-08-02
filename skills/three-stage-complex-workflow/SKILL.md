---
name: three-stage-complex-workflow
description: >-
  Use when work is PLAN_REQUIRED, spans multiple files or components, changes an
  architecture or public contract, is conclusion-sensitive or hard to reverse,
  has substantive competing approaches, resumes an approved complex plan, or is
  explicitly invoked. Do not use for simple Q&A, routine status checks, small
  unambiguous edits, or observation of an already-running job.
---

# Three-Stage Complex Workflow

Govern stage, approval, and scope transitions. Let specialist skills own domain
methods and execution mechanics.

## Route the Task

Classify the current request before acting:

- `SIMPLE`: use the ordinary `READ_ONLY`, `DIAGNOSE`, `DIRECT_CHANGE`, or
  `MONITOR` route.
- `COMPLEX_NEW`: enter `ANALYZE`.
- `RESUME_APPROVED`: reconstruct approval evidence and resume the matching
  stage without repeating completed approvals.

Treat a task as complex when one or more of these materially applies:

- multiple files, modules, systems, hosts, or execution stages;
- architecture, shared interfaces, schemas, data models, or release contracts;
- scientific assumptions or design choices that can change conclusions;
- destructive, difficult-to-reverse, externally visible, costly, or new
  long-running actions;
- two or more genuinely different approaches with meaningful tradeoffs;
- explicit invocation of `$three-stage-complex-workflow`.

Do not inflate a task merely because it is technical. A bounded, reversible edit
with an obvious implementation remains `DIRECT_CHANGE`. A complex read-only
audit or diagnosis may stop after Analyze and does not authorize a fix. Ongoing
observation, failure classification, or bounded recovery of an already-running
job belongs to `job-monitor-loop`, not a fresh three-stage cycle.

## Track Task-Scoped State

Track this minimum logical state in conversation or in an approved plan:

```text
WorkflowState {
    task_id: string | null
    workflow_stage: ANALYZE | REFINE | EXECUTE
    selected_option: string | null
    approved_scope: string | null
    approval_evidence: string | null
    scope_fingerprint: string | null
}
```

- Derive `task_id` from the current objective and deliverable; do not confuse an
  unrelated new request with a follow-up to the active task.
- Summarize `approved_scope` with exact files, outputs, environment, safety
  boundaries, and exclusions when available.
- Record `approval_evidence` as the user's unambiguous statement or an auditable
  approved-plan reference. Never invent approval.
- Use `scope_fingerprint` as a canonical summary or digest of the approved files,
  outputs, environment, risks, and authority. It need not be cryptographic or
  written to disk.
- Reconstruct missing state from conversation, plans, status files, and current
  user intent. Ask only when a missing fact would change authority or validity.

If the user replaces the objective, classify a new task. If the user asks an
unrelated simple question while a complex task exists, answer it through the
ordinary route without silently changing the complex task's state.

## Enforce Transitions

```text
COMPLEX_NEW                                     -> ANALYZE
ANALYZE + explicit option selection             -> REFINE
REFINE + explicit implementation approval       -> EXECUTE
approved plan + current execute request          -> EXECUTE
material scope, risk, input, or authority drift  -> affected planning stage
```

Start every user-visible response for the active complex task with exactly one
current marker: `【分析问题】`, `【细化方案】`, or `【执行方案】`. Keep progress
updates in the same stage. Complete no more than one stage in one assistant turn.

Accept statements such as “用方案1”, “就这么做”, “按这个计划”, or “执行” as
approval only when their target is unambiguous. Accept an approved plan whose
scope matches observed state. Do not demand duplicate approval because a new
conversation began.

Return only the affected part to planning when new evidence materially changes
the selected design, files, outputs, environment, risk, or required authority.
Do not reset the workflow for a local implementation failure that remains inside
the approved scope.

## Route Models by Responsibility

Model routing is a preferred capability assignment, not a source of authority:

| Stage | Preferred model | Allowed responsibility | Exit artifact |
|---|---|---|---|
| `ANALYZE` | `gpt-5.6-sol` | read-only evidence synthesis and option comparison | decision-ready analysis |
| `REFINE` | `gpt-5.6-sol` | bounded plan refinement | execution-ready file and gate contract |
| `EXECUTE` | `gpt-5.6-terra` | implementation, tests, and repair inside approved scope | verified deliverables and receipts |

If the preferred model is unavailable, keep the same responsibility boundary;
never treat a fallback model as added authority. `gpt-5.6-sol` must not hold
canonical write permission, act as `CANONICAL_INTEGRATOR`, or continue into
execution because its plan appears obvious. In Execute, `gpt-5.6-terra` may
write only within the approved assignment scope; the root integrator remains the
only canonical writer when parallel agents are used.

## Stop Planning Loops

Analyze and Refine are decision stages, not open-ended research loops. Use one
broad evidence pass and at most one targeted gap-closing pass. A further pass is
allowed only for a named blocking unknown whose answer can change the selected
option, authority, or acceptance gate.

Classify every newly discovered issue as `IN_SCOPE_BLOCKER`,
`IN_SCOPE_NONBLOCKER`, or `OUT_OF_SCOPE`. Only `IN_SCOPE_BLOCKER` extends the
current stage. Record non-blockers once and do not recursively expand them.
When the same issue fingerprint recurs without new evidence, stop rechecking it
and report the unresolved condition once.

Before leaving Analyze or Refine, fill this logical exit contract:

```text
StageExitContract {
    evidence_sufficiency: SUFFICIENT | INSUFFICIENT
    blocking_unknowns: string[]
    deliverable_complete: true | false
    next_action: REQUEST_SELECTION | REQUEST_EXECUTION_APPROVAL | EXECUTE
    stop_reason: string
}
```

Exit the stage as soon as the deliverable is complete and no blocking unknown
remains. Do not add details merely to consume context, reopen an already resolved
choice, or self-approve the next stage.

## Analyze

Begin with `【分析问题】`.

1. Establish the core objective, deliverable, scope, acceptance criteria, host,
   project root, nearest instructions, environment, and safety boundary.
2. Read relevant code, configuration, documentation, tests, logs, data contracts,
   and prior plans with read-only tools.
3. Distinguish root cause from symptoms and assess upstream, downstream, API,
   data, release, and scientific-conclusion impacts.
4. Classify missing information as blocking, important, or optional. Ask only
   blocking questions; state bounded assumptions for the rest.
5. Offer one to three substantively different solutions. Do not manufacture weak
   alternatives to fill a quota.
6. Compare correctness, evidence, complexity, performance, extensibility,
   intrusion, rollback, maintenance, and technical debt. Prefer KISS and DRY
   without sacrificing validity.
7. Recommend one solution and request explicit selection.

Stop when the decision-ready analysis and `StageExitContract` are complete. Do
not audit implementation details that cannot affect option selection.

Do not modify files, install dependencies, run mutating commands, or implement a
solution in Analyze.

Before presenting the result, internally verify that the alternatives are not a
literal restatement, the root cause is supported, the recommendation is not a
shortcut, and the design is not over-engineered. Present concise evidence and
decision rationale, not private chain-of-thought.

## Refine

Enter only after explicit selection. Begin with `【细化方案】`.

1. List every file or artifact to add, modify, retire, or delete using exact
   paths. Identify backups and rollback artifacts.
2. Describe each file's responsibility and core change with pseudocode or
   detailed prose.
3. Define changed function signatures, class or command interfaces, schemas,
   state values, and data structures. State explicitly when none change.
4. Specify stage order, dependencies, error handling, edge cases, side effects,
   and rollback conditions.
5. Plan applicable formatting, linting, static analysis, type checks, unit and
   integration tests, semantic QA, and artifact checks.
6. Name any task-specific temporary test directory. Remove it only after all
   planned checks pass; retain evidence and report if checks fail.
7. Identify the highest-risk change and define its acceptance gate.
8. Request explicit approval to execute.

Stop when the file/interface/gate contract and `StageExitContract` are complete.
Do not begin implementation, simulate implementation repeatedly, or refine the
same accepted detail without new evidence.

Do not write runnable implementation code or mutate project implementation files
in Refine. Create a versioned planning or decision artifact only when explicitly
authorized or the selected workflow already requires it.

Before presenting the result, internally verify completeness, boundary and
failure coverage, testability, rollback, and minimum intrusion.

## Execute

Enter only after explicit approval or valid approved-plan evidence. Begin with
`【执行方案】`.

1. Re-read the approved scope, nearest project rules, current files, locks, and
   intervening changes. Recompute the scope fingerprint before material writes.
   Inspect the current unique deliverable, authoritative task ledger, valid completion
   evidence, and running assignments; stop a later overlapping path instead of
   duplicating execution, review, build, or sign-off.
2. Discover and reuse the project's existing environment mechanism: conda,
   mamba, venv, uv, Poetry, containers, modules, or the package manager and lock
   files already in use. Create, rebuild, install, or upgrade only when no
   suitable environment exists and the approved scope authorizes it. Never
   install globally.
3. Back up unversioned persistent control files when rollback would otherwise be
   difficult. Preserve unrelated user changes.
4. Implement only the approved files and behavior. Apply YAGNI, KISS, and DRY.
5. Place planned temporary validation code only in the named task-specific
   temporary directory.
6. Discover QA commands from configuration, CI, contribution guides, and
   existing scripts. Run applicable format, lint, static, type, unit,
   integration, semantic, manifest, checksum, and input-immutability checks.
7. If a check fails, stop the affected delivery path, preserve evidence, report
   the exact failure and impact, and repair only inside approved scope. Do not
   claim completion while a required gate fails.
8. Remove the task-specific temporary test directory only after all required
   checks pass, then verify that it no longer exists.
9. Report changed artifacts, checks and outcomes, residual risks, and any next
   action.

Use `gpt-5.6-terra` for scoped implementation work. If parallel agents are
needed, apply the assignment, staging, single-integrator, revision-seal, and
audit-receipt contract from `dispatching-parallel-agents` and
`staged-agent-run-protocol`.

Do not commit or push, start a development server, send external messages,
upload sensitive data, or add out-of-scope features unless explicitly requested.

Before reporting completion, internally verify readability, project consistency,
absence of avoidable technical debt, environment cleanliness, and no silent
regression in security, performance, accessibility, data integrity, or
scientific claim strength.

## Compose with Specialist Skills

Apply this precedence: this skill owns stage, approval, task identity, and scope
transitions; a specialist skill owns only its method inside the current stage.

- Use `multi-agent-bioinformatics-planner` inside Analyze and Refine for
  conclusion-sensitive scientific planning. It does not authorize execution.
- Use `orchestrate-chatgpt-pro-development` inside the appropriate stage for
  complex coding when it otherwise triggers. Its external proposal or generated
  code does not count as user selection or approval.
- Use `writing-plans` only as a Refine-stage plan format and `executing-plans`
  only after entering Execute. Ignore any default commit, subagent, worktree, or
  execution behavior that conflicts with user authority or higher-priority
  instructions.
- Use `staged-agent-run-protocol` inside Execute for an approved auditable
  research run. It owns run control, provenance, host and environment registry,
  QC gates, and frozen outputs.
- Use `job-monitor-loop` for already-running job supervision and bounded
  recovery. Monitoring authority does not authorize redesign.
- Use `project-audit` for audit evidence and semantic acceptance. Audit remains
  read-only unless the user also requests change.

## Validate the Contract

Machine-enforced runtime policy is `<CODEX_HOME>/policies/three-stage-runtime-v1.json`.
It supplements this Skill: Sol is read-only, Terra is the canonical
Execute integrator, and the hook has only declared-payload coverage.

After installing, changing, or auditing this skill, run the bundled read-only
validator against the installed Skill, nearest global routing file, and curated
regression cases:

```text
python3 scripts/validate_workflow_contract.py \
  --skill-root <skill-root> \
  --agents <global-AGENTS.md> \
  --cases <skill-root>/references/regression_cases.tsv
```

Also run the system `skill-creator` `quick_validate.py`. For a substantive
revision, create task-owned temporary copies and confirm that removing a stage
marker, drifting the global Skill name, introducing an unapproved transition, or
removing the global-install prohibition produces a nonzero validator exit. Do
not edit live files to perform negative tests.

## Persist Decision Rationale

When a reasoning summary exceeds 300 Chinese characters and will materially help
future sessions, proactively propose a durable record using this exact sentence:

```text
This reasoning is valuable for future sessions. I'll write it to `[path]`.
```

Resolve destinations from the actual project root when applicable:

- audit or review decision over 500 characters:
  `plans/学位论文/audit_{topic}_{YYYYMMDD}.md`;
- overturned conclusion or a conclusion changed over at least two rounds:
  `{analysis_dir}/{topic}_evolution.md`;
- quantitative literature-method analysis:
  `{analysis_dir}/literature_{author}_{year}_analysis.md`;
- A-versus-B decision rationale: use a task-owned project-local decision log
  only when the approved scope includes it.

If a listed directory is not part of the current project, propose a project-local
equivalent instead of creating a foreign hierarchy. Record the question,
evidence, decision, rejected alternatives, assumptions, and implications as a
concise auditable rationale. Never record hidden chain-of-thought. The proposal
alone does not authorize a write; write only after explicit approval or when the
approved plan already includes that artifact. Do not duplicate a rationale
already captured in an authoritative plan or rule.
