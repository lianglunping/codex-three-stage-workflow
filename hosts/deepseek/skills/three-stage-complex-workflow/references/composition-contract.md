# Model and Specialist Composition Contract

The core Skill owns task identity, stage, approval, authority and scope. Read
this reference only when composing methods or routing an authorized assignment.

New-run stage defaults in `three-stage-runtime-v1.json` are ANALYZE and REFINE
`deepseek-v4-pro`, EXECUTE `deepseek-v4-pro`. User overrides require explicit applicable
user evidence. Keep the observed root identity and authoritative task record;
root coordination does not establish who actually did a stage's work.

Use `scripts/model_routing.py` before dispatch and `validate_run_state.py` before
continuing. Runtime availability and task suitability are independent inputs:

- Runtime JSON: `source`, `observed_at`, `current_model`, `available_models`
  (full IDs observed in the current tool), `delegation_tool_available` (boolean),
  and `agents` (actual `{agent_path, model}` objects observed after dispatch).
- Capability JSON: `source`, `observed_at`, `models` mapping each assessed full ID
  to task-appropriate capabilities: `planning`, `implementation`, `audit`, or
  `canonical_integration`. This is an explicit reviewer judgment based on task
  requirements and current tool/model evidence; tool listings do not grant roles.
- Delegation authorization: separate CLI `--delegation-authorized` and
  `--delegation-evidence` referencing applicable human authorization. Runtime
  availability and state declarations cannot establish this authority.
- Optional independent user-override JSON: `{model, evidence}` passed with
  `--user-override`; the recorded override must match this reviewed input.

Inputs are structural evidence, not authentication. Inspect their origin and
applicability; never derive them by copying the task state's own assertions.
Reobserve availability after a runtime/session change and reassess capabilities
when the task requirements change. Unavailable selected models, absent capability
assessments, unknown identities, missing tools or unauthorized delegation pause;
there is no silent replacement.

If root differs from the selected lead, pass the compact approved plan, stage,
authority, scope, acceptance gates and evidence paths to that authorized model.
Observe and record its actual identity. Subagent models have no static allowlist;
any full ID supported by runtime and independent task assessment is eligible.
`model_roles` retains legacy compatibility only; new evidence can support a
previously read-only or new model in a suitable child role without broadening
stage, write-scope or delegation authority. Root remains the sole canonical
integrator with at most one active writer; the stage execution lead works in its
assigned staging directory and root integrates after it quiesces.

Choose specialists only for their concrete method: `writing-plans` for plan
format, `executing-plans` for approved implementation,
`staged-agent-run-protocol` for research run records, `job-monitor-loop` for
already-authorized supervision, and `project-audit` for evidence review.
`multi-agent-bioinformatics-planner` can supply scientific planning methods;
its name does not independently authorize delegation.

Use `orchestrate-chatgpt-pro-development` only when the user explicitly
authorized ChatGPT Web Pro collaboration or a matching authorized run is active.
Ordinary complex coding does not trigger an external session. An external plan
or code response is never user approval.

When parallel agents are independently authorized, apply the assignment,
staging, single-integrator, revision-seal and audit-receipt contracts from
`dispatching-parallel-agents` and `staged-agent-run-protocol`.
