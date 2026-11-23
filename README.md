# Three-Stage Research Workflow for Codex and DeepSeek Harness

Analyze → Refine → Execute with explicit approvals or task-scoped bounded
autonomy, evidence-based model routing, and verifiable acceptance gates.

[中文说明](docs/README.zh-CN.md) · [Installation](docs/installation.md) ·
[Architecture](docs/architecture.md) · [Security boundary](docs/security-boundary.md)

## Integrated research workflow

Install seven skills for Codex or DeepSeek Harness and merge the corresponding
AGENTS example to enable research intake in new chats. Simple figure edits wait
for one confirmation and route through the figure entry and director. Version
mergers require an inventory, a reviewed candidate and explicit final approval.
The chosen research policy governs how many alternatives merit comparison.
The stage and model defaults below describe the standalone Codex runtime.

## Workflow

Activate with `$three-stage-complex-workflow`, a concrete request to automatically
complete the three-stage workflow, or a verifiable matching ACTIVE run.
Ordinary tasks and maintenance of this workflow do not activate it.

1. **Analyze:** explain exactly three meaningfully different alternatives,
   compare their tradeoffs and recommend one.
2. **Refine:** specify each affected file, interfaces, acceptance and recovery.
3. **Execute:** implement within the approved scope and verify the delivered result.

`MANUAL` is the default: each response advances one stage and waits for the
appropriate user selection or approval. An explicitly authorized `BOUNDED_AUTO`
run advances through all three stages inside its recorded authority envelope.
It still presents the alternatives and refinement before execution. Automatic
progression grants no delegation, plugin, commit, push or external-send authority.

New-run policy `2.1.0` defaults to `gpt-6-astra` for Analyze/Refine and
`gpt-6.1-sol` for Execute. These are preferences to resolve against the actual
runtime, not a claim that those models are available on every installation.
Record actual root and stage-lead identity, runtime availability, independent
task capability evidence and any explicit user override. Missing models or
unauthorized handoffs pause without silently substituting another model.

## Included components

- `three-stage-complex-workflow`: stage, authority, state, model routing,
  structured acceptance, and renewable repair-cycle validators and tests.
- `staged-agent-run-protocol`: approved research-run records, isolated staging,
  compare-and-swap integration, stable revision seals and audit receipts.
- `dispatching-parallel-agents`: separately authorized assignments and write isolation.
- `project-audit`: evidence-based audit of sealed revisions.
- `academic-figure-skill` → `bio-publication-figure-director` → `bio-reporting-figure-export` for scientific plots, local revisions and artifact review.
- Portable runtime policy, optional read-only custom agent templates, dry-run
  installer, public-boundary auditor and isolated validation suite.

Root is the sole canonical integrator, with at most one active writer. Child
models have no fixed allowlist when current runtime and task capability evidence
support them; stage, role, scope and delegation authority remain separate checks.
New auto runs can renew repair cycles after diagnosis and a changed method or
new evidence; cumulative failure history remains intact. Legacy records retain
their original fixed-budget semantics.

## Quick start

```bash
git clone https://github.com/lianglunping/codex-three-stage-workflow.git
cd codex-three-stage-workflow
python3 scripts/audit_public_release.py .
python3 scripts/validate_all.py

# Preview; no target files are written.
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}"
# Apply after reviewing the preview. Existing target files are backed up.
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}" --apply
```

The installer never edits `AGENTS.md`, `config.toml` or `hooks.json`.
Merge the matching host example to enable daily routing. For DeepSeek Harness use
`python3 scripts/install.py --dsh-home "$HOME/.dsh" --apply`, then merge
`hosts/deepseek/examples/AGENTS.md`. Pair it with the [Harness routing example](hosts/deepseek/examples/research-routing.yml) as described in the installation guide. Validation installs into
a disposable Codex home and uses synthetic fixtures, without reading personal
task records or configuration.

## Upgrade and compatibility

Public package **0.3.0** carries workflow policy **2.1.0**; these version numbers
identify different components. See [the changelog](CHANGELOG.md).

The former Sol/Terra-only strict hook is retired because it cannot represent the
current stage and dynamic-model contract. Remove only its old hook entry if you
previously enabled it, preserving unrelated hooks. The installer does not remove
or alter existing hooks. See [migration instructions](docs/installation.md).

The validation suite uses Python's standard library on macOS/Linux. CI targets
Python 3.9 and 3.13. Windows support is not claimed because the control plane
uses `fcntl`. Model availability and agent configuration must be checked in the
actual host. Specialist skills named in composition guidance are optional and
are not bundled unless listed above.

## Privacy and security

This repository contains generic code, documentation and synthetic fixtures.
It excludes local sessions, credentials, personal instructions, task records,
research inputs/results, logs and installer backups. Validators check declared
state and evidence structure; they do not authenticate approvals or enforce an
operating-system security boundary. Keep host permissions and review in effect.

## License

Apache License 2.0. See [LICENSE](LICENSE).
