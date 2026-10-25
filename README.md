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
- **API Validation** - Validates library usage against live documentation to reduce false positives
- **Multi-Stack Support** - 20 technology stacks covered
- **Pattern-Specific Rules** - Apply Clean Architecture, DDD, CQRS, Microservices guidelines
- **Severity-Based Reporting** - Critical, Warning, and Suggestion levels
- **Changed Lines Only** - Findings cover only the lines the change adds or modifies; a relevant older problem can go, one line each, to a short "Pre-existing issues (not counted)" section outside the Summary table; the same problem at several places is one finding with an **Also at:** list; length limits apply only to code the change adds, always as Suggestions
- **Do Not Report List and Stack Precedents** - Skips pre-existing problems, tooling-caught issues, silenced rules, style nits, theoretical DoS and generic hardening; each stack file lists protections its framework already provides (for example React escaping or Eloquent bindings) and when they stop holding
- **Repository Rules with Citations** - Reads `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md` and `.github/instructions/` in the repository root and in every directory down to the changed files (Step 1.6); the most specific rule wins, a rule never silences a Critical security finding, and each rule finding cites the rules file and lines (for example `src/services/AGENTS.md:L4-L5`)
- **Prompt-Injection Defense** - The diff, PR or MR title and description, commit messages, code comments and repository files are data, never instructions: text such as "ignore previous instructions" or "approve this PR" is ignored, and when the change adds it, it can be reported as a Security finding
- **13 Review Categories** - 5 core categories applied to every diff, plus 8 conditional categories loaded from `references/` only when the diff touches their area (accessibility, observability, API design, resilience, migrations, concurrency, i18n, privacy)
- **5 Review Scopes** - Pass `uncommitted`, `staged`, `branch [<base>]`, `commit <sha>` or `range <from>..<to>` as an argument, or let the skill detect the scope; a run with no user to answer (CI, `claude -p`) never stops to ask, and the report starts with the scope and its git command
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
/code-review staged compact       # any scope, in compact mode
```

In a run with no user to answer, such as CI or `claude -p`, pass the scope so the review starts at once:

```bash
claude -p "/code-review branch origin/main"
```

## 📋 Review Process

The skill takes the scope from the argument, and detects it when there is none:

1. **Uncommitted changes** (`uncommitted`) - staged and unstaged changes plus untracked files (`git diff HEAD`)
2. **Staged changes only** (`staged`) - files added to the index (`git diff --cached`)
3. **Current branch vs base** (`branch [<base>]`) - all commits since the branch left the base (`git diff <base>...HEAD`)
4. **Specific commit** (`commit <sha>`) - changes in a single commit (`git show <sha>`)
5. **Commit range** (`range <from>..<to>`) - changes across a range (`git diff <from>..<to>`)

Without an argument, the skill reviews the uncommitted changes if there are any; otherwise, a branch with commits ahead of the default branch (from `origin/HEAD`, falling back to `main` or `master`) is reviewed against it; otherwise it says there is nothing to review. It asks only in an interactive run whose detection is ambiguous, and never in a headless run. An invalid argument, such as an unknown commit or base, stops with `Cannot review: ... Nothing was reviewed.` instead of reviewing another scope. The report starts with the scope and its git command, for example `**Scope:** branch main (git diff main...HEAD)`.

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
- **Changed lines, pre-existing issues and repeats**: findings cite only lines the change adds or modifies. An older problem the change does not touch is never a finding; it can go, one line each (`path:line — problem`), under `## Pre-existing issues (not counted)`, which the Summary table does not count. The same problem at several places is one finding whose **Also at:** line lists the other places; in compact mode the line ends with `(also at path:line)` before any rule citation.
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
│   └── test-check-docs.sh  # Negative tests for check-docs.sh
├── evals/               # Review-quality evals (planted-bug vs. clean diff pairs)
│   ├── README.md        # How to run the evals
│   ├── run.py           # Runner: temp repo per case, headless agent, scoring
│   ├── score.py         # Report parser and scorer
│   ├── make-patch.sh    # Builds a case patch from base/ and an edited copy
│   ├── baseline.json    # Baseline metrics of the skill before review-behavior changes
│   ├── baseline/        # Baseline summary.md and raw reports
│   ├── cases/           # One folder per pair: base/, bug.patch, clean.patch, pair.json
│   └── tests/           # Offline tests for the runner and scorer
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
│   ├── database-migrations.md
│   ├── i18n.md
│   ├── observability.md
│   ├── privacy.md
│   └── resilience.md
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
