from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"


def run_installer(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(INSTALLER), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def digest_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class InstallerTests(unittest.TestCase):
    def test_default_dry_run_does_not_mutate_codex_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "codex-home"
            home.mkdir()
            marker = home / "marker.txt"
            marker.write_text("unchanged\n", encoding="utf-8")
            before = digest_tree(home)
            result = run_installer("--codex-home", str(home))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(digest_tree(home), before)
            self.assertIn("DRY_RUN", result.stdout)

    def test_dry_run_describes_strict_hook_as_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "codex-home"
            result = run_installer("--codex-home", str(home))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("OPTIONAL_STRICT_HOOK", result.stdout)
            self.assertNotIn("MANUAL_MERGE " + str(ROOT / "examples" / "hooks.json"), result.stdout)

    def test_apply_installs_exact_public_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "codex-home"
            result = run_installer("--codex-home", str(home), "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = {
                "agents/deterministic_validator.toml",
                "agents/revision_auditor.toml",
                "agents/three_stage_analyzer.toml",
                "agents/three_stage_refiner.toml",
                "hooks/three_stage_write_guard.py",
                "policies/three-stage-runtime-v1.json",
            }
            expected.update(
                f"skills/{name}/SKILL.md"
                for name in (
                    "three-stage-complex-workflow",
                    "staged-agent-run-protocol",
                    "dispatching-parallel-agents",
                    "project-audit",
                )
            )
            installed = {
                str(path.relative_to(home))
                for path in home.rglob("*")
                if path.is_file()
                and "backups/codex-three-stage-workflow" not in str(path)
            }
            self.assertTrue(expected.issubset(installed))
            self.assertFalse((home / "config.toml").exists())
            self.assertFalse((home / "hooks.json").exists())

    def test_apply_preserves_every_installed_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "codex-home"
            result = run_installer("--codex-home", str(home), "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            mappings = [
                (ROOT / "skills", home / "skills"),
                (ROOT / "runtime" / "agents", home / "agents"),
                (ROOT / "runtime" / "hooks", home / "hooks"),
                (ROOT / "runtime" / "policies", home / "policies"),
            ]
            for source_root, target_root in mappings:
                for source in source_root.rglob("*"):
                    if not source.is_file() or "__pycache__" in source.parts:
                        continue
                    target = target_root / source.relative_to(source_root)
                    self.assertTrue(target.is_file(), target)
                    self.assertEqual(
                        hashlib.sha256(target.read_bytes()).hexdigest(),
                        hashlib.sha256(source.read_bytes()).hexdigest(),
                        target,
                    )

    def test_apply_backs_up_existing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "codex-home"
            target = home / "policies" / "three-stage-runtime-v1.json"
            target.parent.mkdir(parents=True)
            target.write_text("old-policy\n", encoding="utf-8")
            result = run_installer("--codex-home", str(home), "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            backups = list(
                (home / "backups" / "codex-three-stage-workflow").glob(
                    "*/policies/three-stage-runtime-v1.json"
                )
            )
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "old-policy\n")

    def test_missing_source_fails_without_partial_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp) / "repo"
            (fake_root / "scripts").mkdir(parents=True)
            shutil.copy2(INSTALLER, fake_root / "scripts" / "install.py")
            home = Path(tmp) / "codex-home"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(fake_root / "scripts" / "install.py"),
                    "--codex-home",
                    str(home),
                    "--apply",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MISSING_SOURCE", result.stderr)
            self.assertFalse(home.exists())

    def test_filesystem_root_is_rejected_as_codex_home(self):
        result = run_installer("--codex-home", str(Path("/")))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNSAFE_CODEX_HOME", result.stderr)


if __name__ == "__main__":
    unittest.main()
