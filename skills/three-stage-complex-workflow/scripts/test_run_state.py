"""Regression tests against actual JSON-shaped state, including CLI failures."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_run_state import assess_state

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "policies/three-stage-runtime-v1.json"
ROLES = json.loads(POLICY_PATH.read_text())["model_roles"]


def fixture():
    """Synthetic task evidence, never evidence of a real user's authorization."""
    return {
        "task_id": "fixture", "current_task_id": "fixture",
        "workflow_stage": "EXECUTE", "run_status": "ACTIVE",
        "selected_option": "Change the fixture's single output",
        "approved_scope": {"files": ["fixture.txt"]},
        "approval_evidence": "TEST ONLY: explicit bounded-auto approval for this fixture",
        "scope_fingerprint": "fixture-scope", "approval_scope_fingerprint": "fixture-scope",
        "autonomy_mode": "BOUNDED_AUTO", "authority_envelope": {"files": ["fixture.txt"]},
        "acceptance_contract": [{"gate_id": "G1", "criterion": "Output matches input",
            "verification_method": "Compare fixture output", "pass_condition": "Equality",
            "required": True, "status": "PENDING", "evidence": None}],
        "repair_attempts": 0, "max_repair_attempts": 3,
        "total_repair_attempts": 0, "max_total_repair_attempts": 6,
        "auto_transition_log": [
            {"from_stage": a, "to_stage": b, "exit_contract_status": "PASS",
             "authority_match": True, "scope_fingerprint": "fixture-scope",
             "evidence": "TEST ONLY: fixture stage decision"}
            for a, b in [("ANALYZE", "REFINE"), ("REFINE", "EXECUTE")]],
    }


def decision(state=None, **kwargs):
    inputs = dict(current_task_id="fixture", current_scope_fingerprint="fixture-scope",
                  current_model="gpt-6.1-sol", model_roles=ROLES)
    inputs.update(kwargs)
    return assess_state(fixture() if state is None else state, **inputs)["decision"]


class ActualRunState(unittest.TestCase):
    def test_compatible_models_continue_each_stage(self):
        for model in ("gpt-6.1-sol", "gpt-5.6-sol", "gpt-6-astra"):
            for stage, count in [("ANALYZE", 0), ("REFINE", 1), ("EXECUTE", 2)]:
                with self.subTest(model=model, stage=stage):
                    state = fixture()
                    state.update(workflow_stage=stage, auto_transition_log=state["auto_transition_log"][:count])
                    self.assertEqual(decision(state, current_model=model), "CONTINUE_" + stage)

    def test_manual_planning_does_not_require_execution_approval(self):
        state = fixture()
        state.update(autonomy_mode="MANUAL", workflow_stage="ANALYZE", selected_option=None,
                     approved_scope=None, approval_evidence=None, authority_envelope=None,
                     acceptance_contract=[], auto_transition_log=[])
        self.assertEqual(decision(state), "CONTINUE_ANALYZE")

    def test_model_identity_is_required_and_order_independent(self):
        reversed_roles = dict(reversed(list(ROLES.items())))
        self.assertEqual(decision(model_roles=reversed_roles), "CONTINUE_EXECUTE")
        self.assertEqual(decision(current_model=None), "PAUSE_CURRENT_MODEL_UNKNOWN")
        self.assertEqual(decision(current_model="unknown"), "PAUSE_MODEL_ROLE_UNAVAILABLE")
        self.assertEqual(decision(current_model="gpt-5.6-sol"), "CONTINUE_EXECUTE")
        self.assertEqual(decision(current_model="gpt-5.6-luna"), "PAUSE_MODEL_ROLE_UNAVAILABLE")
        self.assertEqual(decision(current_model="gpt-5.6-terra"), "CONTINUE_EXECUTE")

    def test_state_model_claim_does_not_override_runtime(self):
        state = fixture(); state["execution_model"] = "gpt-6.1-sol"
        self.assertEqual(decision(state, current_model="unknown"), "PAUSE_MODEL_ROLE_UNAVAILABLE")

    def test_identity_and_schema(self):
        for change in ({"task_id": "different"}, {"current_task_id": ""}):
            self.assertEqual(decision({**fixture(), **change}), "INVALID_TASK_IDENTITY")
        state = fixture(); del state["auto_transition_log"]
        self.assertEqual(decision(state), "INVALID_STATE")
        self.assertEqual(decision([]), "INVALID_STATE")
        for field in ("workflow_stage", "autonomy_mode", "run_status"):
            self.assertEqual(decision({**fixture(), field: []}), "INVALID_STATE")

    def test_scope_is_checked_independently(self):
        self.assertEqual(decision(current_scope_fingerprint="different"), "RETURN_TO_AFFECTED_PLANNING")
        self.assertEqual(decision({**fixture(), "approval_scope_fingerprint": "old"}), "RETURN_TO_AFFECTED_PLANNING")

    def test_authority_cannot_be_replaced_by_model_compatibility(self):
        for mode in ("MANUAL", "BOUNDED_AUTO"):
            for field in ("approval_evidence", "authority_envelope"):
                with self.subTest(mode=mode, field=field):
                    self.assertEqual(decision({**fixture(), "autonomy_mode": mode, field: None}), "PAUSE_AUTHORITY")
        self.assertEqual(decision({**fixture(), "approved_scope": None}), "RETURN_TO_REFINE_INCOMPLETE_AUTHORITY")

    def test_selection_is_required_before_execute(self):
        self.assertEqual(decision({**fixture(), "selected_option": None}), "RETURN_TO_REFINE_MISSING_SELECTION")

    def test_counters_are_strict_integers(self):
        for field in ("repair_attempts", "total_repair_attempts", "max_repair_attempts", "max_total_repair_attempts"):
            for value in (True, 0.5, "1", -1):
                with self.subTest(field=field, value=value):
                    self.assertEqual(decision({**fixture(), field: value}), "INVALID_REPAIR_COUNTER")

    def test_counter_relationship_and_caps(self):
        for change in ({"repair_attempts": 1}, {"max_repair_attempts": 0},
                       {"max_repair_attempts": 4}, {"max_total_repair_attempts": 7}):
            self.assertEqual(decision({**fixture(), **change}), "INVALID_REPAIR_COUNTER")

    def test_budget_stops_persist(self):
        self.assertEqual(decision({**fixture(), "repair_attempts": 3, "total_repair_attempts": 3}), "PAUSE_REPEATED_FAILURE")
        self.assertEqual(decision({**fixture(), "total_repair_attempts": 6}), "PAUSE_RESOURCE_BUDGET_EXHAUSTED")
        self.assertEqual(decision({**fixture(), "max_repair_attempts": 1, "repair_attempts": 1,
                                   "total_repair_attempts": 1}), "PAUSE_REPEATED_FAILURE")

    def test_gate_schema_and_uniqueness(self):
        for change in ({"required": "true"}, {"status": "READY"}, {"criterion": ""},
                       {"verification_method": None}, {"gate_id": []}):
            state = fixture(); state["acceptance_contract"][0].update(change)
            self.assertEqual(decision(state), "INVALID_ACCEPTANCE")
        state = fixture(); state["acceptance_contract"] *= 2
        self.assertEqual(decision(state), "INVALID_ACCEPTANCE")
        self.assertEqual(decision({**fixture(), "acceptance_contract": []}), "RETURN_TO_REFINE_ACCEPTANCE_NOT_READY")

    def test_pass_requires_evidence(self):
        state = fixture(); state["acceptance_contract"][0]["status"] = "PASS"
        self.assertEqual(decision(state, completion=True), "INVALID_ACCEPTANCE")

    def test_required_failure_and_blocker_differ(self):
        for status, expected in (("FAIL", "REPAIR_WITHIN_SCOPE"), ("BLOCKED", "PAUSE_ACCEPTANCE_BLOCKED")):
            state = fixture(); state["acceptance_contract"][0]["status"] = status
            self.assertEqual(decision(state), expected)

    def test_manual_failed_checks_pause_before_repair_or_completion(self):
        for required in (True, False):
            for completion in (False, True):
                with self.subTest(required=required, completion=completion):
                    state = fixture()
                    state.update(autonomy_mode="MANUAL", auto_transition_log=[])
                    state["acceptance_contract"][0].update(status="PASS", evidence="qa.json")
                    failed = copy.deepcopy(state["acceptance_contract"][0])
                    failed.update(gate_id="failed-check", required=required, status="FAIL", evidence="failed.log")
                    state["acceptance_contract"].append(failed)
                    self.assertEqual(decision(state, completion=completion), "PAUSE_CHECK_FAILED")

    def test_manual_pending_retest_is_not_failed_or_completed(self):
        state = fixture()
        state.update(autonomy_mode="MANUAL", auto_transition_log=[])
        self.assertEqual(decision(state), "CONTINUE_EXECUTE")
        self.assertEqual(decision(state, completion=True), "INCOMPLETE_ACCEPTANCE")
        state["acceptance_contract"][0].update(status="PASS", evidence="retest.log")
        self.assertEqual(decision(state, completion=True), "COMPLETE_READY")

    def test_completion_requires_all_required_gates(self):
        for status in ("PENDING", "FAIL", "BLOCKED"):
            state = fixture(); state["acceptance_contract"][0]["status"] = status
            self.assertEqual(decision(state, completion=True), "INCOMPLETE_ACCEPTANCE")
        state = fixture(); state["acceptance_contract"][0].update(status="PASS", evidence="TEST ONLY: equal output")
        self.assertEqual(decision(state, completion=True), "COMPLETE_READY")
        optional = copy.deepcopy(state["acceptance_contract"][0])
        optional.update(gate_id="optional", required=False, status="FAIL", evidence=None)
        state["acceptance_contract"].append(optional)
        self.assertEqual(decision(state, completion=True), "COMPLETE_READY")

    def test_completion_cannot_close_planning(self):
        state = fixture(); state.update(workflow_stage="ANALYZE", auto_transition_log=[])
        self.assertEqual(decision(state, completion=True), "INCOMPLETE_ACCEPTANCE")

    def test_missing_or_stale_receipt_requires_recovery(self):
        for receipts in ([], fixture()["auto_transition_log"][:1]):
            self.assertEqual(decision({**fixture(), "auto_transition_log": receipts}), "REGENERATE_RECEIPT_IN_REFINE")
        state = fixture(); state["auto_transition_log"][-1]["scope_fingerprint"] = "old"
        self.assertEqual(decision(state), "REGENERATE_RECEIPT_IN_REFINE")

    def test_jumps_discontinuity_and_forged_receipt_fail(self):
        for change, expected in (({"from_stage": "ANALYZE"}, "INVALID_TRANSITION_ORDER"),
                                 ({"authority_match": "true"}, "INVALID_TRANSITION_RECEIPT"),
                                 ({"evidence": ""}, "INVALID_TRANSITION_RECEIPT")):
            state = fixture(); state["auto_transition_log"][-1].update(change)
            self.assertEqual(decision(state), expected)
        state = fixture(); state["auto_transition_log"] = state["auto_transition_log"][-1:]
        self.assertEqual(decision(state), "INVALID_TRANSITION_ORDER")

    def test_replan_retains_history_and_can_execute_again(self):
        state = fixture(); receipt = state["auto_transition_log"][-1]
        state["auto_transition_log"] += [{**receipt, "from_stage": "EXECUTE", "to_stage": "REFINE"},
                                         copy.deepcopy(receipt)]
        self.assertEqual(decision(state), "CONTINUE_EXECUTE")
        state["auto_transition_log"][0]["scope_fingerprint"] = "historical-scope"
        self.assertEqual(decision(state), "CONTINUE_EXECUTE")

    def test_closed_record_cannot_resume(self):
        self.assertEqual(decision({**fixture(), "run_status": "CLOSED"}), "CLOSED_ROUTE_ORDINARY")

    def test_cli_positive_and_negative_exit_status(self):
        with tempfile.TemporaryDirectory(prefix="three-stage-state-") as tmp:
            path = Path(tmp) / "state.json"
            command = [sys.executable, str(ROOT / "scripts/validate_run_state.py"),
                       "--state", str(path), "--current-task-id", "fixture",
                       "--scope-fingerprint", "fixture-scope", "--current-model", "gpt-6.1-sol",
                       "--policy", str(POLICY_PATH)]
            for state, expected in ((fixture(), 0), ({**fixture(), "approval_evidence": None}, 1), ([], 1)):
                path.write_text(json.dumps(state))
                outcome = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(outcome.returncode, expected, outcome.stderr)
                self.assertIn("decision", json.loads(outcome.stdout))
            path.write_text("invalid json")
            outcome = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(outcome.returncode, 1)
            self.assertEqual(json.loads(outcome.stdout)["decision"], "INVALID_STATE")


if __name__ == "__main__":
    unittest.main()
