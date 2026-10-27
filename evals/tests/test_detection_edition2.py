"""Offline checks of stack detection coverage edition 2, evals/tests/fixtures/detection/corpus-edition-2.json.

Edition 2 was written when the guides for Rust, Ruby / Ruby on Rails, Kotlin / Android, Swift / iOS, Next.js,
Kubernetes / Helm, GitHub Actions and SQL were added. Its labels describe the guide inventory it lists in `guides`,
derived from the fixture facts and the contract in SKILL.md Step 1 and references/stack-detection.md; they are never
copied from edition 1 (corpus.json), which stays frozen with the labels of its own time. These checks show that the
labels are well formed, that the labels of the eight new guides and of their platforms follow the written signal
rules for the fixture facts, and that each label points at the rule that decides it. They never show which package,
signal file or guide a real agent picks: only a model run could observe that, and none is part of them.
"""
import fnmatch
import json
import os
import posixpath
import re
import unittest

from test_detection import (EXPECT_KEYS, KINDS, ROOT, RULE_FILES, STATUSES, listed_dirs, manifest_dirs, package_of,
                            parent, read, sides, step1_text)

EDITION = os.path.join(ROOT, "evals", "tests", "fixtures", "detection", "corpus-edition-2.json")
CASE_KEYS = {"id", "guide", "kind", "scope", "files", "changed", "expect", "rule", "why"}
OPTIONAL_KEYS = {"ignore_paths"}
SCOPES = ("uncommitted", "branch")
NEW_GUIDES = ("stacks/rust.md", "stacks/ruby-rails.md", "stacks/kotlin-android.md", "stacks/swift-ios.md",
              "stacks/nextjs.md", "stacks/kubernetes-helm.md", "stacks/github-actions.md", "stacks/sql.md")
# The platform sections of a combined guide, which apply only with their own evidence.
PLATFORMS = {"stacks/ruby-rails.md": "Ruby on Rails", "stacks/kotlin-android.md": "Android",
             "stacks/swift-ios.md": "iOS"}
# Technologies that no stack file of this edition covers, with the file name a guide for them would have.
NO_GUIDE = {"Gradle": "gradle", "Java": "java"}
# The Step 1 signals that select the new guides.
SIGNALS = ("Cargo.toml", "Gemfile", "build.gradle.kts", "Package.swift", "*.xcodeproj", "next.config.*",
           "Chart.yaml", "kustomization.yaml", "*.sql", ".github/workflows/", "action.yml")
# The changed files that each language guide describes; the signal files of a package select it only for these.
DESCRIBES = {"stacks/rust.md": (".rs",), "stacks/ruby-rails.md": (".rb", ".erb", ".rake"),
             "stacks/kotlin-android.md": (".kt", ".kts", ".java"), "stacks/swift-ios.md": (".swift",),
             "stacks/nextjs.md": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")}
ANDROID_PLUGINS = ("com.android.application", "com.android.library")
KOTLIN_PLUGINS = ("kotlin(", "org.jetbrains.kotlin")
ALIAS_CALL = re.compile(r"alias\(libs\.plugins\.([\w.]+)\)")


def load():
    with open(EDITION, encoding="utf-8") as f:
        return json.load(f)


def path_dirs(path, package):
    """The directories from the directory of path up to and including its package directory."""
    dirs, directory = [], parent(path)
    while True:
        dirs.append(directory)
        if directory in (package, "."):
            return dirs
        directory = parent(directory)


def signal_files(case, path, package):
    """The snapshot files whose directory lies between path and its package, as {path: content}."""
    dirs = set(path_dirs(path, package))
    return {p: text for p, text in case["files"].items() if parent(p) in dirs}


def top_level_keys(text):
    return {line.split(":", 1)[0] for line in text.splitlines() if line and not line[0].isspace() and ":" in line}


def build_root(case, package):
    """The nearest directory from the package up to the repository root that holds a settings file, else the package."""
    settings = {parent(p) for p in case["files"]
                if posixpath.basename(p) in ("settings.gradle", "settings.gradle.kts")}
    directory = package
    while directory not in settings and directory != ".":
        directory = parent(directory)
    return directory if directory in settings else package


def catalog_ids(case, package):
    """The plugin ids that the default catalog of the build root gives, by accessor; a repeated accessor gives none.

    A settings file of the build root that mentions versionCatalogs leaves every accessor open."""
    root = build_root(case, package)
    settings = [case["files"].get(posixpath.normpath(posixpath.join(root, name)), "")
                for name in ("settings.gradle", "settings.gradle.kts")]
    if any("versionCatalogs" in text for text in settings):
        return {}
    text = case["files"].get(posixpath.normpath(posixpath.join(root, "gradle", "libs.versions.toml")), "")
    ids, section = {}, None
    for line in text.splitlines():
        if line.startswith("["):
            section = line.strip()
            continue
        key, _, table = line.partition("=")
        inline = section == "[plugins]" and table.strip().startswith("{")
        match = re.search(r'\bid = "([^"]+)"', table) if inline else None
        if match and key.strip():
            accessor = re.sub(r"[-_]", ".", key.strip())
            ids[accessor] = None if accessor in ids else match.group(1)
    return {accessor: plugin for accessor, plugin in ids.items() if plugin}


def module_builds(case, path, package):
    """The text of each build file of the signal files, without its apply false lines, with the ids of its aliases."""
    ids = catalog_ids(case, package)
    texts = []
    for p, text in signal_files(case, path, package).items():
        if posixpath.basename(p) in ("build.gradle", "build.gradle.kts"):
            live = [line for line in text.splitlines() if "apply false" not in line]
            applied = [ids[key] for line in live for key in ALIAS_CALL.findall(line) if key in ids]
            texts.append("\n".join(live) + "".join(f'\nid("{plugin}")' for plugin in applied))
    return texts


def proven_new_guides(case, path, package):
    """The new guides that the Step 1 signals select for one changed file, from the fixture facts alone."""
    name, files, own = posixpath.basename(path), signal_files(case, path, package), case["files"].get(path, "")
    names = {posixpath.basename(p): text for p, text in files.items()}
    builds = module_builds(case, path, package)
    manifests = [json.loads(text) for p, text in files.items() if posixpath.basename(p) == "package.json"]
    proven = set()
    if "Cargo.toml" in names:
        proven.add("stacks/rust.md")
    if "Gemfile" in names:
        proven.add("stacks/ruby-rails.md")
    if any(marker in text for text in builds for marker in ANDROID_PLUGINS + KOTLIN_PLUGINS):
        proven.add("stacks/kotlin-android.md")
    dirs = set(path_dirs(path, package))
    xcode = any(parent(p).endswith(".xcodeproj") and parent(parent(p)) in dirs for p in case["files"])
    if "Package.swift" in names or xcode:
        proven.add("stacks/swift-ios.md")
    if any(fnmatch.fnmatchcase(n, "next.config.*") for n in names) or any(
            "next" in m.get("dependencies", {}) or "next" in m.get("peerDependencies", {}) for m in manifests):
        proven.add("stacks/nextjs.md")
    proven = {g for g in proven if path.endswith(DESCRIBES[g])}
    if ("Chart.yaml" in names and path.endswith((".yaml", ".yml", ".tpl"))) or name in (
            "kustomization.yaml", "kustomization.yml") or (
            path.endswith((".yaml", ".yml")) and {"apiVersion", "kind"} <= top_level_keys(own)):
        proven.add("stacks/kubernetes-helm.md")
    if (parent(path) == ".github/workflows" and path.endswith((".yml", ".yaml"))) or (
            name in ("action.yml", "action.yaml") and "runs" in top_level_keys(own)):
        proven.add("stacks/github-actions.md")
    if path.endswith(".sql"):
        proven.add("stacks/sql.md")
    return proven


def proven_platforms(case, path, package):
    """The platforms whose evidence the signal files of one changed file show, from the fixture facts alone."""
    files = signal_files(case, path, package)
    dirs = set(path_dirs(path, package))
    proven = set()
    if any(posixpath.basename(p) == "Gemfile" and ('gem "rails"' in t or "gem 'rails'" in t) for p, t in files.items()):
        proven.add("Ruby on Rails")
    if any(any(m in t for m in ANDROID_PLUGINS) for t in module_builds(case, path, package)):
        proven.add("Android")
    xcode = [t for p, t in case["files"].items()
             if p.endswith(".xcodeproj/project.pbxproj") and parent(parent(p)) in dirs]
    package_swift = [t for p, t in files.items() if posixpath.basename(p) == "Package.swift"]
    if any("SDKROOT = iphoneos" in t for t in xcode) or any(".iOS(" in t for t in package_swift) or (
            "import UIKit" in case["files"].get(path, "")):
        proven.add("iOS")
    return proven


class EditionShapeTest(unittest.TestCase):
    def setUp(self):
        self.doc = load()
        self.cases = self.doc["cases"]

    def test_cases_have_the_edition_keys(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)), "case ids must be unique")
        self.assertEqual(self.doc["edition"], 2)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertLessEqual(CASE_KEYS, set(case))
                self.assertLessEqual(set(case), CASE_KEYS | OPTIONAL_KEYS)
                self.assertEqual(set(case["expect"]), EXPECT_KEYS)
                self.assertIn(case["guide"], NEW_GUIDES)
                self.assertIn(case["kind"], KINDS)
                self.assertIn(case["scope"], SCOPES)
                self.assertIn(case["rule"]["file"], RULE_FILES)
                self.assertTrue(case["why"].strip())
                for entry in case["changed"]:
                    self.assertIn(entry["status"], STATUSES)
                    self.assertIn(entry["path"], case["files"])

    def test_inventory_lists_existing_cited_guides(self):
        inventory = set(self.doc["guides"])
        self.assertEqual(len(inventory), 28)
        self.assertLessEqual(set(NEW_GUIDES), inventory)
        skill = read("SKILL.md")
        for guide in sorted(inventory):
            with self.subTest(guide=guide):
                self.assertTrue(os.path.isfile(os.path.join(ROOT, guide)))
                self.assertIn(f"`./{guide}`", skill)

    def test_every_new_guide_has_contrasting_cases(self):
        for guide in NEW_GUIDES:
            mine = [case for case in self.cases if case["guide"] == guide]
            with self.subTest(guide=guide):
                self.assertTrue(any(case["kind"] == "positive" and any(
                    guide in guides for guides in case["expect"]["guides"].values()) for case in mine))
                self.assertTrue(any(case["kind"] in ("negative", "ambiguous") and (
                    guide in case["expect"]["never"] or PLATFORMS.get(guide) in case["expect"]["not_proven"])
                    for case in mine))

    def test_every_platform_has_a_case_without_its_evidence(self):
        for guide, platform in PLATFORMS.items():
            with self.subTest(guide=guide):
                self.assertTrue(any(platform in case["expect"]["not_proven"] and any(
                    guide in guides for guides in case["expect"]["guides"].values()) for case in self.cases))


class EditionFactsTest(unittest.TestCase):
    def setUp(self):
        self.doc = load()
        self.cases = self.doc["cases"]

    def test_package_labels_follow_the_nearest_manifest(self):
        for case in self.cases:
            dirs = manifest_dirs(case)
            with self.subTest(case=case["id"]):
                self.assertEqual(case["expect"]["packages"], {p: package_of(p, dirs) for p in sides(case)})

    def test_labels_use_the_edition_inventory(self):
        inventory = set(self.doc["guides"])
        for case in self.cases:
            loaded = {g for guides in case["expect"]["guides"].values() for g in guides}
            never = set(case["expect"]["never"])
            packages = set(case["expect"]["packages"].values())
            with self.subTest(case=case["id"]):
                self.assertFalse(loaded & never)
                self.assertLessEqual(loaded | never, inventory)
                self.assertLessEqual(set(case["expect"]["guides"]) | set(case["expect"]["no_guide"]), packages)
                for technologies in case["expect"]["no_guide"].values():
                    for technology in technologies:
                        self.assertIn(technology, NO_GUIDE)
                        self.assertNotIn(f"stacks/{NO_GUIDE[technology]}.md", inventory)

    def test_new_guide_labels_follow_the_signals(self):
        for case in self.cases:
            expected = {}
            for path, package in case["expect"]["packages"].items():
                expected.setdefault(package, set()).update(proven_new_guides(case, path, package))
            with self.subTest(case=case["id"]):
                labelled = {package: set(guides) & set(NEW_GUIDES)
                            for package, guides in case["expect"]["guides"].items()}
                self.assertEqual({p: g for p, g in labelled.items() if g}, {p: g for p, g in expected.items() if g})
                for guide in case["expect"]["never"]:
                    if guide in NEW_GUIDES:
                        self.assertFalse(any(guide in g for g in expected.values()), guide)

    def test_platform_labels_follow_the_evidence(self):
        for case in self.cases:
            shown = {}
            for path, package in case["expect"]["packages"].items():
                shown.setdefault(package, set()).update(proven_platforms(case, path, package))
            for package, guides in case["expect"]["guides"].items():
                for guide, platform in PLATFORMS.items():
                    if guide not in guides:
                        continue
                    with self.subTest(case=case["id"], platform=platform):
                        self.assertEqual(platform in case["expect"]["not_proven"], platform not in shown[package])

    def test_unread_files_lie_outside_the_listed_directories(self):
        for case in self.cases:
            listed = listed_dirs(case)
            for path in case["expect"]["not_read"]:
                with self.subTest(case=case["id"], path=path):
                    self.assertIn(path, case["files"])
                    self.assertNotIn(parent(path), listed)


class EditionAnchorsTest(unittest.TestCase):
    def setUp(self):
        self.cases = load()["cases"]

    def test_every_rule_anchor_is_in_its_file(self):
        for case in self.cases:
            rule = case["rule"]
            with self.subTest(case=case["id"]):
                self.assertTrue(rule["anchor"] in read(rule["file"]), f"{rule['file']} has no {rule['anchor']}")

    def test_step1_names_every_signal_of_the_new_guides(self):
        text = step1_text()
        for signal in SIGNALS:
            with self.subTest(signal=signal):
                self.assertIn(f"`{signal}`", text)
        for guide in NEW_GUIDES:
            with self.subTest(guide=guide):
                self.assertIn(f"`./{guide}`", text)


if __name__ == "__main__":
    unittest.main()
