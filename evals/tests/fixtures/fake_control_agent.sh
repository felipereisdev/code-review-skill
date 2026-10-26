#!/usr/bin/env bash
# Test double for behavior controls: answers from the arguments in the prompt.
prompt=$(cat)
case "$prompt" in
  *"--fix"*)
    cat <<'EOF'
### Security — Critical

**File:** `app.py:2`
**Issue:** SQL injection through string concatenation.
**Fix:** Use a parameterized query.

## Summary

**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `app.py`.

## Fix proposal

1. `app.py:2` Critical — Security: bind the name as a parameter.

Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.
EOF
    ;;
  *"--second-opinion"*)
    cat <<'EOF'
### Security — Critical

**File:** `app.py:2`
**Issue:** SQL injection through string concatenation.
**Fix:** Use a parameterized query.

## Summary

**Second opinion:** codex unavailable: the call was refused.

**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `app.py`.
EOF
    ;;
esac
