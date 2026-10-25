## Dry run — nothing was published

### 1. Review with 3 inline comments

```sh
gh api --hostname github.com --method POST repos/acme/billing-api/pulls/42/reviews -H 'Content-Type: application/json' --input review.json
```

```json
{
  "commit_id": "3f1c2a9b8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a",
  "event": "COMMENT",
  "body": "Inline comments from code-review-skill: 3. The summary comment lists every finding.",
  "comments": [
    {
      "path": "src/invoices.js",
      "start_line": 9,
      "start_side": "RIGHT",
      "line": 10,
      "side": "RIGHT",
      "body": "**Critical — Potential Bugs** · `src/invoices.js:9-10`\n\n**Issue:** The loop runs while `i <= invoice.lines.length`, one step past the last line.\n**Evidence:** An invoice with 2 lines reaches `i = 2` → `invoice.lines[2]` is `undefined`, reading `.amount` throws a `TypeError`, and every invoice total fails.\n**Fix:** Stop at the last line:\n\n```suggestion\n  for (let i = 0; i < invoice.lines.length; i++) {\n    total += invoice.lines[i].amount;\n```\n\n<!-- code-review-skill:finding -->"
    },
    {
      "path": "src/auth.js",
      "line": 3,
      "side": "LEFT",
      "body": "**Critical — Security** · `src/auth.js:3`\n\n**Issue:** The change removes the admin role check from `requireAdmin`.\n**Evidence:** The removed line 3 answered 403 to a user whose role is not `admin`; without it, any logged-in user who calls an admin route reaches `next()` → non-admins can run admin actions.\n**Fix:** Restore the role check before `next()`.\n\n<!-- code-review-skill:finding -->"
    },
    {
      "path": "src/invoices.js",
      "start_line": 15,
      "start_side": "RIGHT",
      "line": 17,
      "side": "RIGHT",
      "body": "**Suggestion — Tests/Coverage** · `src/invoices.js:15-17`\n\n**Issue:** `applyDiscount` has no test.\n**Evidence:** A change that applied the percent twice would still pass the suite → wrong discounts could ship unnoticed. The function is correct today.\n**Fix:** Add a test for it:\n\n```js\ntest(\"applyDiscount\", () => { ... });\n```\n\n<!-- code-review-skill:finding -->"
    }
  ]
}
```

### 2. Summary comment (edit 9001)

```sh
gh api --hostname github.com --method PATCH repos/acme/billing-api/issues/comments/9001 -H 'Content-Type: application/json' --input summary.json
```

```json
{
  "body": "<!-- code-review-skill:summary -->\n## Code review\n\n**Scope:** pr 42 (gh pr diff 42) at `3f1c2a9`\n**Findings:** 3 Critical, 0 Warning, 1 Suggestion. Inline comments: 3.\n\n- src/config.js:3: Critical: the payments API key `[REDACTED]` is committed in the source → read the key from the environment (already commented)\n- src/invoices.js:9-10: Critical: the loop runs one step past the last line → stop at the last line (inline)\n- src/auth.js:3: Critical: the change removes the admin role check from requireAdmin → restore the role check (inline)\n- src/invoices.js:15-17: Suggestion: applyDiscount has no test → add a test for it (inline)\n\n**Needs human verification**\n\n- src/invoices.js:16: Warning: applyDiscount accepts a percent above 100 → reject percents outside 0-100\n\n**Verification:** 4 Critical/Warning candidates checked, 0 refuted."
}
```
