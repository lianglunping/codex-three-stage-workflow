# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Changed

- Three-stage routing is now activated only by an explicit
  `$three-stage-complex-workflow` invocation or a verifiable active run; ordinary
  tasks retain normal file and agent-dispatch access.
- The Sol/Terra role policy is scoped to active three-stage runs. The declared
  payload write guard is optional strict-session defense in depth, is no longer
  recommended as a global hook, and permits Sol-to-Terra handoff.
- v0.1.0 upgraders must remove only the manually merged global Guard
  `PreToolUse` block from their user `hooks.json`, preserve other hooks, and
  restart Codex before opening a new session. The installed script remains the
  optional strict-session component.

## [0.2.0] - 2026-11-05

### Changed

- Export the current generic workflow and companion coordination components.
- Add MANUAL and explicitly authorized BOUNDED_AUTO modes, exactly three detailed
  alternatives, per-file refinement, structured acceptance gates and transitions.
- Ship workflow policy 2.1.0 with evidence-based stage-lead routing (Astra for
  Analyze/Refine, Sol for Execute), explicit overrides and dynamic child models.
- Add real JSON-state, model-routing and renewable repair-cycle validators/tests;
  retain legacy fixed-budget and compatibility semantics for old records.
- Validate a disposable installation without reading personal Codex configuration;
  policy consumers honor CODEX_HOME for isolated installations.
- Carry dynamic model evidence through registry, manifest and audit-receipt checks;
  reject missing or changed evidence instead of reverting to the static model table.
- Update English/Chinese usage, architecture, installation and security guidance.

### Removed

- Retire the old Sol/Terra-only strict hook and its installation example because
  it cannot implement the current stage and authority contract. Existing hook
  configuration is never edited automatically; see installation migration notes.

## [0.1.0] - 2026-08-03

### Added

- Analyze → Refine → Execute workflow with explicit approval and stage-exit
  contracts.
- Conservative Sol/Terra role policy and declared-payload `PreToolUse` guard.
- Single-writer staging, compare-and-swap integration, stable revision seals,
  and revision-bound audit receipts.
- Four installable Skills, portable validators, safe dry-run installer, public
  release auditor, examples, and macOS/Linux CI.
