from __future__ import annotations

import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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


class RuntimePolicyTests(unittest.TestCase):
    def test_protocol_policy_resolver_honors_isolated_home_and_explicit_path(self):
        source = ROOT / "skills/staged-agent-run-protocol/scripts/sar_utils.py"
        spec = importlib.util.spec_from_file_location("policy_resolver", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CODEX_HOME": tmp}):
            policy = Path(tmp) / "policies/three-stage-runtime-v1.json"
            policy.parent.mkdir()
            policy.write_text("{}", encoding="utf-8")
            self.assertEqual(module.runtime_policy_path(), policy)
            explicit = Path(tmp) / "explicit.json"
            self.assertEqual(module.runtime_policy_path(str(explicit)), explicit)

    def test_current_policy_preserves_activation_and_model_routing(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["version"], "2.1.0")
        self.assertEqual(policy["activation"], "explicit_skill_natural_autonomy_or_active_run")
        self.assertEqual(policy["stage_model_defaults"], {
            "ANALYZE": "gpt-6-astra", "REFINE": "gpt-6-astra", "EXECUTE": "gpt-6.1-sol"})
        self.assertFalse(policy["subagent_selection"]["fixed_model_allowlist"])
        self.assertTrue(policy["subagent_selection"]["delegation_requires_explicit_authority"])

    def test_staged_protocol_allows_ordinary_approved_research_execution(self):
        protocol = RUN_PROTOCOL.read_text(encoding="utf-8")
        self.assertNotIn(
            "Apply this protocol only to an explicitly invoked or verifiably active\n"
            "  three-stage run.",
            protocol,
        )
        self.assertIn("ordinary approved research execution", protocol)
        self.assertIn(
            "Runtime-policy model roles apply only within an explicit or active three-stage run.",
            protocol,
        )


class WorkflowRoutingContractTests(unittest.TestCase):
    def test_workflow_identity_and_status_documentation_are_required(self):
        cases = (
            ("skill_stage_marker", "SKILL.md", "【执行方案】"),
            ("skill_run_status", "SKILL.md", "MANUAL"),
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
        with WORKFLOW_CASES.open(encoding="utf-8") as handle:
            cases = list(csv.DictReader(handle, delimiter="\t"))
        with tempfile.TemporaryDirectory() as tmp:
            for field, invalid in (("prior_stage", "BOGUS"), ("run_status", "active")):
                with self.subTest(field=field):
                    path = Path(tmp) / f"invalid_{field}.tsv"
                    mutated = [dict(row) for row in cases]
                    mutated[0][field] = invalid
                    with path.open("w", encoding="utf-8", newline="") as handle:
                        writer = csv.DictWriter(handle, fieldnames=list(cases[0]), delimiter="\t")
                        writer.writeheader()
                        writer.writerows(mutated)
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



if __name__ == "__main__":
    unittest.main()
