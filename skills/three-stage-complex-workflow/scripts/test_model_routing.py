"""Behavioral routing and real consumer/CLI regression tests (synthetic authority)."""
import copy
import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from model_routing import resolve_stage, model_supports_role
from validate_run_state import assess_state
from test_run_state import fixture, ROLES

SCRIPTS = Path(__file__).resolve().parent
HOME = SCRIPTS.parents[2]
POLICY_PATH = HOME / "policies/three-stage-runtime-v1.json"
POLICY = json.loads(POLICY_PATH.read_text())
REGISTRY_SCRIPT = HOME / "skills/staged-agent-run-protocol/scripts/register_agent_assignment.py"


def evidence():
    return ({"source": "TEST ONLY: current runtime tool and agent observation", "observed_at": "2026-10-23",
             "current_model": "gpt-6-astra", "available_models": ["gpt-6-astra", "gpt-6.1-sol", "gpt-5.6-luna", "future-full-model-id"],
             "delegation_tool_available": True,
             "agents": [{"agent_path": "/root", "model": "gpt-6-astra"},
                        {"agent_path": "/root/exec", "model": "gpt-6.1-sol"}]},
            {"source": "TEST ONLY: task requirements and supported model capabilities reviewed", "observed_at": "2026-10-23",
             "models": {m: ["planning", "implementation", "audit", "canonical_integration"] for m in
                        ["gpt-6-astra", "gpt-6.1-sol", "gpt-5.6-luna", "future-full-model-id"]}})


def state_fixture():
    state = fixture()
    state.update(workflow_policy_version="2.1.0", model_routing={"version": 1,
                 "preferred_model": "gpt-6.1-sol",
                 "stage_lead": {"agent_path": "/root/exec", "model": "gpt-6.1-sol"}})
    return state


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.runtime, self.capabilities = evidence()

    def route(self, stage="EXECUTE", **kwargs):
        options = dict(delegation_authorized=True, delegation_evidence="TEST ONLY human instruction")
        options.update(kwargs)
        return resolve_stage(POLICY, stage, "gpt-6-astra", self.runtime, self.capabilities, **options)

    def assess(self, state=None, **kwargs):
        options = dict(current_task_id="fixture", current_scope_fingerprint="fixture-scope",
                       current_model="gpt-6-astra", model_roles=ROLES, runtime_evidence=self.runtime,
                       capability_evidence=self.capabilities, routing_policy=POLICY,
                       delegation_authorized=True, delegation_evidence="TEST ONLY authorization")
        options.update(kwargs)
        return assess_state(state or state_fixture(), **options)["decision"]

    def test_three_defaults(self):
        for stage, model in [("ANALYZE", "gpt-6-astra"), ("REFINE", "gpt-6-astra"), ("EXECUTE", "gpt-6.1-sol")]:
            with self.subTest(stage=stage):
                self.assertEqual(self.route(stage)["selected_model"], model)

    def test_user_override(self):
        result = self.route(user_override={"model": "future-full-model-id", "evidence": "TEST ONLY explicit user choice"})
        self.assertEqual(result["selected_model"], "future-full-model-id")
        self.assertEqual(result["preferred_model"], "gpt-6.1-sol")

    def test_bad_override(self):
        self.assertEqual(self.route(user_override={"model": "gpt-6-astra"})["decision"], "PAUSE_OVERRIDE_EVIDENCE")

    def test_no_silent_fallback(self):
        self.runtime["available_models"].remove("gpt-6.1-sol")
        self.assertEqual(self.route()["decision"], "PAUSE_MODEL_ROLE_UNAVAILABLE")

    def test_capability_separate_from_runtime(self):
        self.capabilities["models"]["gpt-6.1-sol"] = ["planning"]
        self.assertEqual(self.route()["decision"], "PAUSE_MODEL_ROLE_UNAVAILABLE")

    def test_missing_capability_provenance(self):
        self.capabilities.pop("source")
        self.assertEqual(self.route()["decision"], "PAUSE_MODEL_ROLE_UNAVAILABLE")

    def test_unauthorized_delegation(self):
        self.assertEqual(self.route(delegation_authorized=False)["decision"], "PAUSE_DELEGATION_UNAUTHORIZED")
        self.assertEqual(self.route(delegation_evidence=None)["decision"], "PAUSE_DELEGATION_UNAUTHORIZED")

    def test_tool_unavailable(self):
        self.runtime["delegation_tool_available"] = False
        self.assertEqual(self.route()["decision"], "PAUSE_DELEGATION_UNAVAILABLE")

    def test_unknown_runtime_root(self):
        self.runtime["current_model"] = None
        self.assertEqual(self.route()["decision"], "PAUSE_RUNTIME_EVIDENCE")

    def test_dynamic_old_and_new_model(self):
        for model in ["gpt-5.6-luna", "future-full-model-id"]:
            self.assertTrue(model_supports_role(model, "STAGING_WRITER", self.runtime, self.capabilities))

    def test_real_state_accepts_verified_sol_lead(self):
        self.assertEqual(self.assess(), "CONTINUE_EXECUTE")

    def test_real_state_wrong_lead(self):
        state = state_fixture(); state["model_routing"]["stage_lead"] = {"agent_path": "/root", "model": "gpt-6-astra"}
        self.assertEqual(self.assess(state), "PAUSE_STAGE_LEAD_MISMATCH")

    def test_state_cannot_self_authenticate(self):
        self.runtime["agents"] = []
        self.assertEqual(self.assess(), "PAUSE_STAGE_LEAD_UNVERIFIED")

    def test_new_version_missing_routing(self):
        state = state_fixture();state.pop("model_routing")
        self.assertEqual(self.assess(state), "INVALID_MODEL_ROUTING")

    def test_new_creation_marker_required(self):
        self.assertEqual(self.assess(fixture(), require_model_routing=True), "INVALID_MODEL_ROUTING")

    def test_legacy_state_still_accepted(self):
        self.assertEqual(self.assess(fixture()), "CONTINUE_EXECUTE")

    def test_state_override_requires_independent_input(self):
        state = state_fixture();state["model_routing"]["user_override"] = {"model": "gpt-6-astra", "evidence": "self report"}
        self.assertEqual(self.assess(state), "PAUSE_OVERRIDE_EVIDENCE")

    def test_router_cli_malformed_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in [("runtime", self.runtime), ("capabilities", self.capabilities)]:
                (root / (name + ".json")).write_text(json.dumps(data))
            for bad in [None, []]:
                policy = root / "policy.json"; policy.write_text(json.dumps(bad))
                r = subprocess.run([sys.executable, str(SCRIPTS / "model_routing.py"),
                    "--policy", str(policy), "--stage", "EXECUTE", "--current-model", "gpt-6-astra",
                    "--runtime-evidence", str(root / "runtime.json"),
                    "--capability-evidence", str(root / "capabilities.json")], capture_output=True, text=True)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("INVALID_ROUTING_POLICY", r.stdout)
                self.assertNotIn("Traceback", r.stderr)

    def test_planning_actual_root_lead(self):
        for stage in ["ANALYZE", "REFINE"]:
            state = state_fixture(); state["workflow_stage"] = stage
            state["auto_transition_log"] = [] if stage == "ANALYZE" else state["auto_transition_log"][:1]
            state["model_routing"] = {"version": 1, "preferred_model": "gpt-6-astra",
                "stage_lead": {"agent_path": "/root", "model": "gpt-6-astra"}}
            self.assertEqual(self.assess(state), "CONTINUE_" + stage)

    def test_dynamic_coordination_still_enforces_roles(self):
        from validate_parallel_coordination_contract import resolve
        row = {"case_id": "dynamic", "stage": "EXECUTE", "model": "future-full-model-id",
               "agent_path": "/root/child", "role": "STAGING_WRITER", "write_scope": "OWN_STAGING",
               "base_matches": "true", "overlaps_active": "false", "active_work": "true",
               "active_writer_count": "0", "observations_match": "true", "receipt_present": "false",
               "receipt_current": "false", "drift_class": "none"}
        self.assertEqual(resolve(row, ROLES, self.runtime, self.capabilities), "ALLOW_STAGING_EXECUTION")
        row["role"] = "CANONICAL_INTEGRATOR"
        self.assertEqual(resolve(row, ROLES, self.runtime, self.capabilities), "REJECT_NONROOT_INTEGRATOR")
        row["role"] = "STAGING_WRITER";row["stage"] = "ANALYZE"
        self.assertEqual(resolve(row, ROLES, self.runtime, self.capabilities), "REJECT_PLANNING_WRITE_ROLE")

    def renewal_state(self):
        state = state_fixture()
        state.update(repair_budget_mode="RENEWABLE", repair_attempts=3,
                     total_repair_attempts=3, repair_cycle_attempts=3, repair_cycle_log=[],
                     repair_renewal_authority="TEST ONLY user renewable repair authorization",
                     issue_fingerprint="fixture-routing-renewal")
        return state

    def renew(self, state, **kwargs):
        from repair_budget import renew_cycle
        options = dict(current_task_id="fixture", current_scope_fingerprint="fixture-scope",
                       current_model="gpt-6-astra", model_roles=ROLES,
                       reason="TEST ONLY repair threshold reached", diagnosis="TEST ONLY verified missing context",
                       next_approach="TEST ONLY forward independently reviewed routing evidence",
                       evidence="TEST ONLY failing reproduction retained", runtime_evidence=self.runtime,
                       capability_evidence=self.capabilities, routing_policy=POLICY,
                       delegation_authorized=True, delegation_evidence="TEST ONLY applicable human authority",
                       require_model_routing=True)
        options.update(kwargs)
        return renew_cycle(state, **options)

    def test_new_routing_renewal_preserves_lifetime_and_history(self):
        state = self.renewal_state(); original = copy.deepcopy(state)
        self.assertEqual(self.assess(state), "REVIEW_REPAIR_CYCLE")
        renewed = self.renew(state)
        self.assertEqual(state, original)
        self.assertEqual(renewed["total_repair_attempts"], 3)
        self.assertEqual(renewed["repair_attempts"], 0)
        self.assertEqual(renewed["repair_cycle_attempts"], 0)
        self.assertEqual(renewed["repair_cycle_log"][0]["cycle_attempts"], 3)
        self.assertEqual(renewed["repair_cycle_log"][0]["total_repair_attempts"], 3)
        self.assertEqual(self.assess(renewed), "CONTINUE_EXECUTE")

    def test_new_routing_renewal_rejects_missing_authority(self):
        state = self.renewal_state(); original = copy.deepcopy(state)
        with self.assertRaisesRegex(ValueError, "PAUSE_DELEGATION_UNAUTHORIZED"):
            self.renew(state, delegation_authorized=False)
        self.assertEqual(state, original)
        state["repair_renewal_authority"] = ""
        with self.assertRaisesRegex(ValueError, "PAUSE_REPAIR_RENEWAL_AUTHORITY"):
            self.renew(state)

    def test_new_routing_renewal_forwards_override(self):
        state = self.renewal_state()
        override = {"model": "gpt-6-astra", "evidence": "TEST ONLY explicit root execution request"}
        state["model_routing"]["user_override"] = override
        state["model_routing"]["stage_lead"] = {"agent_path": "/root", "model": "gpt-6-astra"}
        renewed = self.renew(state, user_override=override, delegation_authorized=False)
        self.assertEqual(renewed["model_routing"]["user_override"], override)
        self.assertEqual(renewed["total_repair_attempts"], 3)

    def test_cli_new_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in [("state", state_fixture()), ("runtime", self.runtime), ("capabilities", self.capabilities)]:
                (root / (name + ".json")).write_text(json.dumps(data))
            cmd = [sys.executable, str(SCRIPTS / "validate_run_state.py"), "--state", str(root / "state.json"),
                   "--current-task-id", "fixture", "--scope-fingerprint", "fixture-scope", "--current-model", "gpt-6-astra",
                   "--policy", str(POLICY_PATH), "--runtime-evidence", str(root / "runtime.json"),
                   "--capability-evidence", str(root / "capabilities.json"), "--require-model-routing"]
            denied = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(denied.returncode, 0); self.assertIn("PAUSE_DELEGATION_UNAUTHORIZED", denied.stdout)
            allowed = subprocess.run(cmd + ["--delegation-authorized", "--delegation-evidence", "TEST ONLY human instruction"], capture_output=True, text=True)
            self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
            self.assertIn("CONTINUE_EXECUTE", allowed.stdout)

    def register(self, root, model="future-full-model-id", role="STAGING_WRITER", agent="/root/child", stage="EXECUTE", authority=True, assignment="child", scope=None):
        runtime = root / "runtime.json"; runtime.write_text(json.dumps(self.runtime))
        capabilities = root / "capabilities.json";capabilities.write_text(json.dumps(self.capabilities))
        cmd = [sys.executable, str(REGISTRY_SCRIPT), "--run-dir", str(root), "--assignment-id", assignment,
               "--agent-path", agent, "--parent-agent", "/root", "--role", role, "--model", model,
               "--base-revision", "r0000", "--status", "Planned", "--runtime-evidence", str(runtime),
               "--capability-evidence", str(capabilities), "--workflow-stage", stage]
        if authority: cmd += ["--delegation-authorized", "--delegation-evidence", "TEST ONLY human authorization"]
        if role in {"STAGING_WRITER", "CANONICAL_INTEGRATOR"}:
            cmd += ["--write-scope", str(scope or root / "coordination/staging" / assignment)]
        return subprocess.run(cmd, text=True, capture_output=True)

    def test_registry_dynamic_models_and_provenance(self):
        for model in ["gpt-5.6-luna", "future-full-model-id"]:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp);r = self.register(root, model=model)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                with (root / "coordination/agent_assignments.tsv").open() as handle:
                    notes = next(csv.DictReader(handle, delimiter="\t"))["notes"]
                recorded = json.loads(notes.split("model_evidence=", 1)[1])
                self.assertEqual(set(recorded), {"runtime", "capabilities", "stage",
                    "delegation_authorized", "delegation_evidence"})
                for kind in ("runtime", "capabilities"):
                    self.assertEqual(len(recorded[kind]["sha256"]), 64)

    def test_registry_safety_boundaries(self):
        for options, message in [({"authority": False}, "delegation authority"),
                                 ({"role": "CANONICAL_INTEGRATOR"}, "reserved for root"),
                                 ({"stage": "REFINE"}, "planning stages"),
                                 ({"scope": Path("/tmp/outside")}, "staging writer scope")]:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                r = self.register(Path(tmp), **options)
                self.assertNotEqual(r.returncode, 0); self.assertIn(message, r.stdout)

    def test_registry_second_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);self.assertEqual(self.register(root).returncode, 0)
            second = self.register(root, assignment="other")
            self.assertNotEqual(second.returncode, 0); self.assertIn("at most one active writer", second.stdout)

    def test_registry_missing_capability(self):
        self.capabilities["models"]["future-full-model-id"] = ["planning"]
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(self.register(Path(tmp)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
