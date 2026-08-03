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

## [0.1.0] - 2026-08-03

### Added

- Analyze → Refine → Execute workflow with explicit approval and stage-exit
  contracts.
- Conservative Sol/Terra role policy and declared-payload `PreToolUse` guard.
- Single-writer staging, compare-and-swap integration, stable revision seals,
  and revision-bound audit receipts.
- Four installable Skills, portable validators, safe dry-run installer, public
  release auditor, examples, and macOS/Linux CI.
