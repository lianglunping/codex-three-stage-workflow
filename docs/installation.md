# Installation

Use macOS/Linux and Python 3.9 or later; CI targets 3.9 and 3.13. The suite has no
third-party Python dependency. Check model availability and optional custom-agent
configuration in your actual Codex runtime before adopting the templates.

## Inspect, validate and install

```bash
git clone https://github.com/lianglunping/codex-three-stage-workflow.git
cd codex-three-stage-workflow
python3 scripts/audit_public_release.py .
python3 scripts/validate_all.py
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}"
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}" --apply
```

Dry-run is the default. `--apply` copies the four bundled skills, runtime policy
and four optional read-only agent definitions. Existing target files are backed
up under the selected Codex home. The installer rejects the filesystem root
and the user's home directory as targets. It never edits `AGENTS.md`,
`config.toml` or `hooks.json` and never activates agents, hooks or plugins.

Manually merge `examples/AGENTS.md` if you want project routing instructions.
`examples/config.toml` is an optional root-model preference. Installing templates
does not change a running model or authorize delegation. New runs require
policy `2.1.0`, actual model-routing evidence and applicable user authority.

## Upgrade from 0.1.0

1. Finish or preserve any active run before changing its installed runtime.
   Back up its existing workflow and policy; retain the runtime needed to read
   legacy records. This release does not migrate active task records.
2. Review the dry-run, then apply the new package. Public package version
   `0.2.0` is distinct from runtime policy version `2.1.0`.
3. If you enabled the old `three_stage_write_guard.py` hook, remove only that
   entry from your active hook configuration; keep every unrelated hook.
   The old guard hardcodes Sol/Terra rules and does not implement the current
   stage, authority or dynamic-model contract. This release no longer ships it.
   Review the host's hook-trust interface and restart the relevant session to
   reload the changed configuration. The installer leaves existing hooks alone.
4. Merge the updated generic AGENTS instructions. Use `MANUAL` unless the user
   explicitly authorized bounded automatic progression for the specific task.
5. Start new records with `workflow_policy_version: "2.1.0"` and `model_routing`.
   Existing records without those fields retain legacy semantics; old repair
   budgets remain fixed unless explicitly migrated under separate authority.

## Validate an installation

```bash
python3 /path/to/codex-home/skills/three-stage-complex-workflow/scripts/validate_bundle.py \
  --codex-home /path/to/codex-home \
  --agents-skills-root /path/to/codex-home/skills
```

This checks the chosen home's AGENTS instructions, policy and companion skills.
It runs synthetic state, routing and repair tests; it does not execute research
jobs or establish the authenticity of a real approval. The repository entry
`python3 scripts/validate_all.py` additionally tests installer, control-plane
and privacy regressions in a disposable home, without reading your configuration.

## Rollback

Restore the relevant files from the installer's timestamped backup and use the
runtime matching any preserved active record. Restore manually merged settings
from your own backup. Remove only newly installed files that you have identified;
never recursively delete a Codex home.
