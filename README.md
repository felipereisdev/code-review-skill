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
- **Multi-Stack Support** - 17+ technology stacks covered
- **Pattern-Specific Rules** - Apply Clean Architecture, DDD, CQRS, Microservices guidelines
- **Severity-Based Reporting** - Critical, Warning, and Suggestion levels
- **15 Review Categories** - From Security to Privacy Compliance
- **15 Review Scopes** - Uncommitted changes, staged, branch comparison, specific commits
- **Universal Compatibility** - Works with any LLM supporting Agent Skills

## 📦 Installation

### Option 1: Direct Clone (Universal)

Works with any AI assistant:

```bash
git clone https://github.com/felipereisdev/code-review-skill.git
```

Then configure your AI assistant to load skills from the cloned directory.

### Option 2: Claude Code

```bash
# Clone into your global skills
mkdir -p ~/.claude/skills
ln -s "$(pwd)/code-review-skill" ~/.claude/skills/code-review-skill
```

### Option 3: OpenCode/Codex

```bash
# Clone into your global skills
mkdir -p ~/.codex/skills
ln -s "$(pwd)/code-review-skill" ~/.codex/skills/code-review-skill
```

### Option 4: Cursor

```bash
# Clone into your Cursor skills directory
mkdir -p ~/.cursor/skills
ln -s "$(pwd)/code-review-skill" ~/.cursor/skills/code-review-skill
```

## 🚀 Usage

Invoke the skill to review your code:

### Universal

```
/code-review-skill
```

### Claude Code

```bash
/code-review-skill
```

### OpenCode

```
@code-review-skill
```

### Cursor

```
/code-review-skill
```

## 📋 Review Process

The skill will ask you to choose the review scope:

1. **Uncommitted changes** - files modified but not staged (`git diff HEAD`)
2. **Staged changes only** - files added to index (`git diff --cached`)
3. **Current branch vs base** - all commits compared to merge base
4. **Specific commit** - changes in a single commit
5. **Commit range** - changes across a range

## 🛡️ Review Categories

| Category | What It Checks |
|----------|----------------|
| **Security** | Injection vulnerabilities, auth, secrets, input validation |
| **Performance** | N+1 queries, caching, pagination, memory leaks |
| **Tests** | Coverage, edge cases, mocking, assertions |
| **Architecture** | SOLID, DRY, KISS, separation of concerns |
| **Potential Bugs** | Null dereferences, off-by-one errors, race conditions |
| **Accessibility** | Semantic HTML, ARIA, keyboard navigation |
| **Observability** | Logging, metrics, error tracking |
| **API Design** | HTTP methods, status codes, versioning |
| **Resilience** | Timeouts, retries, circuit breakers |
| **Database** | Zero-downtime migrations, indexing |
| **Concurrency** | Thread safety, atomic operations |
| **i18n** | Translation keys, locale formatting |
| **Privacy** | PII handling, data retention, consent |

## 🏗️ Supported Stacks

### Frontend
- React
- Vue.js
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

### Mobile
- React Native
- Flutter

### DevOps & Infrastructure
- Docker
- Terraform
- Kafka

### Styling & Languages
- TypeScript
- Tailwind CSS

## 🏛️ Architectural Patterns

- **Clean Architecture** - Layer separation, dependency inversion
- **DDD** - Domain-driven design patterns
- **Event-Driven** - Async messaging, event sourcing
- **Microservices** - Service boundaries, inter-service communication
- **CQRS** - Command query responsibility segregation

## 📄 Output Format

Findings are reported with severity levels:

```
### [Category] — [Severity]

**File:** `path/to/file.ext:line`
**Issue:** Brief description of the problem.
**Fix:** Suggested correction or approach.
```

Plus a comprehensive summary table:

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

Runs with automatic stack detection and loads only relevant pattern/stack rules.

## 📁 Project Structure

```
code-review-skill/
├── SKILL.md              # Main skill definition
├── README.md             # This file
├── .gitignore           # Git ignore rules
├── patterns/            # Architectural pattern guidelines
│   ├── clean-architecture.md
│   ├── cqrs.md
│   ├── ddd.md
│   ├── event-driven.md
│   └── microservices.md
└── stacks/              # Technology-specific rules
    ├── angular.md
    ├── docker.md
    ├── dotnet.md
    ├── flutter.md
    ├── go.md
    ├── java-spring.md
    ├── kafka.md
    ├── laravel.md
    ├── node.md
    ├── nuxt.md
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
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

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
