# Security Boundary

The skills and validators govern declared task identity, stages, scope and
acceptance. They do not authenticate user approval, model identity, capability
evidence or the truth of a PASS string. They cannot discover every filesystem
change or enforce an operating-system permission boundary.

- Inspect independent evidence before accepting state assertions.
- Keep host permissions, repository access controls and human review in effect.
- Model compatibility and available tools do not grant delegation or write authority.
- Automatic progression does not authorize external sends, uploads, commits,
  pushes, credential changes or global environment changes.
- Required acceptance failures cannot be hidden by lowering a gate.

The former optional strict hook hardcoded Sol/Terra mutation rules. It is retired
in 0.2.0 and no replacement enforcement hook is claimed. Remove only its old
configuration entry if previously enabled; the installer never changes active
hook configuration. Follow the [migration instructions](installation.md).

## Public export boundary

Publish generic code, documentation and explicitly synthetic fixtures only.
Do not copy personal AGENTS/configuration, sessions, credentials, local task
state, research inputs/results, logs, receipts or backups. The included
`audit_public_release.py` scans known secret/path patterns and checks every
release-file hash against `MANIFEST.sha256`; pattern checks cannot establish
that arbitrary content is free of private information. Review the exact diff
and file inventory before publishing. Keep scan reports outside the repository.

`validate_all.py` installs into a disposable Codex home and uses repository
examples. It does not read personal workflow configuration or research tasks.
The installer copies only bundled components and backs up existing target files;
it does not enable optional agents or modify active configuration.
