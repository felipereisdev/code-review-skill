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
EOF
else
  printf 'Code review passed — no issues found.\n'
fi
