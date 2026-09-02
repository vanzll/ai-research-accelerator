import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "plugins/ai-research-accelerator/skills/multinode-training/scripts"
    / "validate_production_runtime.py"
)
SPEC = importlib.util.spec_from_file_location("production_runtime_validator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ProductionRuntimeValidatorTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self.git_run("init", "-b", "main")
        self.git_run("config", "user.email", "test@example.com")
        self.git_run("config", "user.name", "Test User")
        (self.repo / "tests").mkdir()
        (self.repo / "runners/profile").mkdir(parents=True)
        (self.repo / "tests/test_transport.py").write_text("# regression\n")
        self.contract = b'{"algorithm":"example"}\n'
        (self.repo / "runners/profile/science_contract.json").write_bytes(
            self.contract
        )
        self.git_run("add", ".")
        self.git_run("commit", "-m", "production runtime")
        self.base = self.git_run("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.tempdir.cleanup()

    def git_run(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def manifest(self):
        return {
            "schema_version": 1,
            "runtime_id": "runtime-v1",
            "canonical_runtime_commit": self.base,
            "accepted_runtime": {
                "commit": self.base,
                "evidence_paths": ["shared/attempt/acceptance.json"],
            },
            "fixes": [
                {
                    "id": "transport-fix",
                    "status": "promoted",
                    "promoted_commit": self.base,
                    "source_evidence_paths": ["shared/attempt/retrospective.md"],
                    "regression_tests": ["tests/test_transport.py"],
                    "required_for_profiles": ["*"],
                }
            ],
            "profiles": [
                {
                    "id": "profile",
                    "production_base_commit": self.base,
                    "required_fix_ids": ["transport-fix"],
                    "science_contract_path": "runners/profile/science_contract.json",
                    "science_contract_sha256": hashlib.sha256(
                        self.contract
                    ).hexdigest(),
                }
            ],
        }

    def validate(self, manifest=None, require_clean=False):
        return MODULE.validate(
            manifest or self.manifest(),
            repo=self.repo,
            profile_id="profile",
            candidate=self.base,
            require_clean=require_clean,
        )

    def test_accepts_promoted_fix_and_matching_contract(self):
        result = self.validate(require_clean=True)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["validated_fix_ids"], ["transport-fix"])

    def test_rejects_profile_that_omits_global_fix(self):
        manifest = self.manifest()
        manifest["profiles"][0]["required_fix_ids"] = ["different-fix"]
        with self.assertRaisesRegex(MODULE.ValidationError, "omits applicable"):
            self.validate(manifest)

    def test_rejects_non_ancestor_promotion_commit(self):
        self.git_run("checkout", "-b", "side")
        (self.repo / "side.txt").write_text("side\n")
        self.git_run("add", "side.txt")
        self.git_run("commit", "-m", "side repair")
        side = self.git_run("rev-parse", "HEAD").strip()
        self.git_run("checkout", "main")
        manifest = self.manifest()
        manifest["fixes"][0]["promoted_commit"] = side
        with self.assertRaisesRegex(MODULE.ValidationError, "is not an ancestor"):
            self.validate(manifest)

    def test_rejects_science_contract_hash_mismatch(self):
        manifest = self.manifest()
        manifest["profiles"][0]["science_contract_sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.ValidationError, "hash mismatch"):
            self.validate(manifest)

    def test_rejects_dirty_release_checkout(self):
        (self.repo / "dirty.txt").write_text("dirty\n")
        with self.assertRaisesRegex(MODULE.ValidationError, "must be clean"):
            self.validate(require_clean=True)

    def test_cli_returns_structured_failure(self):
        manifest_path = self.repo / "manifest.json"
        manifest = self.manifest()
        manifest["profiles"][0]["science_contract_sha256"] = "f" * 64
        manifest_path.write_text(json.dumps(manifest))
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--manifest",
                str(manifest_path),
                "--repo",
                str(self.repo),
                "--profile",
                "profile",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["accepted"])


if __name__ == "__main__":
    unittest.main()
