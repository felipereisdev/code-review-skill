# Code Review: staged changes

**Scope:** `git diff --cached` (2 files: `src/components/CommentList.tsx` and `src/components/CommentList.test.tsx`)
**Stack detected:** React 18, TypeScript, Vitest and Testing Library. I loaded the React and TypeScript checklists. No architecture pattern files apply.

## What Was Done Well
- The change is small and focused. It renders `comment.body` as a React text child, so React escapes it and there is no XSS risk. There is no `dangerouslySetInnerHTML`.
- `white-space: pre-line` keeps line breaks in multi-line comments without parsing the text as HTML or markdown.
- The existing stable `key={comment.id}` is kept, and the test was updated in the same change to assert the new body output.

## Findings

### Tests/Coverage — Suggestion

**File:** `src/components/CommentList.test.tsx:9`
**Issue:** The test checks only a single-line body. The reason for the change is to preserve line breaks (`pre-line`), and nothing covers that. Nothing covers an empty `comments` array or an empty `body` either. The `toBeTruthy()` assertions would also pass for any non-null element, so they are weaker than needed.
**Fix:** Add a case with a multi-line body, for example `'a\nb'`. Assert the text content, or the `white-space` style on the element. Add a case for an empty list. If `@testing-library/jest-dom` is available, use `toBeInTheDocument()`.

### Stack-Specific (React) — Suggestion

**File:** `src/components/CommentList.tsx:9`
**Issue:** The inline `style={{ whiteSpace: 'pre-line' }}` creates a new object on every render for each list item. The cost is negligible. It does mix styling into markup, and the project has no established styling convention yet that this follows.
**Fix:** Optional. Hoist the style to a module-level constant such as `const bodyStyle = { whiteSpace: 'pre-line' } as const`, or use a CSS class if the project adopts one. This does not block the merge.

## Other categories
- **Potential bugs:** No problems found. `body` is typed `string`. If an API ever returned `null`, `{comment.body}` would render nothing and not throw. The `Comment` type already requires `body`, so no callers break.
- **Security, Accessibility, Observability:** No problems found. `<p>` is the right semantic element for the body, and nothing sensitive is logged.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 0          |     |
| Observability         | 0        | 0       | 0          |     |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 1          |     |
| **Total**             | **0**    | **0**   | **2**      |     |

**Verdict:** There are no blockers, and the change is safe to merge. The two suggestions are optional.
