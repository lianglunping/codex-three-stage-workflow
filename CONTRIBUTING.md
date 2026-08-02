# Contributing

Contributions are welcome through GitHub issues and pull requests.

## Development

1. Create a feature branch from `main`.
2. Add or update a failing regression before changing behavior.
3. Keep model-role, single-writer, seal, and audit-receipt contracts backward
   compatible unless the change is explicitly documented as breaking.
4. Run:

   ```bash
   python3 scripts/audit_public_release.py .
   python3 scripts/validate_all.py
   ```

5. Use a Conventional Commit subject and explain security-boundary changes in
   the pull request.

Do not include local Codex configuration, transcripts, credentials, private
project paths, research data, or installer backups in issues or commits.
