#!/usr/bin/env bash
# Test double for the eval runner: reports a Critical finding only when the staged diff plants BUG.
cat > /dev/null
if git diff --cached | grep -q 'BUG'; then
  cat <<'EOF'
### Security — Critical

**File:** `app.py:2`
**Issue:** SQL injection through string concatenation.
**Fix:** Use a parameterized query.

## Summary

**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `app.py`.
EOF
else
  cat <<'EOF'
## Findings

Code review passed — no issues found.

**Ready to merge:** Yes — no finding.

## Audit

**Files reviewed:** 1 of 1 changed files: `app.py`.
EOF
fi
