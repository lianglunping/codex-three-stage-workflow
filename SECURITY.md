# Security Policy

## Supported versions

Security fixes currently target the latest tagged release.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting or Security Advisory interface for
the repository. Do not open a public issue for an unpatched vulnerability and
do not include credentials, transcripts, unpublished data, or private paths.

Include the affected version, operating system, Codex version, minimal
reproduction, impact, and whether the hook was enabled or disabled. Expect an
initial acknowledgement through GitHub within seven days.

The included hook is defense in depth. It evaluates declared hook payloads,
fails open on internal exceptions, and has an explicit disable sentinel. It is
not an operating-system sandbox or a replacement for Codex permissions,
repository review, and least-privilege configuration.
