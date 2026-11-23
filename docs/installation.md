# Installation

Use macOS/Linux and Python 3.9 or later; CI targets 3.9 and 3.13. The installer and workflow checks use the Python standard library. Rendering figures uses the plotting dependencies of the selected R or Python project. Check model availability and optional custom-agent
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

Dry-run is the default. `--apply` copies the seven bundled skills, shared research workflow, runtime policy
and four optional read-only agent definitions. Existing target files are backed
up under the selected Codex home. The installer rejects the filesystem root
and the user's home directory as targets. It never edits `AGENTS.md`,
`config.toml` or `hooks.json` and never activates agents, hooks or plugins.

Manually merge `examples/AGENTS.md` if you want project routing instructions.
`examples/config.toml` is an optional root-model preference. Installing templates
does not change a running model or authorize delegation. New runs require
policy `2.1.0`, actual model-routing evidence and applicable user authority.

## Enable daily research routing

For Codex, review and merge `examples/AGENTS.md` into the active global
`AGENTS.md`. For DeepSeek Harness, use its own installation target and example:

```sh
python3 scripts/install.py --dsh-home "$HOME/.dsh"
python3 scripts/install.py --dsh-home "$HOME/.dsh" --apply
```

Merge `hosts/deepseek/examples/AGENTS.md` into the Harness global `AGENTS.md`.
For a new home with no AGENTS file, copy the corresponding example. If the host
home is customized, use its actual path in the example. Keep existing local
instructions. Pair the global example with the Harness runtime prompt:
in a desktop preset append the prose from [research-routing.yml](../hosts/deepseek/examples/research-routing.yml)
to its existing `dsh-persona` suffix. For the native headless profile, pass
`dsh headless --patch "$HOME/.dsh/research-workflow/research-routing.yml" "your task"` or merge the
shown `personaSuffix` with the existing profile suffix. This patch carries
only research intake and delivery instructions.
Start a fresh chat in an ordinary task directory after activation. Both hosts use
the installed `research-workflow/WORKFLOW.md` and the same figure skills;
Harness uses its own stage policy and models. Render plots with the project's
R or Python environment. Optional figure libraries and upstream galleries are
linked where used.

## Upgrade from 0.1.0

1. Finish or preserve any active run before changing its installed runtime.
   Back up its existing workflow and policy; retain the runtime needed to read
   legacy records. This release does not migrate active task records.
2. Review the dry-run, then apply the new package. Public package version
   `0.3.0` is distinct from runtime policy version `2.1.0`.
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
