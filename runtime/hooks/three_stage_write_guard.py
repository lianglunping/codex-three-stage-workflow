#!/usr/bin/env python3
"""Conservative PreToolUse guard for declared Codex hook payloads."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional


POLICY_NAME = "three-stage-runtime-v1.json"
DISABLE_NAME = "three_stage_write_guard.disabled"
WRITE_TOOLS = {"apply_patch", "Write", "Edit", "MultiEdit", "NotebookEdit"}
MUTATION = (
    "apply_patch",
    ">",
    "mkdir ",
    "mv ",
    "cp ",
    "rm ",
    "touch ",
    "chmod ",
)
MUTATION_TOKENS = {
    "write",
    "edit",
    "create",
    "delete",
    "remove",
    "rename",
    "move",
    "copy",
    "upload",
    "send",
    "publish",
    "post",
    "commit",
    "push",
    "merge",
    "patch",
}


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def runtime_policy_path(explicit: Optional[str] = None) -> Path:
    """Resolve explicit, installed, then repository policy locations."""
    if explicit:
        return Path(explicit).expanduser()
    installed = codex_home() / "policies" / POLICY_NAME
    if installed.is_file():
        return installed
    repository = Path(__file__).resolve().parents[1] / "policies" / POLICY_NAME
    return repository if repository.is_file() else installed


def disable_path() -> Path:
    return codex_home() / "hooks" / DISABLE_NAME


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def decision(payload: dict) -> Optional[str]:
    tool = str(payload.get("tool_name", ""))
    model = str(payload.get("model", ""))
    command = str((payload.get("tool_input") or {}).get("command", ""))
    sentinel = disable_path()
    if command.strip() == f"touch {sentinel}" or sentinel.exists():
        return None

    lowered = tool.lower().replace("-", "_")
    words = set(lowered.split("_"))
    named_mutation = bool(words & MUTATION_TOKENS)
    mutates = (
        tool in WRITE_TOOLS
        or named_mutation
        or (tool == "Bash" and any(token in command for token in MUTATION))
    )
    if (tool == "Agent" or "spawn_agent" in lowered) and model == "gpt-5.6-sol":
        return "Sol cannot spawn agents"
    if mutates and model != "gpt-5.6-terra":
        return "only Terra may perform declared mutations"
    return None


def main() -> int:
    try:
        reason = decision(json.load(sys.stdin))
        if reason:
            deny(reason)
    except Exception:
        pass  # Hook-internal errors deliberately fail open.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
