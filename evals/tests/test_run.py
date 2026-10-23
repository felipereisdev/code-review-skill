import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
EVALS = os.path.dirname(HERE)
RUN = os.path.join(EVALS, "run.py")
FIXTURES = os.path.join(HERE, "fixtures", "cases")
FAKE_AGENT = os.path.join(HERE, "fixtures", "fake_agent.sh")


def run(*args):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return subprocess.run([sys.executable, RUN, *args], cwd=tempfile.gettempdir(), env=env,
                          capture_output=True, text=True, timeout=120)


class ValidateTest(unittest.TestCase):
    def test_fixture_pair_is_valid(self):
        r = run("--validate", "--cases-dir", FIXTURES, "--cases", "demo/*")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK demo", r.stdout)
        self.assertIn("1 pair(s), 2 case(s): all valid", r.stdout)

    def test_coverage_required_without_filter(self):
        r = run("--validate", "--cases-dir", FIXTURES)
        self.assertEqual(r.returncode, 1)
        self.assertIn("need at least 6 pairs", r.stdout)

    def test_broken_patch_is_rejected(self):
        tmp = tempfile.mkdtemp()
        shutil.copytree(os.path.join(FIXTURES, "demo"), os.path.join(tmp, "demo"))
        with open(os.path.join(tmp, "demo", "bug.patch"), "w") as f:
            f.write("not a patch\n")
        r = run("--validate", "--cases-dir", tmp, "--cases", "demo/*")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL demo", r.stdout)

    def test_no_matching_cases(self):
        r = run("--validate", "--cases-dir", FIXTURES, "--cases", "nope/*")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no cases match", r.stdout + r.stderr)

    def broken_copy(self, pair_json_text=None):
        tmp = tempfile.mkdtemp()
        shutil.copytree(os.path.join(FIXTURES, "demo"), os.path.join(tmp, "demo"))
        if pair_json_text is not None:
            with open(os.path.join(tmp, "demo", "pair.json"), "w") as f:
                f.write(pair_json_text)
        return tmp

    def test_folder_without_pair_json_fails(self):
        tmp = self.broken_copy()
        os.makedirs(os.path.join(tmp, "unfinished", "base"))
        with open(os.path.join(tmp, "unfinished", "base", "x.py"), "w") as f:
            f.write("x = 1\n")
        r = run("--validate", "--cases-dir", tmp, "--cases", "*")
        self.assertEqual(r.returncode, 1)
        self.assertIn("OK demo", r.stdout)
        self.assertIn("FAIL unfinished: missing pair.json", r.stdout)

    def test_invalid_pair_json_fails(self):
        r = run("--validate", "--cases-dir", self.broken_copy('{"topic": '), "--cases", "demo/*")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL demo: invalid pair.json", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_missing_required_keys_fail(self):
        r = run("--validate", "--cases-dir", self.broken_copy('{"description": "x"}'), "--cases", "demo/*")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL demo: topic must be a non-empty string", r.stdout)
        self.assertIn("FAIL demo: stack must be a non-empty string", r.stdout)
        self.assertIn("FAIL demo: bug must be an object", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def run_demo(self, agent_cmd, *extra):
        return run("--cases-dir", FIXTURES, "--cases", "demo/*", "--out-dir", self.out,
                   "--agent-cmd", agent_cmd, *extra)

    def results(self):
        with open(os.path.join(self.out, "results.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_fake_agent_scores_both_cases(self):
        r = self.run_demo("bash " + FAKE_AGENT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = self.results()
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["metrics"], {"bug_cases": 1, "detected": 1, "recall": 1.0, "clean_cases": 1,
                                           "false_positive_cases": 0, "false_positive_findings": 0, "errors": 0})
        self.assertEqual([c["id"] for c in data["cases"]], ["demo/bug", "demo/clean"])
        bug, clean = data["cases"]
        self.assertTrue(bug["passed"])
        self.assertEqual(bug["matched_finding"], "Security — Critical")
        self.assertEqual(bug["findings"], [{"heading": "Security — Critical", "severity": "Critical",
                                            "needs_verification": False}])
        self.assertEqual(clean["false_positives"], 0)
        self.assertTrue(os.path.isfile(os.path.join(self.out, "reports", "demo__bug.md")))
        with open(os.path.join(self.out, "summary.md"), encoding="utf-8") as f:
            summary = f.read()
        self.assertIn("- Recall: 1/1 (100%)", summary)
        self.assertIn("| demo/clean | clean | python | ok | PASS |", summary)
        self.assertEqual(data["agent"]["mcp"], "unknown (custom agent command)")
        self.assertIn("- MCP/Context7: unknown (custom agent command)", summary)

    def test_agent_gets_prompt_on_stdin_and_skill_dir_env(self):
        r = self.run_demo('echo "SKILL_DIR=$EVAL_SKILL_DIR"; cat; echo; echo "Code review passed — no issues found."')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(os.path.join(self.out, "reports", "demo__bug.md"), encoding="utf-8") as f:
            report = f.read()
        self.assertIn("SKILL_DIR=" + os.path.dirname(EVALS), report)
        self.assertIn('option 2, "Staged changes only"', report)

    def test_failing_agent_is_an_error(self):
        r = self.run_demo("exit 3")
        self.assertEqual(r.returncode, 1)
        case = self.results()["cases"][0]
        self.assertEqual(case["status"], "error")
        self.assertIn("exited with 3", case["error"])
        self.assertFalse(case["passed"])

    def test_report_without_output_format_is_an_error(self):
        r = self.run_demo("echo 'What would you like to review?'")
        self.assertEqual(r.returncode, 1)
        data = self.results()
        self.assertEqual(data["cases"][1]["status"], "error")
        self.assertFalse(data["cases"][1]["passed"])
        self.assertEqual(data["metrics"]["errors"], 2)

    def test_non_review_outputs_are_errors(self):
        commands = {
            "bare summary": "cat > /dev/null; printf '## Summary\\n'",
            "question + summary": "cat > /dev/null; printf 'What would you like to review?\\n\\n## Summary\\n'",
            "prompt echo + summary": "cat; echo; echo '## Summary'",
        }
        for label, cmd in commands.items():
            with self.subTest(label):
                self.out = tempfile.mkdtemp()
                r = self.run_demo(cmd)
                self.assertEqual(r.returncode, 1)
                data = self.results()
                clean = data["cases"][1]
                self.assertEqual((clean["id"], clean["status"], clean["passed"]), ("demo/clean", "error", False))
                self.assertIn("report not in the skill's Output Format", clean["error"])
                self.assertEqual(data["metrics"]["errors"], 2)

    def test_setup_failure_is_an_error(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(os.path.join(FIXTURES, "demo"), os.path.join(tmp, "demo"))
        shutil.rmtree(os.path.join(tmp, "demo", "base"))
        r = run("--cases-dir", tmp, "--cases", "demo/*", "--out-dir", self.out,
                "--agent-cmd", "bash " + FAKE_AGENT)
        self.assertEqual(r.returncode, 1)
        bug, clean = self.results()["cases"]
        self.assertEqual((bug["id"], bug["status"], bug["passed"]), ("demo/bug", "error", False))
        self.assertTrue(bug["error"].startswith("setup failed:"), bug["error"])
        self.assertIs(bug["detected"], False)
        self.assertIs(clean["detected"], None)
        self.assertIs(clean["false_positives"], None)

    def test_broken_pair_stops_run_before_agent(self):
        tmp = tempfile.mkdtemp()
        shutil.copytree(os.path.join(FIXTURES, "demo"), os.path.join(tmp, "demo"))
        with open(os.path.join(tmp, "demo", "pair.json"), "w") as f:
            f.write('{"topic": ')
        r = run("--cases-dir", tmp, "--out-dir", self.out, "--agent-cmd", "bash " + FAKE_AGENT)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL demo: invalid pair.json", r.stdout)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.out, "results.json")))

    def test_hung_agent_times_out(self):
        r = self.run_demo("sleep 30 & wait", "--timeout", "1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("timeout", self.results()["cases"][0]["error"])


if __name__ == "__main__":
    unittest.main()
