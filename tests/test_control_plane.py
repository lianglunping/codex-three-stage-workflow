"""Portable end-to-end control-plane contracts."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[1] / "skills" / "staged-agent-run-protocol"
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: object, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    actual_env = os.environ.copy()
    if env:
        actual_env.update(env)
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], text=True, capture_output=True, env=actual_env)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_state(root: Path, revision: str = "r0000") -> None:
    (root / "metadata").mkdir(parents=True, exist_ok=True)
    (root / "metadata/coordination.yaml").write_text(
        f"coordination_epoch: 0\ncanonical_revision: {revision}\nsealed_revision: \nsealed_scope_fingerprint: \nlast_manifest_sha256: \n",
        encoding="utf-8",
    )


def sealed_audit_fixture(root: Path, verdict: str = "Ready", gates: tuple[str, ...] = ("seal=verified",), finding: str = "F1\tInfo\tresolved\tseal\tevidence", auditor_model: str = "gpt-5.6-sol") -> tuple[Path, Path, str]:
    """Create a real, immediately-verifiable sealed revision and auditor."""
    sys.path.insert(0, str(SCRIPTS))
    from sar_utils import AGENT_ASSIGNMENT_HEADER, REVISION_MANIFEST_HEADER, write_tsv
    canonical = (root / "canonical").resolve(); canonical.write_text("canonical", encoding="utf-8")
    manifest = root / "coordination/revisions/r0000/revision_manifest.tsv"
    write_tsv(manifest, REVISION_MANIFEST_HEADER, [{"revision_id": "r0000", "path": str(canonical), "file_role": "canonical", "size_bytes": canonical.stat().st_size, "modified_time_ns": canonical.stat().st_mtime_ns, "sha256": digest(canonical), "semantic_fingerprint": "", "equivalence_rule": "byte_sha256", "source_assignment_id": "", "status": "Observed", "notes": ""}])
    manifest_sha = digest(manifest); (manifest.parent / "seal.yaml").write_text(f"revision_id: r0000\nmanifest_sha256: {manifest_sha}\nscope_fingerprint: scope\nstatus: SEALED\n", encoding="utf-8")
    (root / "metadata/coordination.yaml").write_text(f"coordination_epoch: 0\ncanonical_revision: r0000\nsealed_revision: r0000\nsealed_scope_fingerprint: scope\nlast_manifest_sha256: {manifest_sha}\n", encoding="utf-8")
    report = root / "report.md"; report.write_text("report", encoding="utf-8")
    findings = root / "findings.tsv"; findings.write_text("finding_id\tseverity\tstatus\tgate\tevidence_path\n" + finding + "\n", encoding="utf-8")
    gate_map = dict(item.split("=", 1) for item in gates); gate_sha = hashlib.sha256("".join(f"{k}={gate_map[k]}\n" for k in sorted(gate_map)).encode()).hexdigest()
    return_fp = hashlib.sha256((digest(report) + "\n" + digest(findings) + "\n" + verdict + "\n" + gate_sha + "\n").encode()).hexdigest()
    write_tsv(root / "coordination/agent_assignments.tsv", AGENT_ASSIGNMENT_HEADER, [{"assignment_id": "auditor", "agent_path": "/root/auditor", "parent_agent": "", "role": "AUDITOR", "model": auditor_model, "base_revision": "r0000", "read_scope": "", "write_scope": "", "forbidden_paths": "", "expected_outputs": "", "status": "Completed", "started_time": "", "finished_time": "now", "return_fingerprint": return_fp, "notes": ""}])
    return report, findings, return_fp


def issue_args(root: Path, report: Path, findings: Path, verdict: str = "Ready", gates: tuple[str, ...] = ("seal=verified",)) -> list[object]:
    args: list[object] = ["issue", "--run-dir", root, "--receipt-id", "receipt", "--audit-type", "audit", "--revision-id", "r0000", "--scope-fingerprint", "scope", "--auditor", "/root/auditor", "--verdict", verdict, "--finding-fingerprint", digest(findings), "--auditor-assignment-id", "auditor", "--audit-report-path", report, "--findings-path", findings]
    for gate in gates: args += ["--gate-status", gate]
    return args


def assignment(root: Path, assignment_id: str = "writer", status: str = "Running", fingerprint: str = "") -> subprocess.CompletedProcess[str]:
    args = ["--run-dir", root, "--assignment-id", assignment_id, "--agent-path", f"/root/{assignment_id}", "--role", "STAGING_WRITER", "--model", "gpt-5.6-terra", "--base-revision", "r0000", "--write-scope", root / "coordination/staging" / assignment_id, "--status", status]
    if fingerprint:
        args += ["--return-fingerprint", fingerprint]
    return run("register_agent_assignment.py", *args)


class ControlPlaneBehavior(unittest.TestCase):
    def test_dynamic_auditor_evidence_survives_manifest_and_receipt_checks(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root)
            report, findings, fingerprint = sealed_audit_fixture(root)
            (root / "coordination/agent_assignments.tsv").unlink()
            runtime = root / "runtime.json"
            capabilities = root / "capabilities.json"
            runtime.write_text(json.dumps({"source": "TEST ONLY runtime observation",
                "observed_at": "2026-11-05", "available_models": ["future-audit-model"],
                "delegation_tool_available": True}), encoding="utf-8")
            capabilities.write_text(json.dumps({"source": "TEST ONLY independent assessment",
                "observed_at": "2026-11-05", "models": {"future-audit-model": ["audit"]}}), encoding="utf-8")
            registered = run("register_agent_assignment.py", "--run-dir", root,
                "--assignment-id", "auditor", "--agent-path", "/root/auditor",
                "--role", "AUDITOR", "--model", "future-audit-model",
                "--base-revision", "r0000", "--status", "Completed",
                "--return-fingerprint", fingerprint, "--workflow-stage", "EXECUTE",
                "--runtime-evidence", runtime, "--capability-evidence", capabilities,
                "--delegation-authorized", "--delegation-evidence", "TEST ONLY user authorization")
            self.assertEqual(registered.returncode, 0, registered.stdout + registered.stderr)
            issued = run("audit_receipt.py", *issue_args(root, report, findings))
            self.assertEqual(issued.returncode, 0, issued.stdout + issued.stderr)
            checked = run("check_manifest.py", "--run-dir", root)
            self.assertNotIn("assignment_invalid_model_role", checked.stdout + checked.stderr)
            capabilities.write_text("{}", encoding="utf-8")
            checked = run("check_manifest.py", "--run-dir", root)
            self.assertIn("assignment_invalid_model_role", checked.stdout + checked.stderr)
            rejected = run("audit_receipt.py", "validate", "--run-dir", root, "--receipt-id", "receipt")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("auditor_model_role_incompatible", rejected.stdout + rejected.stderr)

    def test_assignment_terra_running_and_second_writer_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root)
            self.assertEqual(assignment(root).returncode, 0)
            self.assertNotEqual(assignment(root, "writer2").returncode, 0)

    def test_assignment_completed_requires_fingerprint_and_cannot_reopen(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root); self.assertEqual(assignment(root).returncode, 0)
            self.assertNotEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Completed", "--update").returncode, 0)
            self.assertEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Completed", "--return-fingerprint", "a" * 64, "--update").returncode, 0)
            self.assertNotEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Running", "--update").returncode, 0)

    def test_assignment_new_completed_requires_fingerprint_and_update_model_is_immutable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root)
            self.assertNotEqual(assignment(root, status="Completed").returncode, 0)
            self.assertEqual(assignment(root).returncode, 0)
            self.assertEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Running", "--update").returncode, 0)
            self.assertNotEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Running", "--model", "future-model", "--update").returncode, 0)

    def _integration_root(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        holder = tempfile.TemporaryDirectory(); root = Path(holder.name); write_state(root)
        self.assertEqual(assignment(root).returncode, 0)
        stage = root / "coordination/staging/writer"; stage.mkdir(parents=True); source = stage / "out.txt"; source.write_text("staged", encoding="utf-8")
        target = root / "canonical.txt"; target.write_text("old", encoding="utf-8")
        return holder, root, target

    def _integrate(self, root: Path, manifest: Path, fp: str) -> subprocess.CompletedProcess[str]:
        self.assertEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Completed", "--return-fingerprint", fp, "--update").returncode, 0)
        return run("record_integration.py", "--run-dir", root, "--event-id", "i1", "--assignment-id", "writer", "--base-revision", "r0000", "--staged-manifest-sha256", digest(manifest), "--decision", "integrated")

    def test_integration_requires_manifest_fingerprint_equal_assignment_return(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}), encoding="utf-8")
            result = self._integrate(root, manifest, "b" * 64)
            self.assertNotEqual(result.returncode, 0); self.assertIn("return", result.stdout.lower())
            self.assertIn("canonical_revision: r0000", (root / "metadata/coordination.yaml").read_text())

    def test_integration_rejects_changed_source_and_invalid_manifest_schema(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": str(target), "pre_sha256": digest(target), "source_sha256": "A" * 64}]}), encoding="utf-8")
            self.assertNotEqual(self._integrate(root, manifest, digest(manifest)).returncode, 0)

    def test_integration_valid_manifest_advances_to_r0001(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}), encoding="utf-8")
            self.assertEqual(self._integrate(root, manifest, digest(manifest)).returncode, 0)
            self.assertIn("canonical_revision: r0001", (root / "metadata/coordination.yaml").read_text())

    def test_integration_applies_bundle_before_recording_event_and_revision(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}), encoding="utf-8")
            self.assertEqual(self._integrate(root, manifest, digest(manifest)).returncode, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "staged")
            events = (root / "coordination/integration_events.tsv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 2)
            self.assertIn("\tr0001\t", events[1])

    def test_integration_cas_failure_keeps_target_event_and_revision_unchanged(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}), encoding="utf-8")
            target.write_text("raced", encoding="utf-8")
            result = self._integrate(root, manifest, digest(manifest))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "raced")
            self.assertFalse((root / "coordination/integration_events.tsv").exists())
            self.assertIn("canonical_revision: r0000", (root / "metadata/coordination.yaml").read_text())

    def test_integration_rejects_relative_target_without_target_event_or_revision_change(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": os.path.relpath(target, Path.cwd()), "pre_sha256": digest(target), "source_sha256": digest(source)}]}), encoding="utf-8")
            result = self._integrate(root, manifest, digest(manifest))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "old")
            self.assertFalse((root / "coordination/integration_events.tsv").exists())
            self.assertIn("canonical_revision: r0000", (root / "metadata/coordination.yaml").read_text())

    def test_integration_rejects_manifest_drift_after_prepare_without_target_event_or_revision_change(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}), encoding="utf-8")
            self.assertEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Completed", "--return-fingerprint", digest(manifest), "--update").returncode, 0)
            proc = subprocess.Popen([sys.executable, str(SCRIPTS / "record_integration.py"), "--run-dir", str(root), "--event-id", "i1", "--assignment-id", "writer", "--base-revision", "r0000", "--staged-manifest-sha256", digest(manifest), "--decision", "integrated"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, "STAGED_BUNDLE_TEST_DELAY": "1"})
            deadline = time.time() + 2
            while not list(root.glob(".canonical.txt.*")) and time.time() < deadline:
                time.sleep(.05)
            self.assertTrue(list(root.glob(".canonical.txt.*")))
            manifest.write_text(manifest.read_text(encoding="utf-8") + " \n", encoding="utf-8")
            proc.communicate(timeout=5)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "old")
            self.assertFalse((root / "coordination/integration_events.tsv").exists())
            self.assertIn("canonical_revision: r0000", (root / "metadata/coordination.yaml").read_text())
            self.assertFalse(list(root.glob(".canonical.txt.*")))

    def test_concurrent_integrations_allow_one_consistent_commit(self):
        holder, root, target = self._integration_root()
        with holder:
            stage = root / "coordination/staging/writer"; source = stage / "out.txt"; manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"source": "out.txt", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}), encoding="utf-8")
            self.assertEqual(run("register_agent_assignment.py", "--run-dir", root, "--assignment-id", "writer", "--status", "Completed", "--return-fingerprint", digest(manifest), "--update").returncode, 0)
            common = [sys.executable, str(SCRIPTS / "record_integration.py"), "--run-dir", str(root), "--assignment-id", "writer", "--base-revision", "r0000", "--staged-manifest-sha256", digest(manifest), "--decision", "integrated"]
            first = subprocess.Popen([*common, "--event-id", "i1"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            second = subprocess.Popen([*common, "--event-id", "i2"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            first.communicate(timeout=10); second.communicate(timeout=10)
            self.assertEqual(sorted([first.returncode, second.returncode]), [0, 1])
            self.assertEqual(target.read_text(encoding="utf-8"), "staged")
            self.assertIn("canonical_revision: r0001", (root / "metadata/coordination.yaml").read_text())
            self.assertEqual(len((root / "coordination/integration_events.tsv").read_text(encoding="utf-8").splitlines()), 2)

    def test_bundle_rejects_source_race_without_target_or_temp_artifacts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); bundle = root / "bundle"; bundle.mkdir(); source = bundle / "x"; source.write_text("new")
            target = root / "target"; target.write_text("old")
            manifest = root / "manifest.json"; manifest.write_text(json.dumps({"files": [{"source": "x", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}))
            proc = subprocess.Popen([sys.executable, str(SCRIPTS / "apply_staged_bundle.py"), "--bundle", str(bundle), "--manifest", str(manifest)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, "STAGED_BUNDLE_TEST_DELAY": "1"})
            time.sleep(.2); source.write_text("raced"); proc.communicate(timeout=5)
            self.assertNotEqual(proc.returncode, 0); self.assertEqual(target.read_text(), "old"); self.assertFalse(list(root.glob(".target.*")))

    def test_bundle_success_leaves_no_target_temp(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); bundle = root / "bundle"; bundle.mkdir(); source = bundle / "x"; source.write_text("new")
            target = root / "target"; target.write_text("old")
            manifest = root / "manifest.json"; manifest.write_text(json.dumps({"files": [{"source": "x", "target": str(target), "pre_sha256": digest(target), "source_sha256": digest(source)}]}))
            self.assertEqual(run("apply_staged_bundle.py", "--bundle", bundle, "--manifest", manifest).returncode, 0); self.assertEqual(target.read_text(), "new"); self.assertFalse(list(root.glob(".target.*")))

    def test_bundle_rejects_relative_target_without_changing_target(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); bundle = root / "bundle"; bundle.mkdir(); source = bundle / "x"; source.write_text("new")
            target = root / "target"; target.write_text("old")
            manifest = root / "manifest.json"; manifest.write_text(json.dumps({"files": [{"source": "x", "target": os.path.relpath(target, Path.cwd()), "pre_sha256": digest(target), "source_sha256": digest(source)}]}))
            result = run("apply_staged_bundle.py", "--bundle", bundle, "--manifest", manifest)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), "old")

    def test_snapshot_seal_detects_late_write_and_stable_seal_verifies_metadata_only(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root); canonical = root / "canonical"; canonical.write_text("same")
            self.assertEqual(run("snapshot_revision.py", "snapshot", "--run-dir", root, "--snapshot-id", "s1", "--scope", canonical).returncode, 0)
            snapshot = root / "coordination/snapshots/s1.tsv"
            proc = subprocess.Popen([sys.executable, str(SCRIPTS / "snapshot_revision.py"), "seal", "--run-dir", str(root), "--revision-id", "r0000", "--scope-fingerprint", "scope", "--previous", str(snapshot), "--scope", str(canonical), "--stability-seconds", "5"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(1); canonical.write_text("late"); proc.communicate(timeout=10)
            self.assertNotEqual(proc.returncode, 0); self.assertFalse((root / "coordination/revisions/r0000/seal.yaml").exists())
            self.assertEqual(run("snapshot_revision.py", "snapshot", "--run-dir", root, "--snapshot-id", "s2", "--scope", canonical).returncode, 0)
            self.assertEqual(run("snapshot_revision.py", "seal", "--run-dir", root, "--revision-id", "r0000", "--scope-fingerprint", "scope", "--previous", root / "coordination/snapshots/s2.tsv", "--scope", canonical, "--stability-seconds", "5").returncode, 0)
            os.utime(canonical, None); verified = run("snapshot_revision.py", "verify", "--run-dir", root, "--revision-id", "r0000")
            self.assertEqual(verified.returncode, 0); self.assertIn("VERIFIED_METADATA_ONLY", verified.stdout)
            canonical.write_text("changed"); self.assertNotEqual(run("snapshot_revision.py", "verify", "--run-dir", root, "--revision-id", "r0000").returncode, 0)

    def test_audit_receipt_cli_rejects_unverified_ready_and_requires_gates(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root); report = root / "report.md"; findings = root / "findings.tsv"; report.write_text("report"); findings.write_text("finding_id\tseverity\tstatus\tgate\tevidence_path\nF1\tInfo\tresolved\tseal\tevidence\n")
            result = run("audit_receipt.py", "issue", "--run-dir", root, "--receipt-id", "a1", "--audit-type", "audit", "--revision-id", "r0000", "--scope-fingerprint", "scope", "--auditor", "/root/auditor", "--verdict", "Ready", "--finding-fingerprint", digest(findings), "--auditor-assignment-id", "auditor", "--audit-report-path", report, "--findings-path", findings, "--gate-status", "seal=unverified")
            self.assertNotEqual(result.returncode, 0)

    def test_audit_receipt_issues_and_validates_ready_with_bound_auditor(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root); report, findings, _ = sealed_audit_fixture(root)
            self.assertEqual(run("audit_receipt.py", *issue_args(root, report, findings)).returncode, 0)
            self.assertEqual(run("audit_receipt.py", "validate", "--run-dir", root, "--receipt-id", "receipt").returncode, 0)

    def test_audit_receipt_rejects_terra_auditor_not_allowed_by_runtime_policy(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root); report, findings, _ = sealed_audit_fixture(root, auditor_model="gpt-5.6-terra")
            result = run("audit_receipt.py", *issue_args(root, report, findings))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("model", result.stdout.lower())

    def test_audit_receipt_rejects_unregistered_wrong_identity_and_return_fingerprint(self):
        for mutation in ("unregistered", "identity", "fingerprint"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw:
                root = Path(raw); write_state(root); report, findings, _ = sealed_audit_fixture(root)
                assignment_file = root / "coordination/agent_assignments.tsv"
                text = assignment_file.read_text()
                if mutation == "unregistered": text = text.splitlines()[0] + "\n"
                elif mutation == "identity": text = text.replace("/root/auditor", "/root/not-auditor")
                else: text = text.replace("\t" + hashlib.sha256((digest(report) + "\n" + digest(findings) + "\nReady\n" + hashlib.sha256(b"seal=verified\n").hexdigest() + "\n").encode()).hexdigest() + "\t", "\t" + "0" * 64 + "\t")
                assignment_file.write_text(text)
                self.assertNotEqual(run("audit_receipt.py", *issue_args(root, report, findings)).returncode, 0)

    def test_audit_receipt_rejects_ready_with_unresolved_major(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root); report, findings, _ = sealed_audit_fixture(root, finding="F1\tMajor\tunresolved\tseal\tevidence")
            self.assertNotEqual(run("audit_receipt.py", *issue_args(root, report, findings)).returncode, 0)

    def test_audit_receipt_invalidates_report_and_findings_drift(self):
        for path_kind in ("report", "findings"):
            with self.subTest(path_kind=path_kind), tempfile.TemporaryDirectory() as raw:
                root = Path(raw); write_state(root); report, findings, _ = sealed_audit_fixture(root)
                self.assertEqual(run("audit_receipt.py", *issue_args(root, report, findings)).returncode, 0)
                (report if path_kind == "report" else findings).write_text("drift", encoding="utf-8")
                self.assertNotEqual(run("audit_receipt.py", "validate", "--run-dir", root, "--receipt-id", "receipt").returncode, 0)
                self.assertIn("Invalid", (root / "coordination/audit_receipts.tsv").read_text())

    def test_audit_receipt_invalidates_late_canonical_write(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_state(root); report, findings, _ = sealed_audit_fixture(root)
            self.assertEqual(run("audit_receipt.py", *issue_args(root, report, findings)).returncode, 0)
            (root / "canonical").write_text("late", encoding="utf-8")
            self.assertNotEqual(run("audit_receipt.py", "validate", "--run-dir", root, "--receipt-id", "receipt").returncode, 0)

    def test_check_manifest_read_only_revalidates_valid_receipt_drift(self):
        for drift in ("report", "late_canonical"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as raw:
                outer = Path(raw)
                initialized = subprocess.run([sys.executable, str(SCRIPTS / "init_agent_run.py"), "--task-name", "control", "--root", str(outer), "--profile", "lite"], text=True, capture_output=True)
                self.assertEqual(initialized.returncode, 0); root = Path(initialized.stdout.strip())
                report, findings, _ = sealed_audit_fixture(root)
                self.assertEqual(run("audit_receipt.py", *issue_args(root, report, findings)).returncode, 0)
                (report if drift == "report" else root / "canonical").write_text("drift", encoding="utf-8")
                checked = run("check_manifest.py", "--run-dir", root)
                self.assertNotEqual(checked.returncode, 0)
                self.assertIn("audit_receipt_live_revalidation_failed", checked.stdout)
                self.assertIn("Valid", (root / "coordination/audit_receipts.tsv").read_text())

    def test_migration_preserves_unknown_columns_and_existing_backup(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); path = root / "coordination/agent_assignments.tsv"; path.parent.mkdir(parents=True); path.write_text("assignment_id\tlegacy\nA\tkept\n")
            backup = path.with_suffix(".tsv.pre_migration.bak"); backup.write_text("sentinel")
            self.assertEqual(run("migrate_coordination_schema.py", "--run-dir", root).returncode, 0)
            first = path.read_bytes(); backup_sha = digest(backup)
            self.assertIn("legacy", path.read_text()); self.assertEqual(run("migrate_coordination_schema.py", "--run-dir", root).returncode, 0)
            self.assertEqual(first, path.read_bytes()); self.assertEqual(backup_sha, digest(backup))

if __name__ == "__main__":
    unittest.main()
