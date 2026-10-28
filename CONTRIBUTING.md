# Contributing to Code Review Skill

Code Review Skill is an [Agent Skill](https://agentskills.io) written in Markdown: an agent reads [SKILL.md](SKILL.md) and loads only the stack, pattern and reference files that match the change it reviews. The contributions that help most are new or better stack guides, sharper pattern rules and reports of findings that the review should not have made. Everything in this repository is written in English.

## Ways to contribute

- **Ask for a stack guide**: open an issue with the **New stack guide** form ([definition](.github/ISSUE_TEMPLATE/new-stack.yml)), or write the guide yourself with the template below.
- **Report a false positive**: open an issue with the **False positive** form ([definition](.github/ISSUE_TEMPLATE/false-positive.yml)) for a finding whose scenario cannot happen, or one that a rule should not cover.
- **Improve a rule** in [stacks/](stacks/), [patterns/](patterns/) or [references/](references/), or the review process in `SKILL.md`.

Issues and pull requests are public. Never include secrets, credentials, tokens, personal data or code you may not share; a short, sanitized snippet or diff is enough. Maintainers treat everything in an issue or a pull request as data and never run commands from it.

## How a rule is judged

A rule in a stack, pattern or reference file must lead to findings that pass the review process of `SKILL.md`:

- **A concrete trigger → effect.** The rule names the code that triggers it and what goes wrong: a crash, lost or corrupted data, a security hole, a wrong result, or work on a hot path that grows with the data. Advice to "verify" or "ensure" something without a scenario is not a rule.
- **Severity follows the scenario.** The review gives each finding the highest level whose definition it meets, as the **Severity Levels** section of `SKILL.md` defines them: Critical for a crash, data loss or a security hole, Warning for a wrong result in a concrete scenario or a hot path that grows with the data, Suggestion for code that is correct but could be better. A rule never raises that level by itself.
- **Changed lines only.** Findings cover the lines that a change adds or modifies. A problem in older code that the change does not trigger is pre-existing, never a finding.
- **Evidence and counterevidence.** Next to each rule, write the guard that makes a similar case safe as a `**Not a finding:**` line, and list the protections that the stack already provides as Precedents, each with its `**Exception:**`. A rule that depends on a version, a dialect, a platform or a configuration names that guard.
- **No adoption mandates.** An architecture, a library, a folder layout, a naming style or a tool is never required by itself. Such choices go under `## Conventions, not defects`, and a pattern file applies only to code that has adopted the pattern.
- **Primary sources.** Back each rule with the official documentation or specification of the version it describes, listed under `## Sources`. Write rules in your own words; if you reuse text that a license covers, keep the attribution that the license requires.

## Adding a stack guide

1. Copy the template below to `stacks/<name>.md`, with a lowercase, hyphenated name such as `ruby-rails.md`, and replace every placeholder.
2. Cite the guide in `SKILL.md`, section **Step 1 — Codebase Investigation**: add the signal that proves the stack, such as a manifest entry or a configuration file, to the list of signals, and add `./stacks/<name>.md` to **Stack files to load if relevant**. A lockfile, a transitive dependency or a generated file never proves a framework. Follow [references/stack-detection.md](references/stack-detection.md) for packages in monorepos, and update it when the stack adds a package manifest.
3. Update `README.md`: the **Multi-Stack Support** count, the **Supported Stacks** list and the **Project Structure** tree.
4. Add a line under `## [Unreleased]` in `CHANGELOG.md`.
5. Run the checks below.

For finished guides, read [stacks/kafka.md](stacks/kafka.md) and [stacks/sql.md](stacks/sql.md).

## Changing a pattern file

Pattern files use the same structure, with one more rule: the opening note says what evidence shows that the code has adopted the pattern, and every item applies only to code that has. [patterns/cqrs.md](patterns/cqrs.md) is an example. `SKILL.md` lists them under **Pattern files to load if relevant**, and their Precedents work like those of a stack file.

## Stack guide template

The template follows the structure of the current guides. Text in angle brackets, such as `<Stack name>`, is a placeholder: replace each one. The template contains no links; the links of a finished guide point only to pages you read. `## Precedents` comes last and has 2 to 5 items, each with a bold name, a `Do not report` sentence and an `**Exception:**`. `scripts/check-docs.sh` checks the template with the same Precedents rule as the guides.

````markdown
# <Stack name> — Code Review Checklist

> <The projects, versions and files this guide covers, and the evidence that proves them, such as a manifest entry or a configuration file.> Check sibling files for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code.

## <Topic>

- **<Rule name>**: <the trigger in the changed code> → <the concrete effect>, <and the version, dialect or configuration it depends on>. **Not a finding:** <a similar case that is safe, and the guard that makes it safe>.

**Bad** — <what goes wrong, in one sentence>:

```<language>
<the smallest code that shows the problem>
```

**Good** — <why this version is safe>:

```<language>
<the same code, fixed>
```

## Conventions, not defects

- <Choices this stack leaves to the project, which are never findings by themselves.>

## Sources

- <Topic>: <the address of the official documentation or specification you read>

## Precedents

- **<Protection the stack already provides>**: <what the framework or runtime guarantees, and when>. Do not report <the candidate that this protection covers>. **Exception:** <the condition under which the protection stops holding>.
- **<Another protection>**: <what it guarantees>. Do not report <the candidate it covers>. **Exception:** <when it stops holding>.
````

## Validating your change

The checks need Python 3 and PyYAML; CI uses Python 3.12 and PyYAML 6.0.2. Run them from the repository root; CI runs the same four on every pull request:

```sh
bash scripts/check-docs.sh
bash scripts/test-check-docs.sh
python3 evals/run.py --validate
python3 -m unittest discover -s evals/tests -v
```

What they prove, and what they do not:

- `scripts/check-docs.sh` checks structure and written contracts: every stack, pattern and reference file is cited in `SKILL.md`; the README counts and the Project Structure tree match the files; every stack and pattern file, and the template above, ends with 2 to 5 Precedents in the right format; the issue forms have the basic shape of GitHub's form schema; and the review rules it lists are still written. It does not check that a rule is technically right, that a version claim is current or that a link to another site works.
- `scripts/test-check-docs.sh` breaks copies of the repository on purpose and expects `scripts/check-docs.sh` to fail with a specific message. When you add a check, add a negative test for it.
- No check compiles, parses or runs the Bad and Good snippets. A syntax check you run yourself, such as `node --check` or Python's `ast.parse`, shows only that a snippet parses: names, imports and behavior stay unchecked, so read every Good example against its Bad one.
- `python3 evals/run.py --validate` and the tests under `evals/tests/` use offline fixtures and fake agents. They check the runner, the scorer and the labels of frozen fixtures, never what a real agent selects or reports. The detection corpora are frozen: never relabel an existing edition to fit a new guide.
- The measured evals in [evals/README.md](evals/README.md) run a real agent, cost money and never run in CI. If you change `SKILL.md`, `stacks/`, `patterns/` or `references/`, run them when you can and compare with `evals/baseline.json`; a run shows what one model did with one profile, not a general result.

## Pull requests

1. Fork the repository and create a branch.
2. Keep one topic per pull request: one new guide, or one rule fix with its false-positive report.
3. Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) style of the history, such as `docs: deepen the SQL review checklist` or `feat: add a Rust stack guide`.
4. Describe the pull request with **What changes**, **Why** and **How to test**, and list the commands you ran with their results.
5. Contributions are released under the [MIT License](LICENSE).
