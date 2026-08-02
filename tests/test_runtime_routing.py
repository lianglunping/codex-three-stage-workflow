from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "runtime" / "hooks" / "three_stage_write_guard.py"
POLICY = ROOT / "runtime" / "policies" / "three-stage-runtime-v1.json"


def load_hook():
    spec = importlib.util.spec_from_file_location("public_write_guard", HOOK)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {HOOK}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def codex_home(path: Path):
    previous = os.environ.get("CODEX_HOME")
    os.environ["CODEX_HOME"] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = previous


class RuntimePolicyTests(unittest.TestCase):
    def test_public_policy_has_only_sol_and_terra(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(
            set(policy["model_roles"]), {"gpt-5.6-sol", "gpt-5.6-terra"}
        )
        self.assertEqual(
            policy["model_roles"]["gpt-5.6-sol"],
            ["READ_ONLY_REVIEWER", "AUDITOR"],
        )
        self.assertEqual(
            policy["model_roles"]["gpt-5.6-terra"],
            ["STAGING_WRITER", "CANONICAL_INTEGRATOR"],
        )

    def test_runtime_policy_path_precedence(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            explicit = home / "explicit.json"
            installed = home / "policies" / "three-stage-runtime-v1.json"
            installed.parent.mkdir(parents=True)
            installed.write_text("{}\n", encoding="utf-8")
            with codex_home(home):
                self.assertEqual(hook.runtime_policy_path(str(explicit)), explicit)
                self.assertEqual(hook.runtime_policy_path(), installed)


class WriteGuardTests(unittest.TestCase):
    def test_sol_declared_mutation_is_denied(self):
        hook = load_hook()
        self.assertEqual(
            hook.decision(
                {
                    "tool_name": "apply_patch",
                    "model": "gpt-5.6-sol",
                    "tool_input": {},
                }
            ),
            "only Terra may perform declared mutations",
        )

    def test_terra_declared_mutation_is_allowed(self):
        hook = load_hook()
        self.assertIsNone(
            hook.decision(
                {
                    "tool_name": "apply_patch",
                    "model": "gpt-5.6-terra",
                    "tool_input": {},
                }
            )
        )

    def test_unknown_model_declared_mutation_is_denied(self):
        hook = load_hook()
        self.assertEqual(
            hook.decision(
                {
                    "tool_name": "mcp__fs__write_file",
                    "model": "future-model",
                    "tool_input": {},
                }
            ),
            "only Terra may perform declared mutations",
        )

    def test_sol_cannot_spawn_agents(self):
        hook = load_hook()
        self.assertEqual(
            hook.decision(
                {
                    "tool_name": "spawn_agent",
                    "model": "gpt-5.6-sol",
                    "tool_input": {},
                }
            ),
            "Sol cannot spawn agents",
        )

    def test_only_exact_disable_command_is_excepted(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            sentinel = home / "hooks" / "three_stage_write_guard.disabled"
            exact = f"touch {sentinel}"
            with codex_home(home):
                self.assertIsNone(
                    hook.decision(
                        {
                            "tool_name": "Bash",
                            "model": "gpt-5.6-sol",
                            "tool_input": {"command": exact},
                        }
                    )
                )
                self.assertEqual(
                    hook.decision(
                        {
                            "tool_name": "Bash",
                            "model": "gpt-5.6-sol",
                            "tool_input": {"command": exact + " && touch another"},
                        }
                    ),
                    "only Terra may perform declared mutations",
                )


if __name__ == "__main__":
    unittest.main()
