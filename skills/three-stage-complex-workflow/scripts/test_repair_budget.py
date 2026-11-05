"""Behavioral repair-cycle tests with disposable synthetic task evidence."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from repair_budget import renew_cycle
from test_run_state import fixture, decision, ROLES


def renewable():
    state = fixture()
    state.update(repair_budget_mode="RENEWABLE", repair_cycle_attempts=0,
                 repair_cycle_log=[], issue_fingerprint="fixture:failure",
                 repair_renewal_authority="TEST ONLY: user permits task-scoped cycle renewals")
    return state


def spend(state, issue=3, cycle=3):
    updated = copy.deepcopy(state)
    updated.update(repair_attempts=issue, repair_cycle_attempts=cycle,
                   total_repair_attempts=state["total_repair_attempts"] + cycle)
    return updated


def renew(state, **changes):
    args = dict(current_task_id="fixture", current_scope_fingerprint="fixture-scope",
                current_model="gpt-6.1-sol", model_roles=ROLES,
                reason="TEST ONLY: diagnosis review", diagnosis="TEST ONLY: new cause",
                next_approach="TEST ONLY: changed method", evidence="TEST ONLY: diagnostic result")
    args.update(changes)
    return renew_cycle(state, **args)


class RepairCycles(unittest.TestCase):
    def test_initial_renewable_cycle_is_ready(self):
        self.assertEqual(decision(renewable()), "CONTINUE_EXECUTE")

    def test_thresholds_request_internal_review(self):
        for issue, cycle in ((3, 3), (1, 6)):
            self.assertEqual(decision(spend(renewable(), issue, cycle)), "REVIEW_REPAIR_CYCLE")

    def test_multiple_cycles_exceed_old_lifetime_limit(self):
        state = renewable()
        for index in range(5):
            state = spend(state)
            before = copy.deepcopy(state)
            state = renew(state, diagnosis=f"TEST ONLY: observation {index}",
                          evidence=f"TEST ONLY: result {index}")
            self.assertEqual(before["total_repair_attempts"], state["total_repair_attempts"])
            self.assertEqual(state["repair_attempts"], 0)
            self.assertEqual(state["repair_cycle_attempts"], 0)
            self.assertEqual(state["repair_cycle_log"][:-1], before["repair_cycle_log"])
            self.assertEqual(decision(state), "CONTINUE_EXECUTE")
        self.assertEqual(state["total_repair_attempts"], 15)
        self.assertEqual(len(state["repair_cycle_log"]), 5)

    def test_renewal_preserves_failed_gate_and_input_record(self):
        original = spend(renewable())
        original["acceptance_contract"][0].update(status="FAIL", evidence="TEST ONLY: failed.log")
        saved = copy.deepcopy(original)
        updated = renew(original)
        self.assertEqual(original, saved)
        self.assertEqual(updated["acceptance_contract"], original["acceptance_contract"])
        self.assertEqual(updated["issue_fingerprint"], original["issue_fingerprint"])
        self.assertEqual(decision(updated), "REPAIR_WITHIN_SCOPE")
        self.assertEqual(decision(updated, completion=True), "INCOMPLETE_ACCEPTANCE")

    def test_early_checkpoint_renewal(self):
        state = renew(spend(renewable(), 1, 1), reason="TEST ONLY: checkpoint passed")
        self.assertEqual(state["total_repair_attempts"], 1)

    def test_zero_attempt_and_fixed_mode_renewals_rejected(self):
        for state in (renewable(), fixture(), {**fixture(), "repair_budget_mode": "FIXED"}):
            with self.assertRaises(ValueError):
                renew(state)

    def test_legacy_fixed_limits_remain(self):
        self.assertEqual(decision({**fixture(), "total_repair_attempts": 6}), "PAUSE_RESOURCE_BUDGET_EXHAUSTED")
        self.assertEqual(decision({**fixture(), "repair_attempts": 3, "total_repair_attempts": 3}), "PAUSE_REPEATED_FAILURE")

    def test_smaller_user_threshold_preserved(self):
        state = renewable(); state.update(max_repair_attempts=1, max_total_repair_attempts=2)
        state = spend(state, 1, 1)
        self.assertEqual(decision(state), "REVIEW_REPAIR_CYCLE")
        renewed = renew(state)
        self.assertEqual(renewed["max_repair_attempts"], 1)
        self.assertEqual(renewed["max_total_repair_attempts"], 2)

    def test_identical_renewal_stalls(self):
        state = spend(renew(spend(renewable())))
        with self.assertRaisesRegex(ValueError, "PAUSE_REPAIR_STALLED"):
            renew(state)

    def test_missing_renewal_evidence_rejected(self):
        for field in ("reason", "diagnosis", "next_approach", "evidence"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                renew(spend(renewable()), **{field: ""})

    def test_missing_renewal_authority_is_not_inferred(self):
        for value in (None, "", True):
            state = renewable(); state["repair_renewal_authority"] = value
            self.assertEqual(decision(state), "PAUSE_REPAIR_RENEWAL_AUTHORITY")

    def test_no_authority_task_scope_or_role_bypass(self):
        for changes in ({"current_task_id": "other"}, {"current_scope_fingerprint": "other"},
                        {"current_model": "gpt-5.6-luna"}, {"current_model": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                renew(spend(renewable()), **changes)
        for changes in ({"approval_evidence": None}, {"authority_envelope": None},
                        {"approved_scope": None}, {"approval_scope_fingerprint": "old"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                renew({**spend(renewable()), **changes})

    def test_hard_stops_are_not_reset(self):
        for stop in ("RESOURCE_BUDGET_EXHAUSTED", "OUTSIDE_AUTHORITY_ENVELOPE", "EXTERNAL_SIDE_EFFECT"):
            state = spend(renewable()); state["stop_condition"] = stop
            self.assertEqual(decision(state), "PAUSE_STOP_CONDITION")
            with self.assertRaises(ValueError):
                renew(state)

    def test_manual_failed_check_still_pauses(self):
        state = spend(renewable()); state.update(autonomy_mode="MANUAL", auto_transition_log=[])
        state["acceptance_contract"][0].update(status="FAIL", evidence="TEST ONLY: failed.log")
        self.assertEqual(decision(state), "PAUSE_CHECK_FAILED")
        with self.assertRaises(ValueError):
            renew(state)

    def test_closed_and_planning_runs_cannot_renew(self):
        for stage in ("ANALYZE", "REFINE"):
            state = spend(renewable()); count = 0 if stage == "ANALYZE" else 1
            state.update(workflow_stage=stage, auto_transition_log=state["auto_transition_log"][:count])
            with self.assertRaises(ValueError):
                renew(state)
        with self.assertRaises(ValueError):
            renew({**spend(renewable()), "run_status": "CLOSED"})

    def test_completion_at_threshold_needs_no_reset(self):
        state = spend(renewable(), 3, 6)
        state["acceptance_contract"][0].update(status="PASS", evidence="TEST ONLY: delivered artifact QA")
        self.assertEqual(decision(state, completion=True), "COMPLETE_READY")
        with self.assertRaisesRegex(ValueError, "already achieved"):
            renew(state)

    def test_deleted_receipts_and_reset_lifetime_totals_rejected(self):
        state = renew(spend(renewable()))
        for changes in ({"repair_cycle_log": []}, {"total_repair_attempts": 0},
                        {"repair_cycle_attempts": 1}, {"repair_budget_mode": "FIXED"}):
            self.assertTrue(decision({**state, **changes}).startswith("INVALID_"))

    def test_receipt_structure_and_counts_are_strict(self):
        state = renew(spend(renewable()))
        for field, value in (("cycle_id", True), ("cycle_id", 2), ("cycle_attempts", 0),
                             ("issue_attempts", 4), ("total_repair_attempts", 0),
                             ("task_id", "other"), ("evidence", ""), ("diagnosis", None)):
            changed = copy.deepcopy(state); changed["repair_cycle_log"][0][field] = value
            self.assertEqual(decision(changed), "INVALID_REPAIR_RENEWAL")
        for value in (True, 0.5, "1", -1):
            self.assertEqual(decision({**renewable(), "repair_cycle_attempts": value}), "INVALID_REPAIR_COUNTER")

    def test_both_sol_models_can_renew(self):
        for model in ("gpt-5.6-sol", "gpt-6.1-sol"):
            self.assertEqual(decision(renew(spend(renewable()), current_model=model), current_model=model), "CONTINUE_EXECUTE")

    def test_cli_review_renewed_and_complete_states(self):
        script = Path(__file__).with_name("validate_run_state.py")
        with tempfile.TemporaryDirectory(prefix="repair-ledger-") as tmp:
            state_path = Path(tmp) / "state.json"
            command = [sys.executable, str(script), "--state", str(state_path),
                       "--current-task-id", "fixture", "--scope-fingerprint", "fixture-scope",
                       "--current-model", "gpt-5.6-sol"]
            before = spend(renewable())
            for state, expected, code in ((before, "REVIEW_REPAIR_CYCLE", 1),
                    (renew(before), "CONTINUE_EXECUTE", 0)):
                state_path.write_text(json.dumps(state))
                outcome = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(outcome.returncode, code, outcome.stderr)
                self.assertEqual(json.loads(outcome.stdout)["decision"], expected)


if __name__ == "__main__":
    unittest.main()
