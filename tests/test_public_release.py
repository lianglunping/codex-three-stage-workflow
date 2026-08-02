from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "audit_public_release.py"


def run_audit(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(AUDITOR), str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def minimal_release(root: Path) -> None:
    (root / "LICENSE").write_text("Apache License\n", encoding="utf-8")
    (root / "VERSION").write_text("0.1.0\n", encoding="utf-8")


class PublicReleaseAuditTests(unittest.TestCase):
    def test_clean_minimal_release_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimal_release(root)
            result = run_audit(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS PUBLIC_RELEASE_AUDIT", result.stdout)

    def test_personal_absolute_path_is_rejected_without_echoing_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimal_release(root)
            personal = "/" + "Users" + "/" + "private-person" + "/data"
            (root / "bad.txt").write_text(personal, encoding="utf-8")
            result = run_audit(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PERSONAL_ABSOLUTE_PATH", result.stderr)
            self.assertNotIn("private-person", result.stderr)

    def test_session_backup_and_secret_patterns_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimal_release(root)
            session = ".codex/" + "sessions" + "/2026/run.jsonl"
            backup = ".codex/" + "backups" + "/private"
            token = "ghp" + "_" + ("A" * 36)
            (root / "bad.txt").write_text(
                "\n".join((session, backup, token)), encoding="utf-8"
            )
            result = run_audit(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("CODEX_SESSION_PATH", result.stderr)
            self.assertIn("CODEX_BACKUP_PATH", result.stderr)
            self.assertIn("POSSIBLE_SECRET", result.stderr)
            self.assertNotIn(token, result.stderr)

    def test_session_identifier_is_rejected_without_echoing_identifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimal_release(root)
            identifier = "019" + "abcde-1234-5678-9abc-123456789abc"
            (root / "bad.txt").write_text(identifier, encoding="utf-8")
            result = run_audit(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SESSION_IDENTIFIER", result.stderr)
            self.assertNotIn(identifier, result.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unsupported")
    def test_broken_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimal_release(root)
            (root / "broken").symlink_to(root / "missing")
            result = run_audit(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("BROKEN_SYMLINK", result.stderr)

    def test_missing_license_and_version_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_audit(Path(tmp))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MISSING_LICENSE", result.stderr)
            self.assertIn("MISSING_VERSION", result.stderr)

    def test_duplicate_manifest_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimal_release(root)
            license_hash = hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest()
            version_hash = hashlib.sha256((root / "VERSION").read_bytes()).hexdigest()
            (root / "MANIFEST.sha256").write_text(
                f"{license_hash}  LICENSE\n"
                f"{license_hash}  LICENSE\n"
                f"{version_hash}  VERSION\n",
                encoding="utf-8",
            )
            result = run_audit(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("DUPLICATE_MANIFEST_PATH", result.stderr)

    def test_current_repository_passes_public_boundary_audit(self):
        result = run_audit(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
