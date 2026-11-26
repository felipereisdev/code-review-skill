# Changelog

All notable changes to this project are listed here, in the format of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each release lists the changes merged since the release before it, and changes merged after the latest release wait under `## [Unreleased]` for the next one. Changes up to `v2.0.0` (commit `f9f00fe`) are described in the [v2.0.0 release notes](https://github.com/felipereisdev/code-review-skill/releases/tag/v2.0.0).

## 3.1.0 — 2026-11-12

- Add evidence-driven adversarial coverage, real-contract fixture checks, cumulative re-review and proportionate regression tests.
- Add opt-in isolated execution and source-into-target integration checks on pinned SHA pairs.
- Add Bitbucket Cloud review/publishing and opt-in own-thread/review-state workflow, with explicit tracker authorization and dry runs.
- Separate merge blocking from severity; emit JSON contract v2 while retaining v1 consumer compatibility and frozen studies.
- Add deterministic blocker-gate tests and executable evidence scenarios. No new model-quality benchmark is claimed.

## [Unreleased]

### Changed

- **Summary comment layout.** With `--comment`, the summary comment on the pull request or merge request is now a structured document instead of consecutive `**Label:**` lines, which GitLab joined into one paragraph: a `# Code review: <scope> at <sha>` title, a `## Verification` table (diff, snapshot, review checks, candidates, review effort, relevant tests), `## Findings` with one `### <Severity>` heading per severity, `## Needs human verification`, `## Audit` as a list and a closing `## Assessment` with the `**Ready to merge:**` verdict and `**Look first:**`. Inline comments keep their fields but put a blank line between each of them, so `**Issue:**`, `**Evidence:**`, `**Blocking:**` and `**Fix:**` are separate paragraphs. A script that parsed the old summary or inline bodies must be adapted.
- **Only Critical blocks.** A Warning never blocks the merge any more: `**Blocking:**` is `yes` exactly for a High-confidence Critical finding, and a report with Warnings and no Critical says `Ready to merge: With fixes`. Verdict row 8 (No for a blocking Warning) is retired; JSON version 2 rejects a document that uses it or marks a Warning as blocking.
- **Broken requirements and failing tests are Critical.** A broken acceptance criterion, spec or required public contract is Critical when an executed reproduction or a static trace that quotes the requirement's exact text proves it; without that proof it goes to Needs human verification. With `--execute`, a test or suite that fails because of the change is Critical, one finding per cause, never counted again as missing tests.
- **A link alone is a `pr` review.** `/code-review <pull or merge request URL>` reviews it as `pr <url>` does, for GitHub, GitLab and Bitbucket Cloud links; a bare number still needs `pr`.
- **Publishing and the workflow are the default.** A `pr` review now publishes its inline comments and summary and then runs the review workflow (own-thread resolution and own request-changes/withdrawal) without any flag. `--no-comment` gives a report-only run, and `--no-workflow` publishes comments without touching threads or the review state. `--comment` and `--workflow` are still accepted and only state the defaults. A `pr` review with `--format json` or `--fix` never publishes, `--dry-run` needs a review that publishes, and tracker writes still need an explicit request. Scripts or CI jobs that ran `/code-review pr <n>` expecting a read-only review must add `--no-comment`.
- **Review rounds.** Every `pr` review reads `references/review-rounds.md`. The state of the last published round lives in a hidden `<!-- code-review-skill:state {...} -->` line at the end of the skill's own summary comment (round, head and destination SHAs, and each finding's stable key, severity and location), so no local file is needed. From round 2 on, the report adds a `**Round:**` line, verifies each earlier finding again under `## Previous findings` (fixed, still open, withdrawn or not verified), keeps keys and severity stable unless the Evidence states a reversal, and moves Warning and Suggestion candidates on code that the previous round already reviewed to `## Late notes (not counted)`; a late Critical still blocks. The summary title says `(round <n>)`, and `--comment` publishes nothing when the own summary already covers the current head and destination. A state written by another account is never read.
- **Published language.** Everything `--comment` publishes, the summary and the inline comments, is written in English, whatever the language of the chat; code, paths, identifiers and quoted errors stay as they are.

## [3.0.0] - 2026-10-28

### Upgrading from v2.0.0

- **Scope selection.** `v2.0.0` always asked which of five scopes to review and waited for the answer. The scope now comes from the arguments (`uncommitted`, `staged`, `branch [<base>]`, `commit <sha>`, `range <from>..<to>` or `pr <number|url>`) or is detected when there are none; an interactive run asks only when detection is ambiguous, and a run with no user to answer (CI, `claude -p`) never stops to ask ([#9](https://github.com/felipereisdev/code-review-skill/pull/9), [#10](https://github.com/felipereisdev/code-review-skill/pull/10)).
- **Markdown report.** Each finding has `**Location:**`, `**Issue:**`, `**Evidence:**`, `**Confidence:**` and `**Fix:**` lines instead of `**File:**`, `**Issue:**` and `**Fix:**`, and Medium-confidence findings move to `## Needs human verification` ([#3](https://github.com/felipereisdev/code-review-skill/pull/3)). The report starts with a `**Scope:**` line ([#9](https://github.com/felipereisdev/code-review-skill/pull/9)) and a `## Intent` section ([#17](https://github.com/felipereisdev/code-review-skill/pull/17)), and after the Summary table adds the verification line ([#4](https://github.com/felipereisdev/code-review-skill/pull/4)), the triage lines, a `**Ready to merge:** Yes / No / With fixes` verdict and a closing `## Audit` ([#13](https://github.com/felipereisdev/code-review-skill/pull/13)). "Code review passed — no issues found." now appears only when `## Findings` is empty and the verdict is `Yes`.
- **Frontmatter.** In `SKILL.md`, `author`, `version` and `date` are under `metadata`; at `v2.0.0` they were top-level keys and `version` read `1.0.0` ([#1](https://github.com/felipereisdev/code-review-skill/pull/1)).
- **Scripts.** A script that parses the old Markdown report or the old frontmatter keys must be adapted. For new automation, `--format json` delivers the review as one JSON document, described in `references/json-output.md` ([#18](https://github.com/felipereisdev/code-review-skill/pull/18)); `v2.0.0` had no JSON output, so there is no older JSON format to migrate from.

### Added

- Deeper architecture pattern checklists for Clean Architecture, CQRS, DDD, event-driven architecture and microservices: each one applies only to code that has adopted the pattern, with concrete trigger → effect checks, Bad and Good examples, primary sources and Precedents ([#25](https://github.com/felipereisdev/code-review-skill/pull/25)).
- The Precedents of loaded pattern files are applied like those of stack files: in Step 1, in the Step 2 verification, in the dimension review and in the second opinion ([#25](https://github.com/felipereisdev/code-review-skill/pull/25)).
- `CONTRIBUTING.md`: how a rule is judged, a stack guide template that `scripts/check-docs.sh` checks, and the commands that validate a change, with what each one proves ([#25](https://github.com/felipereisdev/code-review-skill/pull/25)).
- Issue forms for new stack guides and false positives, checked by `scripts/check-docs.sh` ([#25](https://github.com/felipereisdev/code-review-skill/pull/25)).
- This changelog ([#25](https://github.com/felipereisdev/code-review-skill/pull/25)).
- Stack guides for Rust, Ruby / Ruby on Rails, Kotlin / Android, Swift / iOS, Next.js, Kubernetes / Helm, GitHub Actions and SQL, each loaded only for the files that its evidence selects ([#24](https://github.com/felipereisdev/code-review-skill/pull/24)).
- Stack detection by the directories of the changed files, per package in monorepos, with `references/stack-detection.md` ([#21](https://github.com/felipereisdev/code-review-skill/pull/21)).
- `--fix` to apply approved fixes after the report, and an optional second opinion from another reviewer CLI with `--second-opinion` ([#19](https://github.com/felipereisdev/code-review-skill/pull/19)).
- `--format json` output and the optional `scripts/review_gate.py` CI gate ([#18](https://github.com/felipereisdev/code-review-skill/pull/18)).
- The `## Intent` section of every report and the git history of removed protections ([#17](https://github.com/felipereisdev/code-review-skill/pull/17)).
- Large diffs reviewed in module batches, with their coverage limits in the Audit ([#16](https://github.com/felipereisdev/code-review-skill/pull/16)).
- Dimension review with native subagents ([#15](https://github.com/felipereisdev/code-review-skill/pull/15)).
- Review triage, the Ready to merge verdict and the Audit, and API validation with any documentation tool the agent has or the official documentation ([#13](https://github.com/felipereisdev/code-review-skill/pull/13)).
- Repository configuration in `.code-review/config.yml` and custom rules in `.code-review/rules/` ([#12](https://github.com/felipereisdev/code-review-skill/pull/12)).
- `--comment` publishing of findings as pull request and merge request comments, with `--dry-run` previews ([#11](https://github.com/felipereisdev/code-review-skill/pull/11)).
- The `pr` scope for a GitHub pull request or a GitLab merge request by number or URL ([#10](https://github.com/felipereisdev/code-review-skill/pull/10)).
- The review scope from arguments or automatic detection ([#9](https://github.com/felipereisdev/code-review-skill/pull/9)).
- Conditional review categories loaded from `references/` only when the diff matches their trigger ([#8](https://github.com/felipereisdev/code-review-skill/pull/8)).
- Repository rules files read and cited in findings ([#6](https://github.com/felipereisdev/code-review-skill/pull/6)).
- The Do Not Report list and per-stack precedents ([#5](https://github.com/felipereisdev/code-review-skill/pull/5)).
- Verification of Critical and Warning findings before the report ([#4](https://github.com/felipereisdev/code-review-skill/pull/4)).
- Evidence, confidence and operational severity levels for every finding ([#3](https://github.com/felipereisdev/code-review-skill/pull/3)).
- The eval suite, its baseline and the CI checks ([#2](https://github.com/felipereisdev/code-review-skill/pull/2)).

### Changed

- Thirteen existing stack checklists deepened ([#22](https://github.com/felipereisdev/code-review-skill/pull/22), [#23](https://github.com/felipereisdev/code-review-skill/pull/23)).
- Evaluation coverage expanded and the baselines corrected ([#20](https://github.com/felipereisdev/code-review-skill/pull/20)).
- Findings limited to changed lines, less size noise, and review input treated as data, never as instructions ([#7](https://github.com/felipereisdev/code-review-skill/pull/7)).
- The README documents the v2.0.0 features and recommends installing with `npx skills` (`c2f612a`, `0e4c9ce`).

### Fixed

- Review triage, audit and review effort claims reconciled ([#14](https://github.com/felipereisdev/code-review-skill/pull/14)).
- README counts, the MIT `LICENSE` and the `SKILL.md` frontmatter ([#1](https://github.com/felipereisdev/code-review-skill/pull/1)).

[Unreleased]: https://github.com/felipereisdev/code-review-skill/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/felipereisdev/code-review-skill/compare/v2.0.0...v3.0.0
