# Example Output

This is an example of the code review output format. The actual review will vary based on your codebase and the changes being reviewed.

## Scenario

Reviewing pull request #123 on GitHub (`https://github.com/acme/shop-api/pull/123`), which adds user authentication with JWT to a Node.js/Express API. The repository has an `AGENTS.md` at its root and another in `src/services/`, whose lines 4-5 say that services log through `logger` from `src/lib/logger.ts` and never call `console.*`. The pull request also edits `src/app.ts` to mount the new auth routes; the `/health` handler at the top of that file is older than the branch. The pull request already has two review threads: an open one on `src/routes/auth.routes.ts:8` saying that `POST /auth/login` has no rate limit, and a resolved one on `src/services/auth.service.ts:45` asking to remove the hard-coded JWT secret. Its description says that it adds registration, login, token refresh and logout, closes #98 and follows the security design in SEC-42, a ticket on another tracker for which the agent has no tool; it names SEC-42 only as background, and no changed behavior depends on what SEC-42 says. Issue #98 states four requirements: login returns an access token and a refresh token for valid credentials, logout revokes the refresh token, a refresh token works only once, and five failed logins in a row lock the account. The diff has more than 500 changed lines and no lockfile or generated file, so the review follows the large diff strategy and reviews all 6 changed files in batches. The review was started with `/code-review pr 123`.

---

## Code Review Report

**Scope:** pr 123 (gh pr diff 123)

## Intent

**Intent:** Add registration, login, token refresh and logout with JWT to the API (title, description, #98).
**Requirements:** 2 met, 1 not met, 1 not judged.
- Met — login returns an access token and a refresh token for valid credentials (#98): `src/controllers/auth.controller.ts:15-40` returns both tokens from `POST /auth/login`.
- Met — logout revokes the refresh token (#98): `src/controllers/auth.controller.ts:96-110` deletes the stored refresh token.
- Not met — a refresh token works only once (#98): the Critical finding at `src/services/auth.service.ts:89-97` lets two concurrent requests use the same refresh token.
- Not judged — five failed logins in a row lock the account (#98): `src/services/auth.service.ts:131-133` counts the failures, but whether parallel attempts lose a count depends on the gateway configuration, which is not in the repository.
**Scope creep:** compared only with the description and #98: `src/controllers/auth.controller.ts:300-487` (password reset and email verification, which neither asks for).
**Sources not read:** SEC-42 (no read-only tool for its tracker).

### What Was Done Well

- Clean separation between auth controller and service layers
- Proper use of async/await patterns
- Good error handling structure with custom error classes
- Tests cover both happy path and error scenarios

---

## Findings

### Security — Critical

**Location:** `src/services/auth.service.ts:45-46`
**Issue:** The JWT secret falls back to the hard-coded string `'dev-secret'` when `JWT_SECRET` is not set.
**Evidence:** A deployment without `JWT_SECRET` signs every token with `'dev-secret'` → anyone who reads this repository can forge a token for any user ID and pass `authMiddleware`. Raised in https://github.com/acme/shop-api/pull/123#discussion_r1188 and marked resolved, but the fallback is still in the current diff.
**Confidence:** High
**Fix:** Fail at startup instead of falling back:
```typescript
if (!process.env.JWT_SECRET) {
  throw new Error('JWT_SECRET environment variable is required');
}
```

### Potential Bugs — Critical

**Location:** `src/services/auth.service.ts:89-97`
**Issue:** Token refresh reads the stored refresh token, then deletes it and creates a new one in separate queries.
**Evidence:** Two concurrent `POST /auth/refresh` requests with the same refresh token both pass the `findUnique` check before either delete runs → both receive a new valid refresh token, so a stolen token can be replayed without ending the session. Verification checked `POST /auth/refresh`, the only caller of the rotation code, and found no lock or transaction around the read and the delete.
**Confidence:** High
**Fix:** Rotate the token in one transaction, so the second request fails on the delete:
```typescript
await db.$transaction(async (tx) => {
  await tx.refreshTokens.delete({ where: { token: oldToken } });
  await tx.refreshTokens.create({ data: { token: newToken, userId } });
});
```

### Security — Warning

**Location:** `src/controllers/auth.controller.ts:23-27`
**Issue:** Login answers "User not found" for an unknown email and "Invalid credentials" for a wrong password.
**Evidence:** `POST /auth/login` with `alice@example.com` and a wrong password answers "Invalid credentials" when that account exists and "User not found" when it does not → an attacker can find out which emails are registered.
**Confidence:** High
**Fix:** Return the same message for both cases: "Invalid email or password".

### Performance — Suggestion

**Location:** `src/services/auth.service.ts:67-69`
**Issue:** The query that loads the user for token generation fetches every column, including the password hash, when only `id` and `email` are used.
**Evidence:** Each token refresh reads the full user row, including `passwordHash` → the result is correct, but the query moves more data than needed and keeps the hash in memory for no reason.
**Confidence:** High
**Fix:** Select only the needed fields:
```typescript
const user = await db.users.findFirst({
  where: { email },
  select: { id: true, email: true }
});
```

### Tests/Coverage — Suggestion

**Location:** `tests/auth.test.ts:34-41`
**Issue:** The login test mocks `jwt.sign`, so it never checks the claims or the expiry of the real token.
**Evidence:** If `generateToken` stopped passing `expiresIn`, this test would still pass → tokens that never expire could ship unnoticed. The code is correct today; the test is weaker than it looks.
**Confidence:** High
**Fix:** Verify the real token:
```typescript
const decoded = jwt.verify(token, process.env.JWT_SECRET!);
expect(decoded).toHaveProperty('userId');
expect(decoded).toHaveProperty('exp');
```

### Architecture — Suggestion

**Location:** `src/middleware/auth.middleware.ts:18-74`
**Issue:** The new `authMiddleware` is 57 lines long and handles token extraction, verification and user lookup.
**Evidence:** Adding API-key authentication means editing this one function in three places → the change is harder to review and to test in isolation. Behavior is correct today.
**Confidence:** High
**Fix:** Extract token extraction and user lookup into separate functions:
```typescript
const extractToken = (authHeader: string): string | null => { ... }
const getUserFromToken = (token: string): Promise<User | null> => { ... }
```

### Code & File Size — Suggestion

**Location:** `src/controllers/auth.controller.ts:1-487`
**Issue:** The branch adds a 487-line controller for login, register, logout, token refresh, password reset and email verification.
**Evidence:** A change to password reset edits the same file as login → unrelated changes conflict and every review covers all six flows. The file is new in this branch, and the other controllers in `src/controllers/` stay under 200 lines. Behavior is correct.
**Confidence:** High
**Fix:** Split into separate controllers: `login.controller.ts`, `register.controller.ts`, etc.

### Observability — Suggestion

**Location:** `src/services/auth.service.ts:112`
**Rule:** `src/services/AGENTS.md:L4-L5`
**Also at:** `src/services/auth.service.ts:124`
**Issue:** Authentication failures are logged with `console.error` in two places, which the rules for `src/services/` forbid.
**Evidence:** `src/services/AGENTS.md:L4-L5` says services log through `logger` and never call `console.*`; lines 112 and 124 call `console.error` → a burst of failed logins writes free-text lines that the log pipeline cannot count or alert on by `reason`. Login behavior itself is correct.
**Confidence:** High
**Fix:** Use the structured logger:
```typescript
logger.warn('Authentication failed', {
  email: emailMasked,
  reason: 'invalid_credentials',
  ip: req.ip,
  timestamp: new Date().toISOString()
});
```

---

## Needs human verification

### Concurrency — Warning

**Location:** `src/services/auth.service.ts:131-133`
**Issue:** Failed attempts are counted with a read-modify-write (`user.failedAttempts + 1`) instead of an atomic increment.
**Evidence:** Six wrong-password requests for the same account arrive at the same time while `failedAttempts = 0`; all six read 0 before any update runs, and all six write 1 → after six failures the stored count is 1, so the lockout, which engages when the stored count reaches 5, does not engage. This assumes the lockout is decided only by the stored `failedAttempts` count. Verification checked the login route and `src/middleware/` and found no per-user lock, but the gateway configuration is not in the repository. Check whether the gateway serializes requests per user.
**Confidence:** Medium
**Fix:** Use an atomic update: `db.users.update({ where: { id }, data: { failedAttempts: { increment: 1 } } })`.

---

## Pre-existing issues (not counted)

- src/app.ts:5 — the `/health` handler opens a new database connection on every request and never closes it; this branch does not change it.

---

## Already raised in the PR (not repeated)

- src/routes/auth.routes.ts:8 — `POST /auth/login` has no rate limit, so a password can be guessed without limit (https://github.com/acme/shop-api/pull/123#discussion_r1201)

---

## Summary

| Category | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security | 1 | 1 | 0 | |
| Performance | 0 | 0 | 1 | |
| Tests/Coverage | 0 | 0 | 1 | |
| Architecture | 0 | 0 | 1 | |
| Code & File Size | 0 | 0 | 1 | |
| Potential Bugs | 1 | 0 | 0 | |
| Accessibility | 0 | 0 | 0 | ✓ |
| Observability | 0 | 0 | 1 | |
| API Design | 0 | 0 | 0 | |
| Resilience | 0 | 0 | 0 | ✓ |
| DB Migrations | 0 | 0 | 0 | ✓ |
| Concurrency | 0 | 0 | 0 | |
| i18n | 0 | 0 | 0 | ✓ |
| Privacy/Compliance | 0 | 0 | 0 | ✓ |
| Architecture Patterns | 0 | 0 | 0 | |
| Stack-Specific | 0 | 0 | 0 | |
| **Total** | **2** | **1** | **5** | |

**Verification:** 5 Critical/Warning candidates checked, 1 refuted.

**Review effort:** 5/5 — 501 to 1000 changed lines in 6 files; authentication and concurrency.
**Relevant tests:** changed — `tests/auth.test.ts` covers login and token generation; no test covers token refresh. Execution: not run.
**Look first:** `src/services/auth.service.ts` (the JWT secret fallback and the refresh-token race, both Critical), `src/controllers/auth.controller.ts` (login answers reveal which emails are registered), `src/middleware/auth.middleware.ts` (every protected route depends on it).
**Ready to merge:** No — 2 Critical findings must be fixed before merging. Not fully reviewed: see the Audit.

The Medium-confidence finding under Needs human verification is not counted in the table. The refuted candidate is not listed. The pre-existing note is not a finding and is not counted either. Neither is the already-raised line, which the open review thread already covers.

## Audit

**Files reviewed:** 6 of 6 changed files: `src/app.ts`, `src/controllers/auth.controller.ts`, `src/middleware/auth.middleware.ts`, `src/routes/auth.routes.ts`, `src/services/auth.service.ts`, `tests/auth.test.ts`.
**Read for context:** `AGENTS.md`, `package.json`, `skill:references/api-design.md`, `skill:references/concurrency.md`, `skill:references/intent.md`, `skill:references/large-diffs.md`, `skill:references/observability.md`, `skill:stacks/node.md`, `skill:stacks/typescript.md`, `src/controllers/user.controller.ts`, `src/lib/logger.ts`, `src/services/AGENTS.md`.
**Checked with no findings:** API Design, Architecture Patterns, Stack-Specific.
**Already raised, not verified:** `src/routes/auth.routes.ts:8` (Security).
**Not verified:**
- `jsonwebtoken` version-specific migration recommendations — API not validated, not material: no documentation tool was available and the official documentation for the installed version could not be read; no migration finding is made, and no changed behavior or contract relies on those recommendations.
- gateway configuration — context not read, material: it is not in the repository, and whether the changed failed-attempt count can lose an increment depends on whether the gateway serializes requests per user.

---

The report ends with the Audit above. The action items below are not part of it: they are one way a team can track the findings.

## Action Items

### Must Fix Before Merge
1. ✅ Remove the hard-coded JWT secret fallback (Critical - Security)
2. ✅ Rotate refresh tokens in one transaction (Critical - Potential Bugs)

### Should Fix Soon After
3. ⏳ Use one error message for unknown email and wrong password (Warning - Security)

### Optional Improvements
4. 💡 Select only the needed fields when loading the user
5. 💡 Assert the real token claims and expiry in tests
6. 💡 Split the auth middleware into smaller functions
7. 💡 Split the auth controller into smaller files
8. 💡 Replace console.error with structured logging (rule in src/services/AGENTS.md)

### Ask a Human
9. 🔍 Check whether failed-login counting can run in parallel for one account

---

## Compact Mode

The same review when the user asks for `/code-review pr 123 compact`:

**Scope:** pr 123 (gh pr diff 123)

**Intent:** Add registration, login, token refresh and logout with JWT to the API (title, description, #98).
**Requirements:** 2 met, 1 not met, 1 not judged.
- Met — login returns an access token and a refresh token for valid credentials (#98): `src/controllers/auth.controller.ts:15-40` returns both tokens from `POST /auth/login`.
- Met — logout revokes the refresh token (#98): `src/controllers/auth.controller.ts:96-110` deletes the stored refresh token.
- Not met — a refresh token works only once (#98): the Critical finding at `src/services/auth.service.ts:89-97` lets two concurrent requests use the same refresh token.
- Not judged — five failed logins in a row lock the account (#98): `src/services/auth.service.ts:131-133` counts the failures, but whether parallel attempts lose a count depends on the gateway configuration, which is not in the repository.
**Scope creep:** compared only with the description and #98: `src/controllers/auth.controller.ts:300-487` (password reset and email verification, which neither asks for).
**Sources not read:** SEC-42 (no read-only tool for its tracker).

- src/services/auth.service.ts:45-46: Critical: the JWT secret falls back to 'dev-secret', so anyone can forge tokens → fail at startup when JWT_SECRET is unset
- src/services/auth.service.ts:89-97: Critical: two concurrent refreshes with one token both get a new valid token → rotate the token in one transaction
- src/controllers/auth.controller.ts:23-27: Warning: different login errors reveal which emails are registered → return one message for both cases
- src/services/auth.service.ts:67-69: Suggestion: token generation loads every user column, including the password hash → select only id and email
- tests/auth.test.ts:34-41: Suggestion: the test mocks jwt.sign and never checks claims or expiry → verify the real token
- src/middleware/auth.middleware.ts:18-74: Suggestion: the 57-line middleware mixes extraction, verification and lookup → extract helpers
- src/controllers/auth.controller.ts:1-487: Suggestion: one 487-line controller handles six flows → split it into one controller per flow
- src/services/auth.service.ts:112: Suggestion: auth failures go to console.error, which the services rules forbid → use the structured logger (also at src/services/auth.service.ts:124) (Rule: src/services/AGENTS.md:L4-L5)

## Needs human verification

- src/services/auth.service.ts:131-133: Warning: six parallel wrong-password requests all read 0 and store 1, so a lockout at a stored count of 5 never engages → use an atomic increment

## Pre-existing issues (not counted)

- src/app.ts:5 — the `/health` handler opens a new database connection on every request and never closes it; this branch does not change it.

## Already raised in the PR (not repeated)

- src/routes/auth.routes.ts:8 — `POST /auth/login` has no rate limit, so a password can be guessed without limit (https://github.com/acme/shop-api/pull/123#discussion_r1201)

**Verification:** 5 Critical/Warning candidates checked, 1 refuted.

**Review effort:** 5/5 — 501 to 1000 changed lines in 6 files; authentication and concurrency.
**Relevant tests:** changed — `tests/auth.test.ts` covers login and token generation; no test covers token refresh. Execution: not run.
**Look first:** `src/services/auth.service.ts` (the JWT secret fallback and the refresh-token race, both Critical), `src/controllers/auth.controller.ts` (login answers reveal which emails are registered), `src/middleware/auth.middleware.ts` (every protected route depends on it).
**Ready to merge:** No — 2 Critical findings must be fixed before merging. Not fully reviewed: see the Audit.
**Audit:** 6 of 6 changed files reviewed; 12 files read for context; no findings in API Design, Architecture Patterns, Stack-Specific; already raised, not verified: 1 Warning candidate; not verified: `jsonwebtoken` version-specific migration recommendations (API not validated, not material), gateway configuration (context not read, material).

---

## Coverage Limits

The verdict and the Audit never claim more than the review covered, and a limit is never reported as a bug. In another `branch` review, the diff output for the rewritten `src/legacy/report.ts` was cut off at line 1200 of that file, and no documentation tool was available to check the new `date-fns` call. The review found no Critical or Warning finding in what it read, but the change is not ready to merge until a person reviews what it could not:

```markdown
**Review effort:** 5/5 — more than 1000 changed lines in 4 files; no risk area.
**Relevant tests:** not verified — `tests/report.test.ts` calls `buildLegacyTotals`, which is in the lines that were not read, so whether it runs the changed code could not be checked. Execution: not run.
**Look first:** `src/legacy/report.ts` (lines 1201-2310 were not read), `src/report/format.ts` (its new period labels depend on an API that was not validated).
**Ready to merge:** No — not fully reviewed (not read): `src/legacy/report.ts` lines 1201-2310. 1 more material limit is in the Audit.
```

Its Audit marks each limit `material` or `not material`, and says why:

```markdown
## Audit

**Files reviewed:** 3 of 4 changed files: `src/legacy/report.ts`, `src/report/format.ts`, `tests/report.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/large-diffs.md`, `skill:stacks/typescript.md`, `src/report/index.ts`.
**Checked with no findings:** Security, Performance, Architecture, Potential Bugs.
**Not verified:**
- `src/legacy/report.ts` lines 1201-2310 — not read, material: the diff output was cut off at line 1200 of this file.
- `format` from `date-fns` in `src/report/format.ts` — API not validated, material: no documentation tool was available and the official documentation could not be read, and the period labels that `formatPeriod` returns depend on how the installed version reads the `YYYY` token.
- `assets/report-logo.png` — binary, not material: a changed image that no changed code reads.
- relevant tests — tests not verified, not material: `tests/report.test.ts` calls `buildLegacyTotals`, which is in the lines that were not read and is already a material limit; the findings about the code that was read were judged from the code, not from the tests.
```

---

## Repository Configuration

The same kind of review in another repository, which has this `.code-review/config.yml`:

```yaml
ignore_paths:
  - "src/generated/**"
min_severity: Warning
disabled_categories:
  - Accessibility
```

and one rule, saved as `.code-review/rules/validate-request-bodies.md`:

````markdown
---
paths:
  - "src/api/**/*.ts"
severity: Warning
---

Every API handler parses its request body with the zod schema of the route
before it reads any field of `req.body`.

## Bad

```ts
export async function createUser(req: Request) {
  const email = req.body.email;
}
```

## Good

```ts
export async function createUser(req: Request) {
  const { email } = CreateUserBody.parse(req.body);
}
```
````

The pull request changes `src/api/users.ts`, `src/components/SignupForm.vue` and the generated `src/generated/api-client.ts`. Right after its Scope line, the report says what the configuration did:

```markdown
**Configuration:** `.code-review/config.yml` and 1 rule file from `.code-review/rules/`.
**Excluded by configuration:** 1 changed file matches ignore_paths and was not reviewed: `src/generated/api-client.ts`.
```

A finding that breaks the rule cites it. In compact mode:

```markdown
- src/api/users.ts:12: Warning: the handler reads `req.body.email` before the body is parsed, so a request without an email stores a user whose email is `undefined` → parse the body with `CreateUserBody` first (Rule: .code-review/rules/validate-request-bodies.md:L7-L8)
```

Right after the verification line, the report counts what the filters left out: two Suggestions below `min_severity` and one Accessibility Warning on the signup form. A Critical finding would have been shown in any category.

```markdown
**Omitted by configuration:** min_severity Warning: 2 omitted; disabled categories Accessibility: 1 omitted.
```

---

## Publishing Dry Run

The same review when the user asks for `/code-review pr 123 --comment --dry-run`: after the report, the skill prints what `--comment` would post and posts nothing. The pull request has no summary comment from an earlier run, so the summary comment would be created. The review payload below shows one of its 8 inline comments. The summary comment ends with the triage lines and the one-line audit; no inline comment carries them. With `--comment` the skill also read the publishing guide, so this run's **Read for context** line adds `skill:references/publishing.md` after `skill:references/observability.md`, and its audit counts 13 files read for context.

## Dry run — nothing was published

### 1. Review with 8 inline comments

```sh
gh api --hostname github.com --method POST repos/acme/shop-api/pulls/123/reviews -H 'Content-Type: application/json' --input review.json
```

```json
{
  "commit_id": "9c1e4b7a2f3d5e6c8b0a1d2e3f4a5b6c7d8e9f01",
  "event": "COMMENT",
  "body": "Inline comments from code-review-skill: 8. The summary comment lists every finding.",
  "comments": [
    {
      "path": "src/controllers/auth.controller.ts",
      "start_line": 23,
      "start_side": "RIGHT",
      "line": 27,
      "side": "RIGHT",
      "body": "**Warning — Security** · `src/controllers/auth.controller.ts:23-27`\n\n**Issue:** Login answers \"User not found\" for an unknown email and \"Invalid credentials\" for a wrong password.\n**Evidence:** `POST /auth/login` with `alice@example.com` and a wrong password answers \"Invalid credentials\" when that account exists and \"User not found\" when it does not → an attacker can find out which emails are registered.\n**Fix:** Return the same message for both cases: \"Invalid email or password\".\n\n<!-- code-review-skill:finding -->"
    }
  ]
}
```

### 2. Summary comment (create)

```sh
gh api --hostname github.com --method POST repos/acme/shop-api/issues/123/comments -H 'Content-Type: application/json' --input summary.json
```

```json
{
  "body": "<!-- code-review-skill:summary -->\n## Code review\n\n**Scope:** pr 123 (gh pr diff 123) at `9c1e4b7`\n**Findings:** 2 Critical, 1 Warning, 5 Suggestion. Inline comments: 8.\n\n- src/services/auth.service.ts:45-46: Critical: the JWT secret falls back to `[REDACTED]`, so anyone can forge tokens → fail at startup when JWT_SECRET is unset (inline)\n- src/services/auth.service.ts:89-97: Critical: two concurrent refreshes with one token both get a new valid token → rotate the token in one transaction (inline)\n- src/controllers/auth.controller.ts:23-27: Warning: different login errors reveal which emails are registered → return one message for both cases (inline)\n- src/services/auth.service.ts:67-69: Suggestion: token generation loads every user column, including the password hash → select only id and email (inline)\n- tests/auth.test.ts:34-41: Suggestion: the test mocks jwt.sign and never checks claims or expiry → verify the real token (inline)\n- src/middleware/auth.middleware.ts:18-74: Suggestion: the 57-line middleware mixes extraction, verification and lookup → extract helpers (inline)\n- src/controllers/auth.controller.ts:1-487: Suggestion: one 487-line controller handles six flows → split it into one controller per flow (inline)\n- src/services/auth.service.ts:112: Suggestion: auth failures go to console.error, which the services rules forbid → use the structured logger (also at src/services/auth.service.ts:124) (Rule: src/services/AGENTS.md:L4-L5) (inline)\n\n**Needs human verification**\n\n- src/services/auth.service.ts:131-133: Warning: six parallel wrong-password requests all read 0 and store 1, so a lockout at a stored count of 5 never engages → use an atomic increment\n\n**Verification:** 5 Critical/Warning candidates checked, 1 refuted.\n\n**Review effort:** 5/5 — 501 to 1000 changed lines in 6 files; authentication and concurrency.\n**Relevant tests:** changed — `tests/auth.test.ts` covers login and token generation; no test covers token refresh. Execution: not run.\n**Look first:** `src/services/auth.service.ts` (the JWT secret fallback and the refresh-token race, both Critical), `src/controllers/auth.controller.ts` (login answers reveal which emails are registered), `src/middleware/auth.middleware.ts` (every protected route depends on it).\n**Ready to merge:** No — 2 Critical findings must be fixed before merging. Not fully reviewed: see the Audit.\n**Audit:** 6 of 6 changed files reviewed; 13 files read for context; no findings in API Design, Architecture Patterns, Stack-Specific; already raised, not verified: 1 Warning candidate; not verified: `jsonwebtoken` version-specific migration recommendations (API not validated, not material), gateway configuration (context not read, material)."
}
```

---

*Generated by Code Review Skill v2.0.0*
