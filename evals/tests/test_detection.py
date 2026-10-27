"""Offline checks of the frozen stack detection corpus, evals/tests/fixtures/detection/corpus.json.

The corpus labels which package each changed file belongs to, which stack guides apply, which technologies have no
guide and which files a review never reads, from the fixture facts and the contract in SKILL.md Step 1 and
references/stack-detection.md. These checks show that the labels are well formed, agree with the fixture facts and
the nearest-manifest rule, and point at the section of that contract that decides them. They never show which
package, signal file or guide a real agent picks: only a model run could observe that, and none is part of them.

The corpus is edition 1. Its guide and no-guide labels describe the stack guides that existed when it was frozen
(EDITION1_GUIDES), not the guides that exist now: a guide added later never relabels it.
"""
import fnmatch
import hashlib
import json
import os
import posixpath
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CORPUS = os.path.join(HERE, "fixtures", "detection", "corpus.json")

NEW_SIGNALS = ("Cargo.toml", "Gemfile", "build.gradle.kts", "Package.swift", "next.config.*", "angular.json",
               ".github/workflows/")
SIGNALS = NEW_SIGNALS + ("existing",)
KINDS = ("positive", "negative", "ambiguous")
CONTRASTS = ("monorepo-nested", "unrelated-package", "root-shared", "inherited", "direct", "dev",
             "transitive-lockfile", "generated", "rename", "delete", "snapshot", "diff-alone", "configuration",
             "fallback", "existing-signal")
SCOPES = ("uncommitted", "branch", "pr", "pr-diff-alone")
STATUSES = ("A", "M", "D", "R")
MANIFESTS = ("package.json", "composer.json", "pyproject.toml", "requirements.txt", "setup.py", "go.mod", "pom.xml",
             "build.gradle", "build.gradle.kts", "pubspec.yaml", "Cargo.toml", "Gemfile", "Package.swift")
INSTALLED = ("node_modules", "vendor")
# Technologies that no stack file covered when the corpus was frozen, with the file name a guide for them would have.
NO_GUIDE = {"Rust": "rust", "Ruby": "ruby", "Ruby on Rails": "rails", "Swift": "swift", "Android": "android",
            "Kotlin": "kotlin", "Gradle": "gradle", "GitHub Actions": "github-actions"}
# The stack guides that existed when the corpus was frozen.
EDITION1_GUIDES = frozenset(f"stacks/{name}.md" for name in (
    "angular", "docker", "dotnet", "flutter", "go", "inertia", "java-spring", "kafka", "laravel", "node", "nuxt",
    "pest", "python", "react-native", "react", "svelte", "tailwind", "terraform", "typescript", "vue"))
# The sha256 of corpus.json when it was frozen: the file and its labels never change.
CORPUS_SHA256 = "ef7ed4dabe999720d4e657f15338bdf01d05fc373f3d6b86a50da9b59eb762cc"
RULE_FILES = ("SKILL.md", "references/stack-detection.md")
CASE_KEYS = {"id", "signal", "kind", "contrasts", "scope", "files", "changed", "expect", "rule", "why"}
OPTIONAL_KEYS = {"checkout", "ignore_paths"}
EXPECT_KEYS = {"packages", "guides", "no_guide", "never", "not_proven", "not_read"}


def load_cases():
    with open(CORPUS, encoding="utf-8") as f:
        return json.load(f)["cases"]


def read(path):
    full = os.path.join(ROOT, path)
    if not os.path.isfile(full):
        return ""
    with open(full, encoding="utf-8") as f:
        return f.read()


def step1_text():
    text = read("SKILL.md")
    start = text.find("## Step 1 — Codebase Investigation")
    end = text.find("## Step 1.5", start)
    return text[start:end] if start >= 0 and end > start else ""


def is_manifest(path):
    parts = path.split("/")
    if any(part in INSTALLED for part in parts[:-1]):
        return False
    return parts[-1] in MANIFESTS or parts[-1].endswith(".csproj")


def excluded(path, patterns):
    return any(path.startswith(p) if p.endswith("/") else fnmatch.fnmatchcase(path, p) for p in patterns)


def parent(directory):
    return posixpath.dirname(directory) or "."


def sides(case):
    """The paths a review detects from: each changed path, and the old path of a rename, unless excluded."""
    paths = []
    for entry in case["changed"]:
        paths.append(entry["path"])
        if entry["status"] == "R":
            paths.append(entry["old_path"])
    return [p for p in paths if not excluded(p, case.get("ignore_paths", []))]


def manifest_dirs(case):
    """Directories with a package manifest in the snapshot, or in manifest lines that the diff shows."""
    paths = set() if case["scope"] == "pr-diff-alone" else set(case["files"])
    paths |= {entry["path"] for entry in case["changed"] if "manifest_lines" in entry}
    return {parent(p) for p in paths if is_manifest(p)}


def package_of(path, dirs):
    directory = parent(path)
    while directory not in dirs and directory != ".":
        directory = parent(directory)
    return directory


def listed_dirs(case):
    """The directories of the changed paths and all their parents up to the repository root."""
    listed = set()
    for path in sides(case):
        directory = parent(path)
        listed.add(directory)
        while directory != ".":
            directory = parent(directory)
            listed.add(directory)
    return listed


class CorpusShapeTest(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases()

    def test_corpus_is_frozen(self):
        with open(CORPUS, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), CORPUS_SHA256)

    def test_cases_have_the_frozen_keys(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)), "case ids must be unique")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertLessEqual(CASE_KEYS, set(case))
                self.assertLessEqual(set(case), CASE_KEYS | OPTIONAL_KEYS)
                self.assertEqual(set(case["expect"]), EXPECT_KEYS)
                self.assertIn(case["signal"], SIGNALS)
                self.assertIn(case["kind"], KINDS)
                self.assertTrue(case["contrasts"])
                self.assertLessEqual(set(case["contrasts"]), set(CONTRASTS))
                self.assertIn(case["scope"], SCOPES)
                self.assertIn(case["rule"]["file"], RULE_FILES)
                self.assertTrue(case["rule"]["anchor"].strip())
                self.assertTrue(case["why"].strip())

    def test_changed_entries_match_the_snapshot(self):
        for case in self.cases:
            files = case["files"]
            with self.subTest(case=case["id"]):
                if case["scope"] == "pr-diff-alone":
                    self.assertEqual(files, {}, "a review of the diff alone has no snapshot")
                self.assertEqual("checkout" in case, case["scope"] == "pr", "only a pr case has a local checkout")
                for entry in case["changed"]:
                    self.assertIn(entry["status"], STATUSES)
                    self.assertEqual("old_path" in entry, entry["status"] == "R")
                    if "manifest_lines" in entry:
                        self.assertTrue(is_manifest(entry["path"]), entry["path"])
                    if entry["status"] == "D":
                        self.assertNotIn(entry["path"], files)
                    elif case["scope"] != "pr-diff-alone":
                        self.assertIn(entry["path"], files)
                    if entry["status"] == "R":
                        self.assertNotIn(entry["old_path"], files)

    def test_every_new_signal_has_contrasting_cases(self):
        for signal in NEW_SIGNALS:
            kinds = {case["kind"] for case in self.cases if case["signal"] == signal}
            with self.subTest(signal=signal):
                self.assertIn("positive", kinds)
                self.assertTrue(kinds & {"negative", "ambiguous"})

    def test_every_contrast_and_kind_is_covered(self):
        self.assertEqual({c for case in self.cases for c in case["contrasts"]}, set(CONTRASTS))
        self.assertEqual({case["kind"] for case in self.cases}, set(KINDS))


class CorpusFactsTest(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases()

    def test_package_labels_follow_the_nearest_manifest(self):
        for case in self.cases:
            dirs = manifest_dirs(case)
            expected = {path: package_of(path, dirs) for path in sides(case)}
            with self.subTest(case=case["id"]):
                self.assertEqual(case["expect"]["packages"], expected)

    def test_guides_are_keyed_by_labelled_packages(self):
        for case in self.cases:
            packages = set(case["expect"]["packages"].values())
            with self.subTest(case=case["id"]):
                self.assertLessEqual(set(case["expect"]["guides"]), packages)
                self.assertLessEqual(set(case["expect"]["no_guide"]), packages)

    def test_guides_exist_and_are_cited(self):
        skill = read("SKILL.md")
        for case in self.cases:
            loaded = {g for guides in case["expect"]["guides"].values() for g in guides}
            never = set(case["expect"]["never"])
            with self.subTest(case=case["id"]):
                self.assertFalse(loaded & never)
                for guide in loaded | never:
                    self.assertIn(guide, EDITION1_GUIDES)
                    self.assertTrue(guide.startswith("stacks/") and os.path.isfile(os.path.join(ROOT, guide)), guide)
                    self.assertTrue(f"`./{guide}`" in skill, f"SKILL.md does not cite `./{guide}`")

    def test_technologies_without_a_guide_had_no_stack_file_when_frozen(self):
        for case in self.cases:
            for technologies in case["expect"]["no_guide"].values():
                for technology in technologies:
                    with self.subTest(case=case["id"], technology=technology):
                        self.assertIn(technology, NO_GUIDE)
                        self.assertNotIn(f"stacks/{NO_GUIDE[technology]}.md", EDITION1_GUIDES)

    def test_unread_files_lie_outside_the_listed_directories(self):
        for case in self.cases:
            listed = listed_dirs(case)
            for path in case["expect"]["not_read"]:
                with self.subTest(case=case["id"], path=path):
                    if path in case.get("checkout", {}):
                        continue
                    self.assertIn(path, case["files"])
                    self.assertNotIn(parent(path), listed)

    def test_the_root_only_rule_disagrees_with_the_package_labels(self):
        nested = [case["id"] for case in self.cases if set(case["expect"]["packages"].values()) - {"."}]
        self.assertGreaterEqual(len(nested), 10, "the corpus must tell package detection from root-only detection")


class ContractAnchorsTest(unittest.TestCase):
    """Each label points at the written rule that decides it; these fail until that rule is written."""

    def setUp(self):
        self.cases = load_cases()

    def test_every_rule_anchor_is_in_its_file(self):
        for case in self.cases:
            rule = case["rule"]
            with self.subTest(case=case["id"]):
                self.assertTrue(rule["anchor"] in read(rule["file"]), f"{rule['file']} has no {rule['anchor']}")

    def test_step1_names_every_new_signal(self):
        text = step1_text()
        for signal in NEW_SIGNALS:
            with self.subTest(signal=signal):
                self.assertTrue(f"`{signal}`" in text, f"Step 1 does not name `{signal}`")

    def test_step1_names_every_technology_without_a_guide(self):
        text = step1_text()
        for technology in NO_GUIDE:
            with self.subTest(technology=technology):
                self.assertTrue(technology in text, f"Step 1 does not name {technology}")


if __name__ == "__main__":
    unittest.main()
