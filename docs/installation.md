# Installation

## Requirements

- macOS or Linux
- Python 3.9–3.13
- A current Codex release with Skills, custom agents, and hooks support

No third-party Python dependency is required.

## Inspect and validate

```bash
git clone https://github.com/lianglunping/codex-three-stage-workflow.git
cd codex-three-stage-workflow
python3 scripts/audit_public_release.py .
python3 scripts/validate_all.py
```

## Preview installation

```bash
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}"
```

Dry-run is the default and is byte-for-byte non-mutating. Inspect every target
printed by the command before applying.

## Apply installation

```bash
python3 scripts/install.py \
  --codex-home "${CODEX_HOME:-$HOME/.codex}" \
  --apply
```

The installer copies four Skills, the runtime policy, the hook, and four custom
agent definitions. Existing target files are first copied into a timestamped
backup below the selected Codex home. The installer never edits `config.toml`
or `hooks.json`.

Review and manually merge:

- `examples/config.toml`
- `examples/hooks.json`
- `examples/AGENTS.md`

After enabling the hook, use `/hooks` in Codex CLI to review and trust the exact
definition. Codex records hook trust against its hash, so a changed hook must be
reviewed again.

## Uninstall or rollback

The installer deliberately has no automatic uninstall command. Review the
installed target list and restore the relevant files from the timestamped
backup. If no prior target existed, remove only the exact files installed by
this repository. Never recursively delete an entire Codex home.

