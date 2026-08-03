# Security Boundary

The runtime hook is an optional strict `PreToolUse` guard for a dedicated,
explicitly activated three-stage session. It reads the declared
tool name, model slug, and tool input supplied by Codex and emits only a short
reason code when it denies an action.

It can block declared mutations by Sol or unknown models. It permits an explicit
Sol-to-Terra handoff and rejects other strict-mode Sol agent-spawn calls. It is
not enabled by default and must not be used as a global restriction on ordinary
task reads, file generation, writes, or agent dispatch. It cannot:

- prove that the declared model identity is authentic;
- parse every possible shell mutation or indirect side effect;
- cover specialized tools that opt out of the normal hook path;
- prevent writes after an internal hook exception, because it fails open;
- replace Codex sandboxing, approval policy, repository permissions, or review.

Creating `<CODEX_HOME>/hooks/three_stage_write_guard.disabled` disables the
guard. The exact command to create that sentinel is intentionally allowed so an
operator can recover from a broken rule. Treat sentinel access as privileged
and document its use.

Codex can load multiple matching hooks concurrently; this guard does not stop
another hook from starting. Review all active hook sources with `/hooks`.

Official Codex references:

- [Hooks](https://developers.openai.com/codex/hooks)
- [Subagents and custom agents](https://developers.openai.com/codex/subagents)
- [Configuration reference](https://developers.openai.com/codex/config-reference)
