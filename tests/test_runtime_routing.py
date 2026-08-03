from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "runtime" / "hooks" / "three_stage_write_guard.py"
POLICY = ROOT / "runtime" / "policies" / "three-stage-runtime-v1.json"
RUN_PROTOCOL = ROOT / "skills" / "staged-agent-run-protocol" / "SKILL.md"
WORKFLOW_VALIDATOR = (
    ROOT
    / "skills"
    / "three-stage-complex-workflow"
    / "scripts"
    / "validate_workflow_contract.py"
)
WORKFLOW_SKILL = ROOT / "skills" / "three-stage-complex-workflow"
WORKFLOW_CASES = WORKFLOW_SKILL / "references" / "regression_cases.tsv"
EXAMPLE_AGENTS = ROOT / "examples" / "AGENTS.md"


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
    def test_public_policy_scopes_model_roles_to_explicit_or_active_runs(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["activation"], "explicit_skill_or_active_run")

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

    def test_staged_protocol_allows_ordinary_approved_research_execution(self):
        protocol = RUN_PROTOCOL.read_text(encoding="utf-8")
        self.assertNotIn(
            "Apply this protocol only to an explicitly invoked or verifiably active\n"
            "  three-stage run.",
            protocol,
        )
        self.assertIn("ordinary approved research execution", protocol)
        self.assertIn(
            "Sol/Terra model roles apply only within an explicit or active three-stage run.",
            protocol,
        )


class WorkflowRoutingContractTests(unittest.TestCase):
    def test_workflow_identity_and_status_documentation_are_required(self):
        cases = (
            ("skill_current_task_id", "SKILL.md", "current_task_id: string | null"),
            ("skill_run_status", "SKILL.md", "run_status: ACTIVE | CLOSED"),
            ("agents_current_task_id", "AGENTS.md", "current_task_id"),
            ("agents_active_status", "AGENTS.md", "状态为 `ACTIVE`"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            skill_root = temporary / "three-stage-complex-workflow"
            shutil.copytree(WORKFLOW_SKILL, skill_root)
            agents = temporary / "AGENTS.md"
            shutil.copy(EXAMPLE_AGENTS, agents)
            for name, relative_path, token in cases:
                with self.subTest(name=name):
                    target = skill_root / relative_path if relative_path == "SKILL.md" else agents
                    original = target.read_text(encoding="utf-8")
                    self.assertIn(token, original)
                    target.write_text(
                        original.replace(token, "REMOVED_REQUIRED_TOKEN"),
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(WORKFLOW_VALIDATOR),
                            "--skill-root",
                            str(skill_root),
                            "--agents",
                            str(agents),
                            "--cases",
                            str(WORKFLOW_CASES),
                            "--policy",
                            str(POLICY),
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    target.write_text(original, encoding="utf-8")

    def test_invalid_active_run_enumerations_are_input_errors(self):
        cases = WORKFLOW_CASES.read_text(encoding="utf-8")
        invalid_cases = {
            "prior_stage": cases.replace(
                "selected_option_active_run\tcomplex_multifile\tfalse\tANALYZE",
                "selected_option_active_run\tcomplex_multifile\tfalse\tBOGUS",
            ),
            "run_status": cases.replace(
                "task-selected\ttask-selected\tACTIVE\toption-1",
                "task-selected\ttask-selected\tactive\toption-1",
            ),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for field, content in invalid_cases.items():
                with self.subTest(field=field):
                    path = Path(tmp) / f"invalid_{field}.tsv"
                    path.write_text(content, encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(WORKFLOW_VALIDATOR),
                            "--skill-root",
                            str(WORKFLOW_SKILL),
                            "--agents",
                            str(EXAMPLE_AGENTS),
                            "--cases",
                            str(path),
                            "--policy",
                            str(POLICY),
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(f"invalid {field}", result.stderr)


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

    def test_sol_may_explicitly_handoff_to_terra(self):
        hook = load_hook()
        self.assertIsNone(
            hook.decision(
                {
                    "tool_name": "spawn_agent",
                    "model": "gpt-5.6-sol",
                    "tool_input": {"model": "gpt-5.6-terra"},
                }
            )
        )

    def test_sol_to_terra_handoff_cannot_bypass_declared_mutation(self):
        hook = load_hook()
        for tool in ("mcp__spawn_agent_write_file", "write_spawn_agent"):
            with self.subTest(tool=tool):
                self.assertEqual(
                    hook.decision(
                        {
                            "tool_name": tool,
                            "model": "gpt-5.6-sol",
                            "tool_input": {"model": "gpt-5.6-terra"},
                        }
                    ),
                    "only Terra may perform declared mutations",
                )

    def test_sol_may_handoff_to_terra_with_runtime_spawn_name(self):
        hook = load_hook()
        self.assertIsNone(
            hook.decision(
                {
                    "tool_name": "collaborationspawn_agent",
                    "model": "gpt-5.6-sol",
                    "tool_input": {"model": "gpt-5.6-terra"},
                }
            )
        )

    def test_sol_strict_guard_cannot_spawn_non_terra_agent(self):
        hook = load_hook()
        self.assertEqual(
            hook.decision(
                {
                    "tool_name": "spawn_agent",
                    "model": "gpt-5.6-sol",
                    "tool_input": {"model": "gpt-5.6-sol"},
                }
            ),
            "Sol may only hand off to Terra",
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
