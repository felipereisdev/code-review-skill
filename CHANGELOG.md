# Changelog

All notable changes to this project are listed here, in the format of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The latest release tag is `v2.0.0`, on commit `f9f00fe`. Everything below was merged after that tag and is not part of a tagged release; the version in `SKILL.md` stays `2.0.0` until a maintainer releases these changes.

## [Unreleased]

### Added

- Deeper architecture pattern checklists for Clean Architecture, CQRS, DDD, event-driven architecture and microservices: each one applies only to code that has adopted the pattern, with concrete trigger → effect checks, Bad and Good examples, primary sources and Precedents.
- The Precedents of loaded pattern files are applied like those of stack files: in Step 1, in the Step 2 verification, in the dimension review and in the second opinion.
- `CONTRIBUTING.md`: how a rule is judged, a stack guide template that `scripts/check-docs.sh` checks, and the commands that validate a change, with what each one proves.
- Issue forms for new stack guides and false positives, checked by `scripts/check-docs.sh`.
- This changelog.
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
