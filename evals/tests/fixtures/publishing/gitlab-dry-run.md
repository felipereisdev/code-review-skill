## Dry run — nothing was published

### 1. Discussion on src/invoices.js:9-10

```sh
glab api --hostname gitlab.com --method POST projects/77/merge_requests/42/discussions -H 'Content-Type: application/json' --input discussion-1.json
```

```json
{
  "body": "**Critical — Potential Bugs** · `src/invoices.js:9-10`\n\n**Issue:** The loop runs while `i <= invoice.lines.length`, one step past the last line.\n**Evidence:** An invoice with 2 lines reaches `i = 2` → `invoice.lines[2]` is `undefined`, reading `.amount` throws a `TypeError`, and every invoice total fails.\n**Fix:** Stop at the last line:\n\n```suggestion:-1+0\n  for (let i = 0; i < invoice.lines.length; i++) {\n    total += invoice.lines[i].amount;\n```\n\n<!-- code-review-skill:finding -->",
  "position": {
    "position_type": "text",
    "base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    "start_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    "head_sha": "3f1c2a9b8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a",
    "old_path": "src/invoices.js",
    "new_path": "src/invoices.js",
    "new_line": 10
  }
}
```

### 2. Discussion on src/auth.js:3

```sh
glab api --hostname gitlab.com --method POST projects/77/merge_requests/42/discussions -H 'Content-Type: application/json' --input discussion-2.json
```

```json
{
  "body": "**Critical — Security** · `src/auth.js:3`\n\n**Issue:** The change removes the admin role check from `requireAdmin`.\n**Evidence:** The removed line 3 answered 403 to a user whose role is not `admin`; without it, any logged-in user who calls an admin route reaches `next()` → non-admins can run admin actions.\n**Fix:** Restore the role check before `next()`.\n\n<!-- code-review-skill:finding -->",
  "position": {
    "position_type": "text",
    "base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    "start_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    "head_sha": "3f1c2a9b8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a",
    "old_path": "src/auth.js",
    "new_path": "src/auth.js",
    "old_line": 3
  }
}
```

### 3. Discussion on src/invoices.js:15-17

```sh
glab api --hostname gitlab.com --method POST projects/77/merge_requests/42/discussions -H 'Content-Type: application/json' --input discussion-3.json
```

```json
{
  "body": "**Suggestion — Tests/Coverage** · `src/invoices.js:15-17`\n\n**Issue:** `applyDiscount` has no test.\n**Evidence:** A change that applied the percent twice would still pass the suite → wrong discounts could ship unnoticed. The function is correct today.\n**Fix:** Add a test for it:\n\n```js\ntest(\"applyDiscount\", () => { ... });\n```\n\n<!-- code-review-skill:finding -->",
  "position": {
    "position_type": "text",
    "base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    "start_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    "head_sha": "3f1c2a9b8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a",
    "old_path": "src/invoices.js",
    "new_path": "src/invoices.js",
    "new_line": 17
  }
}
```

### 4. Summary comment (edit 502)

```sh
glab api --hostname gitlab.com --method PUT projects/77/merge_requests/42/notes/502 -H 'Content-Type: application/json' --input summary.json
```

```json
{
  "body": "<!-- code-review-skill:summary -->\n## Code review\n\n**Scope:** pr 42 (glab mr diff 42) at `3f1c2a9`\n**Findings:** 3 Critical, 0 Warning, 1 Suggestion. Inline comments: 3.\n\n- src/config.js:3: Critical: the payments API key `[REDACTED]` is committed in the source → read the key from the environment (already commented)\n- src/invoices.js:9-10: Critical: the loop runs one step past the last line → stop at the last line (inline)\n- src/auth.js:3: Critical: the change removes the admin role check from requireAdmin → restore the role check (inline)\n- src/invoices.js:15-17: Suggestion: applyDiscount has no test → add a test for it (inline)\n\n**Needs human verification**\n\n- src/invoices.js:16: Warning: applyDiscount accepts a percent above 100 → reject percents outside 0-100\n\n**Verification:** 4 Critical/Warning candidates checked, 0 refuted."
}
```
