# Code Review — Staged changes (`git diff --cached`)

**Stack:** React 18 + TypeScript + Vitest. No other stack or pattern files apply.
**Files:** `src/components/CommentList.tsx`, `src/components/CommentList.test.tsx`

## What Was Done Well
- The test was extended in the same change that adds the new rendering, so the body is now asserted.
- The component is small, and its `key={comment.id}` is stable and not an array index.
- The `Comment` type is explicit.

## Findings

### Security — Critical

**File:** `src/components/CommentList.tsx:9`
**Issue:** `dangerouslySetInnerHTML` renders `comment.body` unescaped. `comment.body` is user-generated content, and the `.replace(/\n/g, '<br>')` call only swaps newlines. It does not sanitize anything. A comment like `<img src=x onerror=...>` gives stored XSS for every viewer of the list, which allows session or token theft and actions taken as the viewer. React escapes text by default, and this change bypasses that protection.
**Fix:** Render the body as text and keep the line breaks with CSS:
```tsx
<p style={{ whiteSpace: 'pre-line' }}>{comment.body}</p>
```
Use a CSS class instead of the inline style if the project has a convention for that. If HTML must be supported, sanitize with DOMPurify, using a strict allowlist, before injecting it. Sanitize on the server too.

### Tests/Coverage — Warning

**File:** `src/components/CommentList.test.tsx:6-10`
**Issue:** There is no test for a body containing HTML or script markup, so the XSS above would not be caught. There is also no test for multi-line bodies, which is the purpose of the `\n` → `<br>` conversion. Empty lists and an empty body are not covered either.
**Fix:** Add a regression test that renders `body: '<img src=x onerror=alert(1)>'` and asserts that no `img` element is created and the markup shows as literal text. Add a test for `'a\nb'` that checks both lines render with a line break between them.

### Potential Bugs — Warning

**File:** `src/components/CommentList.tsx:9`
**Issue:** `comment.body.replace(...)` throws a `TypeError` if `body` is `null` or `undefined`. The `Comment` type says `string`, but API data is not validated at runtime. One bad record would crash the whole list, because there is no error boundary.
**Fix:** Rendering `{comment.body}` as text, as suggested above, removes the `.replace()` call and the crash risk. Validate API data at the boundary, for example with Zod. This follows from the TypeScript runtime-validation guideline.

### Accessibility — Suggestion

**File:** `src/components/CommentList.tsx:8-9`
**Issue:** The author and body sit in sibling elements with no semantic link between them. This is minor and works acceptably as it is.
**Fix:** Optionally mark each comment up as an `<article>` or use a description list. This is not required.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 1       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
| Accessibility         | 0        | 0       | 1          |     |
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **2**   | **1**      |     |

**Verdict:** Do not merge until the stored-XSS issue is fixed.
