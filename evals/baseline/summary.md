# Code review skill evals

- Generated: 2026-10-23T09:18:30Z
- Agent: claude (model: sonnet)
- MCP/Context7: disabled; API-validation step skipped
- Skill: ae62bbea62653b5df422f424814cdc53162b870c (SKILL.md sha256 f326b9e15c59)
- Recall: 6/6 (100%)
- False positives: 5 Critical/Warning finding(s) in 3/6 clean case(s)
- Errors: 0

| Case | Kind | Stack | Status | Result | Details |
| --- | --- | --- | --- | --- | --- |
| n-plus-one-laravel/bug | bug | laravel | ok | PASS | detected: Performance — Warning (N+1 queries) |
| n-plus-one-laravel/clean | clean | laravel | ok | FAIL | 1 Critical/Warning finding(s) |
| null-node/bug | bug | node | ok | PASS | detected: Potential Bugs — Critical |
| null-node/clean | clean | node | ok | PASS | 0 Critical/Warning finding(s) |
| off-by-one-python/bug | bug | python | ok | PASS | detected: Potential Bugs — Critical |
| off-by-one-python/clean | clean | python | ok | PASS | 0 Critical/Warning finding(s) |
| sqli-laravel/bug | bug | laravel | ok | PASS | detected: Security — Critical |
| sqli-laravel/clean | clean | laravel | ok | FAIL | 2 Critical/Warning finding(s) |
| swallowed-error-ts/bug | bug | typescript | ok | PASS | detected: Potential Bugs — Critical |
| swallowed-error-ts/clean | clean | typescript | ok | FAIL | 2 Critical/Warning finding(s) |
| xss-react/bug | bug | react | ok | PASS | detected: Security — Critical |
| xss-react/clean | clean | react | ok | PASS | 0 Critical/Warning finding(s) |
