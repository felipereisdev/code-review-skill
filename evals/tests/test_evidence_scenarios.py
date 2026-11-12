"""Execute the new scenario artifacts, not an agent or the skill's prose.

These checks ensure that a future behavioral study has real bugs and controls.
They do not measure whether a model discovers them or obeys the updated skill.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios" / "evidence-driven"
FIXTURES = SCENARIOS / "fixtures"


def load_module(relative):
    path = FIXTURES / relative
    spec = importlib.util.spec_from_file_location(path.parent.name.replace("-", "_") + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(path, *args, cwd=None):
    return subprocess.run([sys.executable, "-B", str(path), *args], cwd=cwd, capture_output=True, text=True)


class EvidenceArtifactTest(unittest.TestCase):
    def test_fake_hides_real_producers_empty_encoding(self):
        consumer = load_module("mock-empty/consumer.py")
        fake = (FIXTURES / "mock-empty/fake.json").read_text()
        self.assertEqual(consumer.result_count(fake), 0)
        real = execute(FIXTURES / "mock-empty/producer.py")
        self.assertEqual(real.returncode, 0, real.stderr)
        self.assertEqual(json.loads(real.stdout), [])
        with self.assertRaises(TypeError):
            consumer.result_count(real.stdout)

    def test_nonempty_real_output_is_a_positive_control(self):
        consumer = load_module("mock-empty/consumer.py")
        real = execute(FIXTURES / "mock-empty/producer.py", "missing-owner")
        self.assertEqual(real.returncode, 0, real.stderr)
        self.assertEqual(consumer.result_count(real.stdout), 1)

    def test_same_required_rule_is_bypassed_by_warning_and_absence(self):
        policy = load_module("rule-routes/policy.py")
        config = lambda **extra: {"checks": [{"required": True, **extra}]}
        self.assertFalse(policy.accepted(config(severity="off")))
        self.assertTrue(policy.accepted(config(severity="warn")))
        self.assertTrue(policy.accepted(config()))

    def test_rule_keeps_valid_controls(self):
        policy = load_module("rule-routes/policy.py")
        self.assertTrue(policy.accepted({"checks": [{"required": True, "severity": "error"}]}))
        self.assertTrue(policy.accepted({"checks": [{"required": False, "severity": "off"}]}))

    def test_static_proof_fixture_has_a_concrete_missing_customer_failure(self):
        handler = load_module("static-proof/handler.py")
        with self.assertRaises(TypeError):
            handler.customer_name({}, 99)
        self.assertEqual(handler.customer_name({99: {"name": "Ada"}}, 99), "Ada")

    def test_current_suite_passes_while_original_probe_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            for source in (FIXTURES / "rereview").iterdir():
                shutil.copy2(source, temp)
            current = execute(Path(temp) / "current_test.py", cwd=temp)
            original = execute(Path(temp) / "original_probe.py", cwd=temp)
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertNotEqual(original.returncode, 0)
        self.assertIn('accepted("disabled") is False', original.stderr)


class MergeArtifactTest(unittest.TestCase):
    def test_both_pinned_tips_are_green_but_the_real_merge_is_red(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_AUTHOR_NAME="Evidence Eval", GIT_AUTHOR_EMAIL="eval@example.invalid",
                       GIT_COMMITTER_NAME="Evidence Eval", GIT_COMMITTER_EMAIL="eval@example.invalid")

            def git(*args):
                result = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, *args],
                                        cwd=repo, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout.strip()

            def overlay(name):
                for source in (FIXTURES / "merge" / name).iterdir():
                    shutil.copy2(source, repo)

            def suite():
                return subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-q"],
                                      cwd=repo, env=env, capture_output=True, text=True)

            git("init", "-b", "target")
            overlay("base")
            git("add", ".")
            git("commit", "-m", "base")
            git("switch", "-c", "feature")
            overlay("feature")
            git("add", ".")
            git("commit", "-m", "require explicit strictness")
            feature_sha = git("rev-parse", "HEAD")
            feature_result = suite()
            git("switch", "target")
            overlay("target")
            git("add", ".")
            git("commit", "-m", "add endpoint")
            target_sha = git("rev-parse", "HEAD")
            target_result = suite()
            git("switch", "--detach", target_sha)
            git("merge", "--no-commit", "--no-ff", feature_sha)
            merged_result = suite()

        self.assertEqual(feature_result.returncode, 0, feature_result.stderr)
        self.assertEqual(target_result.returncode, 0, target_result.stderr)
        self.assertNotEqual(feature_sha, target_sha)
        self.assertNotEqual(merged_result.returncode, 0)
        self.assertIn("missing 1 required keyword-only argument: 'strict'", merged_result.stderr)


if __name__ == "__main__":
    unittest.main()
