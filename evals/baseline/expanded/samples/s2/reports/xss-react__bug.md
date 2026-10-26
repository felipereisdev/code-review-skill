**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: render each comment's body under its author, keeping line breaks (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The test now asserts the comment body as well as the author (`src/components/CommentList.test.tsx:6-9`), so the new rendering has some coverage.
- The list keeps the stable `key={comment.id}`.

## Findings

### Security — Critical

**Location:** `src/components/CommentList.tsx:9`
**Issue:** The comment body is injected as raw HTML through `dangerouslySetInnerHTML`. The only transformation is replacing `\n` with `<br>`, so nothing escapes or sanitizes the text.
**Evidence:** A comment is user-written text (`Comment.body: string`). If one has the body `<img src=x onerror=alert(document.cookie)>`, the `.replace` leaves it unchanged and React writes it into the `<p>` as markup. The handler runs in every reader's browser, which is stored XSS (session theft, actions as the reader). Verification checked the only caller-facing contract, the `Comment` type, and the repository. It has no sanitizer such as DOMPurify and no other caller of `CommentList` that escapes `body`. React's JSX-escaping precedent does not cover `dangerouslySetInnerHTML`.
**Confidence:** High
**Fix:** Render the body as text. For example, use `<p style={{ whiteSpace: 'pre-line' }}>{comment.body}</p>`. Or split on `\n` and interleave `<br />` elements: `comment.body.split('\n').map((line, i) => <Fragment key={i}>{i > 0 && <br />}{line}</Fragment>)`. If HTML from users is really required, sanitize it with an allow-list sanitizer first.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
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
| **Total**             | **1**    | **0**   | **0**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/components/CommentList.test.tsx` now asserts that the author and the body text `Hello` render. It does not cover newline conversion or markup or HTML in the body, so it would not catch the XSS above. Execution: not run.
**Look first:** `src/components/CommentList.tsx` (Critical stored XSS at line 9), `src/components/CommentList.test.tsx` (add a test with an HTML body and a multi-line body).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/CommentList.test.tsx`, `src/components/CommentList.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`.
**Checked with no findings:** Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:** nothing.
