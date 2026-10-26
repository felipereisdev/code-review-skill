# Code Review 🔍

[![GitHub stars](https://img.shields.io/github/stars/felipereisdev/code-review-skill?style=social)](https://github.com/felipereisdev/code-review-skill)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-purple)](https://agentskills.io)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-blue)](https://claude.ai)
[![OpenCode](https://img.shields.io/badge/OpenCode-compatible-green)](https://opencode.ai)

> An Agent Skill that performs structured, comprehensive code reviews with automatic stack detection and severity-based reporting.

**Compatible with any LLM that supports the [Agent Skills Standard](https://agentskills.io)** - Claude Code, OpenCode, Cursor, and any other AI coding assistant that implements the skills protocol.

## 🌟 Features

- **Automatic Stack Detection** - Identifies project technology from config files
- **Consistency-First Review** - Checks existing project conventions before flagging violations (Step 1.5)
- **API Validation** - Checks a version-specific or uncertain claim about a library API against the documentation of the version in use, with any documentation tool the agent has (for example the Context7 MCP server) or the official documentation; stable behavior that a loaded stack file documents needs no lookup. A claim it cannot check is never reported and is listed as `API not validated` in the Audit, marked `material` only when a changed behavior or a contract the change relies on depends on it, and `not material` otherwise
- **Multi-Stack Support** - 20 technology stacks covered
- **Pattern-Specific Rules** - Apply Clean Architecture, DDD, CQRS, Microservices guidelines
- **Severity-Based Reporting** - Critical, Warning, and Suggestion levels
- **Triage, Verdict and Audit** - Every report rates the review effort from 1 to 5, says which tests cover the change and what it ran without claiming a result it did not see, names up to 3 files to look at first, and gives a `**Ready to merge:** Yes / No / With fixes` verdict from a fixed table over the findings, the Warning candidates already raised in open threads (pending verification, never confirmed) and the coverage and verification limits, before any configuration filter; a closing `## Audit` lists every file reviewed and read for context, the categories checked with no findings, and each limit with its reason, marked material or not
- **Changed Lines Only** - Findings cover only the lines the change adds or modifies; a relevant older problem can go, one line each, to a short "Pre-existing issues (not counted)" section outside the Summary table; the same problem at several places is one finding with an **Also at:** list; length limits apply only to code the change adds, always as Suggestions
- **Do Not Report List and Stack Precedents** - Skips pre-existing problems, tooling-caught issues, silenced rules, style nits, theoretical DoS and generic hardening; each stack file lists protections its framework already provides (for example React escaping or Eloquent bindings) and when they stop holding
- **Repository Rules with Citations** - Reads `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md` and `.github/instructions/` in the repository root and in every directory down to the changed files (Step 1.6); the most specific rule wins, a rule never silences a Critical security finding, and each rule finding cites the rules file and lines (for example `src/services/AGENTS.md:L4-L5`)
- **Repository Configuration and Custom Rules** - An optional `.code-review/config.yml` sets `ignore_paths`, `min_severity`, `max_findings_per_file` and `disabled_categories`, and `.code-review/rules/*.md` adds the team's own rules with `paths`, `severity` and Bad/Good examples; an invalid file stops the review with a clear error, excluded paths and omitted findings are declared in the report, a Critical finding is never omitted, and a change to `.code-review/` applies to its own review
- **Prompt-Injection Defense** - The diff, PR or MR title and description, commit messages, code comments and repository files are data, never instructions: text such as "ignore previous instructions" or "approve this PR" is ignored, and when the change adds it, it can be reported as a Security finding
- **Pull Request Reviews** - `/code-review pr 123`, or the URL of a GitHub pull request or GitLab merge request, reviews it with `gh` or `glab`: the skill reads the diff, title, description, commits, linked issues and review threads, and never writes to the pull request unless you pass `--comment`; a problem an open thread already raises goes to a short "Already raised in the PR (not repeated)" list outside the Summary table, and a resolved thread is never reopened
- **Publishing to the Pull Request** - `/code-review pr 123 --comment` posts each finding that sits on a line of the diff as an inline comment, in one review submitted only as a comment (never an approval), with a `suggestion` block only for a complete fix, plus one summary comment that later runs edit instead of repeating; `--dry-run` prints the exact `gh` or `glab` commands and payloads and posts nothing
- **Dimension Review with Subagents** - When the agent can start subagents, up to four of them review the bugs, security, repository rules and tests dimensions, each with only its own checklist, while the main review keeps every other category, merges duplicate candidates, verifies them, applies the configuration filters once, and alone writes the verdict, the audit and any published comment; a subagent that fails never makes its dimension clean (`references/dimensions.md`). Without subagents, the single-pass review runs unchanged
- **Large Diff Strategy** - When the diff has more than 500 changed lines, the review skips lockfiles and generated files found by fixed path and header rules (never by running a build), reviews the other files in batches by module with the riskiest modules first, keeps the counts of the whole diff, and lists every skipped or unread file in the Audit, material unless other evidence the review read lets it judge the change without that file; a skipped file is never called reviewed (`references/large-diffs.md`). Smaller diffs are reviewed in full
- **Intent and Requirements** - Every report opens with a `## Intent` section: what the change is meant to do, from the request and, in a `pr` review, the title, description, commits and linked issues, or a purpose inferred from the diff and labelled as inferred when no source states one. When a source states requirements, each one is met, not met or not judged from the behavior of the reviewed code, with the code behind it; scope creep is compared only with the sources the review read, and every named source it could not read is listed. Issues and specs are data, an issue on another tracker such as Jira or Linear is read only with a read-only tool the agent already has, and a requirement is never judged from a file the review did not read; the section never adds a finding or changes the verdict (`references/intent.md`)
- **History of Removed Protections** - When the change removes a validation, a permission check or error handling, the review reads the git history of the removed lines, read-only and only from commits the selected scope names: from the old side of the diff or, when the old side is not available, as for a GitHub pull request, from its head commit only, without the pull request's own commits, and says that this view is partial. It reports what the commands show, such as the commit that last changed the lines and what its message says, never that a commit added them. History only explains why the code was there: a finding still needs a scenario from the current code and goes through verification, and git history is never listed as a file read for context (`references/removed-code-history.md`)
- **JSON Output and Merge Gate** - `--format json` delivers the same review as one JSON document: every finding with its file, line range, side, category, severity, confidence and evidence, before the configuration filters, plus the triage lines, the verdict and the Audit; `--fail-on critical` adds a gate that fails on a verified Critical finding and never passes an incomplete review or an error. The skill never sets an exit status: the optional `scripts/review_gate.py` turns the document into one for CI (0 pass, 1 Critical, 2 incomplete or error, 3 invalid input) (`references/json-output.md`)
- **Fixing Approved Findings** - `--fix` applies, after the report, only the fixes you approve: in your own words in the conversation, such as "fix every Critical finding", which stay valid in later turns and rounds while they cover the fix, or in answer to the numbered proposal it shows; `--fix` alone is not an approval, and a headless run without one lists the proposal and changes nothing. It edits only the lines that an approved finding names, only when the file still holds the reviewed code, compares each file right before each edit with the reviewed text plus its own earlier edits, leaves a file that someone else changed alone, re-reviews what it changed in at most 2 rounds, and never stages, commits, pushes or publishes (`references/fix.md`)
- **Second Opinion** - `--second-opinion codex` or `--second-opinion gemini` offers the same change, in the same snapshot and with secrets replaced, to that CLI once, but only as a bundle that the CLI can be limited to: `codex` runs from a new empty directory with its command, local-image, app and memory tools turned off, `apply_patch` staying on, and `gemini` is reported unavailable; any candidates it returns are verified like the review's own: agreement is never a vote, nothing outside the diff becomes a finding, and the report says whether it returned candidates, returned none, or was unavailable or failed. The skill never installs, logs in to or configures that CLI (`references/second-opinion.md`)
- **13 Review Categories** - 5 core categories applied to every diff, plus 8 conditional categories loaded from `references/` only when the diff touches their area (accessibility, observability, API design, resilience, migrations, concurrency, i18n, privacy)
- **6 Review Scopes** - Pass `uncommitted`, `staged`, `branch [<base>]`, `commit <sha>`, `range <from>..<to>` or `pr <number|url>` as an argument, or let the skill detect the scope; a run with no user to answer (CI, `claude -p`) never stops to ask, and the report starts with the scope and the command that produced the diff
- **Universal Compatibility** - Works with any LLM supporting Agent Skills

## 📦 Installation

### Option 1: npx skills (Recommended)

Install via the [skills CLI](https://github.com/vercel-labs/skills) — supports 45+ AI agents interactively:

```bash
npx skills add felipereisdev/code-review-skill
```

This will prompt you to select which agents to install to (Claude Code, OpenCode, Cursor, Codex, etc.).

Install to all agents without prompts:

```bash
npx skills add felipereisdev/code-review-skill --all
```

Install to specific agents:

```bash
npx skills add felipereisdev/code-review-skill -a claude-code -a opencode -a cursor
```

Install globally:

```bash
npx skills add felipereisdev/code-review-skill -g --all
```

### Option 2: Direct Clone (Universal)

Works with any AI assistant:

```bash
git clone https://github.com/felipereisdev/code-review-skill.git
```

Then configure your AI assistant to load skills from the cloned directory.

### Option 3: Claude Code

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/code-review-skill" ~/.claude/skills/code-review
```

### Option 4: OpenCode/Codex

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/code-review-skill" ~/.codex/skills/code-review
```

### Option 5: Cursor

```bash
mkdir -p ~/.cursor/skills
ln -s "$(pwd)/code-review-skill" ~/.cursor/skills/code-review
```

## 🚀 Usage

Invoke the skill to review your code:

### Universal

```
/code-review
```

### Claude Code

```bash
/code-review
```

### OpenCode

```
@code-review
```

### Cursor

```
/code-review
```

### Scope arguments

Pass the scope after the command, or leave it out and let the skill detect it:

```
/code-review uncommitted          # staged and unstaged changes, plus untracked files
/code-review staged               # only the changes in the index
/code-review branch main          # this branch since it left main (no base: the default branch)
/code-review commit abc123        # one commit
/code-review range v1.2.0..HEAD   # a range of commits
/code-review pr 123               # a GitHub pull request or GitLab merge request (needs gh or glab)
/code-review pr https://github.com/owner/repo/pull/123   # the same, by URL
/code-review staged compact       # any scope, in compact mode
```

In a run with no user to answer, such as CI or `claude -p`, pass the scope so the review starts at once:

```bash
claude -p "/code-review branch origin/main"
```

### Publishing to the pull request

```
/code-review pr 123 --comment             # post the review to the pull request or merge request
/code-review pr 123 --comment --dry-run   # print what would be posted and post nothing
```

With `--comment`, the skill first writes the whole report in the chat, then posts it with `gh` or `glab`:

- Each finding under `## Findings` whose location is on a line of the diff becomes an inline comment. On GitHub they go out in one review submitted only as a comment (`"event": "COMMENT"`); the skill never approves a pull request or requests changes. A `suggestion` block is added only when the fix replaces exactly the commented lines.
- One summary comment, which starts with `<!-- code-review-skill:summary -->`, lists every finding. Later runs edit that comment instead of adding another, and never repeat a finding the skill already commented on at the same place.
- Findings under Needs human verification appear only in the summary comment; pre-existing and already-raised lines are never posted. Secrets are replaced with `[REDACTED]`. If a command fails, the skill says so, and the report in the chat is still complete.
- The summary comment also carries the triage lines, the `**Ready to merge:**` verdict and the one-line audit; inline comments never do, and the verdict never approves or blocks the pull request.

`--comment` works only with the `pr` scope: with another scope, or `--dry-run` without `--comment`, the skill stops with `Cannot review: ... Nothing was reviewed.`. The rules live in `references/publishing.md`, which the skill reads only when `--comment` is given. `--dry-run` prints each command and its JSON payload under `## Dry run — nothing was published`, for example this review payload, shortened to one inline comment (see [example-output.md](example-output.md) for the full printout):

```json
{
  "commit_id": "9c1e4b7a2f3d5e6c8b0a1d2e3f4a5b6c7d8e9f01",
  "event": "COMMENT",
  "body": "Inline comments from code-review-skill: 8. The summary comment lists every finding.",
  "comments": [
    {"path": "src/controllers/auth.controller.ts", "start_line": 23, "start_side": "RIGHT", "line": 27, "side": "RIGHT", "body": "**Warning — Security** · `src/controllers/auth.controller.ts:23-27` ..."}
  ]
}
```

### JSON output and the merge gate

```
/code-review branch main --format json                     # the result as one JSON document
/code-review branch main --format json --fail-on critical  # the same document with a merge gate
```

`--format json` runs the same review and delivers it as one JSON document instead of the Markdown report: the scope, the Intent lines, every finding with its file, line range, side, category, severity, confidence, evidence and fix, the verification counts, the four triage lines, the verdict row and the Audit. A finding that a `.code-review/config.yml` filter hides from the Markdown report stays in the document with `omitted_by` set, so the counts behind the verdict never disappear. `--fail-on critical` adds a gate to the document:

- `fail` when a verified Critical finding is under Findings, counted before the configuration filters;
- `incomplete` when no changed file was reviewed or the Audit lists a material limit;
- `error` when the run stopped with `Cannot review`;
- `pass` otherwise, `Nothing to review` included. A Critical finding under Needs human verification is not verified and does not fail the gate; the verdict still asks a person to check it.

The contract, with its examples, is in `references/json-output.md`, which the skill reads only with `--format json`.

| Arguments | Result |
| --- | --- |
| `--format json` | the JSON document; its gate is `not_requested` |
| `--format json --fail-on critical` | the JSON document with the gate |
| `--fail-on critical` without `--format json` | `Cannot review: --fail-on needs --format json. Nothing was reviewed.` |
| `--format json` with `compact` | a JSON document with status `error`: `compact cannot be combined with --format json` |
| `--format json` with `--comment` or `--comment --dry-run` | a JSON document with status `error`: `--comment cannot be combined with --format json`; nothing is read for publishing and nothing is published |

The skill's text cannot change the exit status of your agent's CLI: that status says whether the agent ran, never what the review found. To make a CI job fail on the gate, save the agent's reply to a file and run the optional consumer `scripts/review_gate.py` on it. It needs only Python 3 and its standard library, and the skill itself never needs it. Its exit statuses:

| Exit | Meaning |
| --- | --- |
| 0 | `pass`: a complete review with no verified Critical finding, or nothing to review |
| 1 | `fail`: at least one verified Critical finding |
| 2 | `incomplete` or `error`: the review is not complete, or the run stopped with `Cannot review` |
| 3 | invalid input: empty, not exactly one JSON document, another schema or version, a document that contradicts itself, its file accounting included, or a review run without `--fail-on critical` |

The consumer checks the structure of the document and the facts it states; it cannot check that the review read what the document says, or that its evidence and judgments are right.

Try it on the handwritten fixtures, which are examples of the contract, not the output of an agent:

```bash
python3 scripts/review_gate.py evals/tests/fixtures/json/pass.json         # exit 0
python3 scripts/review_gate.py evals/tests/fixtures/json/critical.json     # exit 1
python3 scripts/review_gate.py evals/tests/fixtures/json/incomplete.json   # exit 2
python3 scripts/review_gate.py evals/tests/fixtures/json/error.json        # exit 2
printf '' | python3 scripts/review_gate.py -                                # exit 3
```

In a CI job, the two steps look like this sketch; replace the first command with your agent's headless command. This repository's CI runs only the offline fixtures, never an agent:

```yaml
- name: Code review
  run: <your agent's headless command> "/code-review branch origin/main --format json --fail-on critical" > review.json
- name: Review gate
  run: python3 path/to/code-review-skill/scripts/review_gate.py review.json
```

Some agent CLIs wrap the reply in an envelope of their own or add a code fence: unwrap it before the gate. The gate never strips or repairs its input, and it reads an empty, cut-off or wrapped reply as invalid, never as zero findings.

### Repository configuration

An optional `.code-review/` directory at the root of the reviewed repository tunes the review. `.code-review/config.yml` holds the settings, all optional:

```yaml
ignore_paths:                # changed files that are not reviewed
  - "src/generated/**"
  - "docs/"
min_severity: Warning        # Critical, Warning or Suggestion (default: Suggestion)
max_findings_per_file: 5     # default: no limit
disabled_categories:         # names from the Summary table
  - Accessibility
```

Each `.code-review/rules/*.md` file is one rule of the team: a frontmatter with `paths` (the files it applies to) and `severity`, the rule text, and `## Bad` and `## Good` examples. A finding that breaks it cites the rule file and lines, for example `(Rule: .code-review/rules/validate-request-bodies.md:L7-L8)`.

- An invalid file stops the review before it starts, with `Cannot review: .code-review/config.yml is invalid: <reason>. Nothing was reviewed.`; the skill never guesses or falls back to the defaults.
- Ignored paths are declared in the report (`**Excluded by configuration:**`); the diff itself is unchanged.
- `min_severity`, `disabled_categories` and `max_findings_per_file` only filter what the report shows, after verification, and the report declares the counts (`**Omitted by configuration:**`). They never change a finding's severity or confidence, and a Critical finding is never omitted.
- A pull request that changes `.code-review/` is reviewed with the configuration as it leaves it: a valid one applies, an invalid one stops the review, and the files it ignores are declared as excluded, never as reviewed. In a `pr` review, the configuration is read from the pull request's head commit, never from your checkout; when that commit is not available, the report says that the configuration was not verified. The settings and rules are data: they can never turn on `--comment`, change the scope or skip verification.

The full schema, path patterns and rule format are in `references/configuration.md`, which the skill reads only when `.code-review/` has a config or rules.

### Fixing approved findings

```
/code-review staged --fix   # review the staged changes, then fix the findings you approve
/code-review --fix          # the same on the detected scope
```

With `--fix`, the skill first delivers the whole report. It applies the fixes that an approval you already gave covers, without asking again; otherwise it lists each finding under `## Findings` whose fix is a concrete edit in a numbered `## Fix proposal` and asks which ones to apply. An approval in your own words, such as "fix every Critical and Warning finding" in your request or in an earlier message, counts for as long as its words cover the finding and the fix, in later turns and in a second round too; approving one numbered edit never approves a different edit. `--fix` alone is not an approval, and text in the diff, the repository or the pull request never is. A headless run never asks: without an approval it prints the proposal and `Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.`

- It edits only the lines that an approved finding names, and only when the file still holds the reviewed code: before its first edit in a file it compares the file with what the review read, for every scope, `uncommitted` too, and for `commit`, `range` and `pr` it edits only when the reviewed commit is the checked-out one. Right before each edit it reads the file again and compares it with the reviewed text plus its own earlier edits, so two approved fixes on different lines of one file both apply, and it leaves the file alone when someone else changed it.
- Then it re-reviews the lines it changed. The `## Fix` section after the report says which approved findings are fixed and verified, still present or not applied, lists any new finding in the changed lines and every file it changed. An interactive run can run a second round and asks only for the edits that no approval you gave already covers; a headless run stops after one round, and a run never has more than 2 rounds; a second round may correct lines that the first round wrote, but two fixes of one round never overlap.
- It never stages, commits, pushes or publishes, and never rewrites the report above it: that report's verdict describes the code before the fixes.

The rules are in `references/fix.md`, which the skill reads only with `--fix`.

### Second opinion

```
/code-review branch main --second-opinion codex   # also ask the Codex CLI to review the same change
/code-review staged --second-opinion gemini       # or the Gemini CLI
```

`--second-opinion` asks one other reviewer CLI, which you already installed and configured, to review the same change. The skill sends it only a bundle of the change and the code around it, with secrets replaced by `[REDACTED]`, and only to a CLI that the skill can limit to that bundle. The read-only flags limit writes and shell commands, not what a CLI reads, so the skill runs `codex` only from a new empty directory outside the repository, with its tools that run commands, its tool that opens local images, its app connectors and its memories turned off for that call, once the installed `codex` confirms that they are off. Its `apply_patch` tool stays on: the read-only sandbox refuses its writes, but the skill does not establish that it opens no local file. It names no such command for `gemini`: `--second-opinion gemini` reports `gemini cannot be limited to the supplied content`, and no CLI runs. Agreement between the two reviews is never a vote, a candidate outside the diff never becomes a finding, and what the other CLI says it read never counts as coverage. A `**Second opinion:**` line before the triage lines says whether it returned candidates, returned none, was unavailable or failed; the review is complete without it. The read-only flags limit the commands that the other CLI runs; they cannot promise anything about other tools you configured for it. The prompt goes to the provider that CLI is configured for. The skill never installs, logs in to or configures that CLI.

The rules are in `references/second-opinion.md`, which the skill reads only with `--second-opinion`.

| Arguments | Result |
| --- | --- |
| `--fix` | the report, then the fix proposal or the approved fixes, and the `## Fix` section |
| `--fix` in a headless run without an approval | the report, the proposal and `Fix not applied: no fix was approved before this headless run; ...`; no file is changed |
| `--fix` on `commit`, `range` or `pr` when the reviewed commit is not checked out | the report and `Fix not applied: the working tree is not the reviewed code: ...`; no file is changed |
| `--fix` with `--format json` | a JSON document with status `error`: `--fix cannot be combined with --format json` |
| `--fix` with `--comment` | `Cannot review: --fix cannot be combined with --comment; publish and fix in separate runs. Nothing was reviewed.` |
| `--second-opinion codex` or `--second-opinion gemini` | the report, with the candidates of that CLI verified like the review's own, and its `**Second opinion:**` line |
| `--second-opinion` with another value | `Cannot review: --second-opinion needs codex or gemini. Nothing was reviewed.` |
| `--second-opinion` with `--format json` | a JSON document with status `error`: `--second-opinion cannot be combined with --format json` |

The examples in `references/fix.md` and `references/second-opinion.md` are fictional. This repository's checks verify their wording and their consistency offline, never by running an agent, a fix or another CLI.

## 📋 Review Process

The skill takes the scope from the argument, and detects it when there is none:

1. **Uncommitted changes** (`uncommitted`) - staged and unstaged changes plus untracked files (`git diff HEAD`)
2. **Staged changes only** (`staged`) - files added to the index (`git diff --cached`)
3. **Current branch vs base** (`branch [<base>]`) - all commits since the branch left the base (`git diff <base>...HEAD`)
4. **Specific commit** (`commit <sha>`) - changes in a single commit (`git show <sha>`)
5. **Commit range** (`range <from>..<to>`) - changes across a range (`git diff <from>..<to>`)
6. **Pull request or merge request** (`pr <number|url>`) - the pull request's diff, read with `gh pr diff` (GitHub) or `glab mr diff` (GitLab)

Without an argument, the skill reviews the uncommitted changes if there are any; otherwise, a branch with commits ahead of the default branch (from `origin/HEAD`, falling back to `main` or `master`) is reviewed against it; otherwise it says there is nothing to review. It asks only in an interactive run whose detection is ambiguous, and never in a headless run. An invalid argument, such as an unknown commit or base, stops with `Cannot review: ... Nothing was reviewed.` instead of reviewing another scope. The report starts with the scope and its git command, for example `**Scope:** branch main (git diff main...HEAD)`.

A `pr` review picks `gh` or `glab` from the URL or from the `origin` remote; that CLI must be installed and logged in, or the skill stops with `Cannot review: ... Nothing was reviewed.`. It reads the diff, title, description, commits, linked issues and review threads, never writes to the pull request unless you pass `--comment` (see Publishing to the pull request), and starts the report with, for example, `**Scope:** pr 123 (gh pr diff 123)`. A problem that an open review thread already raises at the same place is listed, one line each with the thread's URL, under `## Already raised in the PR (not repeated)` instead of being reported again. A Critical problem stays a finding, and a resolved thread is never reopened: a finding that matches one is reported only because the current diff still has the problem, and it cites the thread.

## 🛡️ Review Categories

| Category | Applied | What It Checks |
|----------|---------|----------------|
| **Security** | Always | Injection vulnerabilities, auth, secrets, input validation |
| **Performance** | Always | N+1 queries, caching, pagination, memory leaks |
| **Tests** | Always | Coverage, edge cases, mocking, assertions |
| **Architecture** | Always | SOLID, DRY, KISS, separation of concerns |
| **Potential Bugs** | Always | Null dereferences, off-by-one errors, race conditions |
| **Accessibility** | When the diff changes UI markup, templates, components or styles | Semantic HTML, ARIA, keyboard navigation |
| **Observability** | When the diff changes logging, error handling, metrics, jobs or external calls | Logging, metrics, error tracking |
| **API Design** | When the diff changes API endpoints, schemas or API clients | HTTP methods, status codes, versioning |
| **Resilience** | When the diff changes external calls, queues or critical flows | Timeouts, retries, circuit breakers |
| **Database** | When the diff changes migrations or schema definitions | Zero-downtime migrations, indexing |
| **Concurrency** | When the diff changes shared state, locks, jobs or parallel work | Thread safety, atomic operations |
| **i18n** | When the project has several locales and the diff changes user-facing text, formatting or RTL-sensitive layout | Translation keys, locale formatting, RTL layout |
| **Privacy** | When the diff collects, stores, logs or shares user data | PII handling, data retention, consent |

The five **Always** categories live in `SKILL.md`. Each of the others lives in its own file under `references/`, and the skill reads it only when the diff matches its trigger, so a CSS-only diff does not load the API, migration or concurrency rules.

## 🏗️ Supported Stacks

### Frontend
- React
- Vue.js (+ Inertia.js)
- Angular
- Svelte
- Nuxt

### Backend
- Node.js
- Python
- Laravel (PHP)
- Go
- Java Spring
- .NET

### Testing
- Pest PHP

### Mobile
- React Native
- Flutter

### DevOps & Infrastructure
- Docker
- Terraform
- Kafka

### Styling & Languages
- TypeScript
- Tailwind CSS (v3/v4 detection)

## 🏛️ Architectural Patterns

- **Clean Architecture** - Layer separation, dependency inversion
- **DDD** - Domain-driven design patterns
- **Event-Driven** - Async messaging, event sourcing
- **Microservices** - Service boundaries, inter-service communication
- **CQRS** - Command query responsibility segregation

## 📄 Output Format

Each finding carries a severity, a location inside the diff, a concrete trigger → effect scenario and a confidence level:

```
### [Category] — [Severity]

**Location:** `path/to/file.ext:start-end`
**Issue:** Brief description of the problem.
**Evidence:** Trigger → effect: the concrete scenario in which it goes wrong.
**Confidence:** High
**Fix:** Suggested correction or approach.
```

- **Severity** has fixed definitions: Critical = crash, data loss or security hole; Warning = wrong result in some scenario, or a hot path doing work or queries that grow with data size (N+1 queries, unbounded queries or loads, O(n^2) work per request), because that causes timeouts or outages at scale; Suggestion = correct but suboptimal. Advice that only says "verify" or "ensure" is never above Warning.
- **Confidence**: High findings are listed; Medium findings go to a separate "Needs human verification" section; Low findings are not reported.
- **Verification**: before the report, every Critical and Warning finding is checked against the real code (guards, callers, types, tests, framework configuration) and comes out CONFIRMED, DOWNGRADED or REFUTED. Refuted findings are dropped and the report states how many there were. Suggestions skip this step.
- **Repository rules**: a finding that breaks a rule from `CLAUDE.md`, `AGENTS.md` or another rules file adds a **Rule:** line that cites the rules file and its lines, for example `src/services/AGENTS.md:L4-L5`; in compact mode the line ends with `(Rule: src/services/AGENTS.md:L4-L5)`. Without a citation that can be checked, it is not a rule finding.
- **Repository configuration**: with `.code-review/`, the report adds a `**Configuration:**` line and, when files were ignored, an `**Excluded by configuration:**` line after the Scope line, and an `**Omitted by configuration:**` line after the verification line.
- **Changed lines, pre-existing issues and repeats**: findings cite only lines the change adds or modifies. An older problem the change does not touch is never a finding; it can go, one line each (`path:line — problem`), under `## Pre-existing issues (not counted)`, which the Summary table does not count. The same problem at several places is one finding whose **Also at:** line lists the other places; in compact mode the line ends with `(also at path:line)` before any rule citation.
- **Already raised in the PR**: in a `pr` review, the lines under `## Already raised in the PR (not repeated)` have no severity and are not counted in the Summary table; a Warning candidate already raised in an open thread makes the verdict `With fixes` as pending verification, because an open thread does not prove the problem, and the verdict never calls it confirmed or fixed.
- **Triage and verdict**: after the verification line come `**Review effort:** <n>/5` (from the line and file counts measured on the diff, never estimated), `**Relevant tests:**` (with `Execution:` saying what ran, or `not run`), `**Look first:**` and `**Ready to merge:**`. No changed file reviewed, a Critical finding, or a material limit such as changed lines the review could not read gives `No`; a Warning finding, a finding under Needs human verification or a Warning candidate already raised in an open thread gives `With fixes`; otherwise `Yes`. Files excluded by configuration are counted in the verdict, never called clean, and the verdict never approves or blocks a pull request.
- **Audit**: the report ends with `## Audit` (one `**Audit:**` line in compact mode): every file reviewed and every file read for context, each once (repository files by their path, the skill's own files as `skill:<path>`), the categories checked with no findings, the already-raised Warning candidates in a `pr` review, and each limit with its reason, such as `not read`, `API not validated` or `tests not verified`, marked `material` when it leaves a changed behavior, or a contract the change relies on, unjudged.
- **Compact mode**: ask for `/code-review compact` to get one line per finding (`path:line: Severity: problem → fix`).

Plus a summary table that counts the High-confidence findings:

```
| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 1       | 2          |     |
| Performance           | 0        | 0       | 1          |     |
...
```

## 🔧 How It Works

This skill follows the [Agent Skills Standard](https://agentskills.io), making it compatible with any AI assistant that supports:

- **Tool Calling**: Read, Grep, Glob, Bash
- **Subagents**: Forked execution for safe analysis
- **Skill Discovery**: Automatic loading from skills directories

### Supported Tools

- `Read` - Codebase exploration and stack files
- `Grep` - Pattern searching in code
- `Glob` - File discovery
- `Bash` - Git operations and diff extraction

Runs with automatic stack detection and loads only the relevant stack and pattern rules, plus the conditional categories whose trigger the diff matches.

## 📁 Project Structure

```
code-review-skill/
├── SKILL.md              # Main skill definition
├── README.md             # This file
├── LICENSE               # MIT License
├── example-output.md     # Sample review report
├── .gitignore           # Git ignore rules
├── .github/workflows/   # CI
│   └── ci.yml           # Docs checks, SKILL.md references, eval case validation
├── scripts/             # Maintenance scripts
│   ├── check-docs.sh    # Docs, frontmatter and SKILL.md file-reference checks
│   ├── review_gate.py   # Optional consumer: turns a --format json document into a CI exit status
│   └── test-check-docs.sh  # Negative tests for check-docs.sh
├── evals/               # Review-quality evals (planted-bug vs. clean diff pairs)
│   ├── README.md        # How to run the evals
│   ├── run.py           # Runner: temp repo per case, headless agent, scoring, controls, provenance
│   ├── score.py         # Report parser and scorer
│   ├── aggregate.py     # Checks a measured study and computes its baseline metrics
│   ├── make-patch.sh    # Builds a case patch from base/ and an edited copy
│   ├── baseline.json    # Current baseline: the aggregate of baseline/expanded/
│   ├── baseline/        # Initial run of 2026-10-23, the original, rescored and corrected expanded studies (protocol, hashes, raw reports)
│   ├── cases/           # One folder per pair: base/, bug.patch, clean.patch, pair.json
│   ├── controls/        # Behavior controls: JSON gate, headless --fix, unavailable second opinion
│   ├── profiles/        # Frozen agent profiles for measured studies
│   └── tests/           # Offline tests for the runner, the scorer, the --comment dry-run payloads, the triage verdict and the --format json gate
├── patterns/            # Architectural pattern guidelines
│   ├── clean-architecture.md
│   ├── cqrs.md
│   ├── ddd.md
│   ├── event-driven.md
│   └── microservices.md
├── references/          # Conditional checklists, read only when the diff touches their area
│   ├── accessibility.md
│   ├── api-design.md
│   ├── concurrency.md
│   ├── configuration.md # Settings and custom rules from .code-review/ (not a review category)
│   ├── database-migrations.md
│   ├── dimensions.md    # Dimension review with subagents (not a review category)
│   ├── fix.md           # Approved fixes and their re-review for --fix (not a review category)
│   ├── i18n.md
│   ├── intent.md        # Intent and requirements of every review (not a review category)
│   ├── json-output.md   # JSON document and merge gate for --format json (not a review category)
│   ├── large-diffs.md   # Strategy for diffs over 500 changed lines (not a review category)
│   ├── observability.md
│   ├── privacy.md
│   ├── publishing.md    # Publishing rules for --comment (not a review category)
│   ├── removed-code-history.md # Git history of removed validation, permission checks and error handling (not a review category)
│   ├── resilience.md
│   └── second-opinion.md # Second opinion from another reviewer CLI for --second-opinion (not a review category)
└── stacks/              # Technology-specific rules
    ├── angular.md
    ├── docker.md
    ├── dotnet.md
    ├── flutter.md
    ├── go.md
    ├── inertia.md
    ├── java-spring.md
    ├── kafka.md
    ├── laravel.md
    ├── node.md
    ├── nuxt.md
    ├── pest.md
    ├── python.md
    ├── react-native.md
    ├── react.md
    ├── svelte.md
    ├── tailwind.md
    ├── terraform.md
    ├── typescript.md
    └── vue.md
```

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Run `bash scripts/check-docs.sh` and `bash scripts/test-check-docs.sh` and make sure all checks pass; if you change `SKILL.md`, `stacks/`, `patterns/` or `references/`, also run the evals ([evals/README.md](evals/README.md)) and compare with `evals/baseline.json`
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by industry code review best practices
- Built following the [Agent Skills Standard](https://agentskills.io)
- Compatible with Claude Code, OpenCode, Cursor, and any Agent Skills-compatible AI
- Community-driven development

## 🔗 Links

- [Agent Skills Standard](https://agentskills.io)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [OpenCode Documentation](https://opencode.ai/docs/skills)
- [Cursor Documentation](https://cursor.sh)

## 💡 Request Support for Your AI Assistant

If your favorite AI assistant doesn't support Agent Skills yet, open an issue or reach out to their team! This skill is designed to work with any tool that implements the standard.

---

⭐ Star this repo if it helps you write better code!

**Made with ❤️ for the AI coding community**
