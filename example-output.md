# Example Output

This is an example of the code review output format. The actual review will vary based on your codebase and the changes being reviewed.

## Scenario

Reviewing a feature branch that adds user authentication with JWT to a Node.js/Express API.

---

## Code Review Report

### What Was Done Well

- Clean separation between auth controller and service layers
- Proper use of async/await patterns
- Good error handling structure with custom error classes
- Tests cover both happy path and error scenarios

---

## Findings

### Security — Critical

**File:** `src/services/auth.service.ts:45`
**Issue:** JWT secret is read from `process.env.JWT_SECRET` without validation. If undefined, the app will use `undefined` as the secret.
**Fix:** Add validation at startup:
```typescript
if (!process.env.JWT_SECRET) {
  throw new Error('JWT_SECRET environment variable is required');
}
```

### Security — Warning

**File:** `src/controllers/auth.controller.ts:23`
**Issue:** Error message exposes whether email exists ("User not found" vs "Invalid credentials"), enabling user enumeration attacks.
**Fix:** Use generic error message for both cases: "Invalid email or password"

### Performance — Suggestion

**File:** `src/services/auth.service.ts:67`
**Issue:** Database query fetches all user fields including password hash when only `id` and `email` are needed for JWT generation.
**Fix:** Use `select` to limit fields:
```typescript
const user = await db.users.findFirst({
  where: { email },
  select: { id: true, email: true, password: true }
});
```

### Tests — Warning

**File:** `tests/auth.test.ts:34`
**Issue:** Test mocks JWT signing but doesn't verify the actual token structure or expiration.
**Fix:** Add assertions to verify token contains expected claims:
```typescript
const decoded = jwt.verify(token, process.env.JWT_SECRET!);
expect(decoded).toHaveProperty('userId');
expect(decoded).toHaveProperty('exp');
```

### Architecture — Suggestion

**File:** `src/middleware/auth.middleware.ts:18`
**Issue:** Middleware function exceeds 50 lines and handles multiple responsibilities (token extraction, verification, and user lookup).
**Fix:** Extract token extraction and user lookup into separate functions:
```typescript
const extractToken = (authHeader: string): string | null => { ... }
const getUserFromToken = (token: string): Promise<User | null> => { ... }
```

### Potential Bugs — Critical

**File:** `src/services/auth.service.ts:89`
**Issue:** Race condition in token refresh - concurrent requests could generate multiple valid refresh tokens for the same user.
**Fix:** Use database transaction or atomic operation:
```typescript
await db.$transaction(async (tx) => {
  await tx.refreshTokens.deleteMany({ where: { userId } });
  await tx.refreshTokens.create({ data: { token: newToken, userId } });
});
```

### Code & File Size — Warning

**File:** `src/controllers/auth.controller.ts`
**Issue:** File is 487 lines and contains controller logic for login, register, logout, refresh token, password reset, and email verification.
**Fix:** Split into separate controllers: `login.controller.ts`, `register.controller.ts`, etc.

### Observability — Suggestion

**File:** `src/services/auth.service.ts:112`
**Issue:** Authentication failures are logged with `console.error` instead of structured logging, making it hard to aggregate and alert on security events.
**Fix:** Use structured logger:
```typescript
logger.warn('Authentication failed', {
  email: emailMasked,
  reason: 'invalid_credentials',
  ip: req.ip,
  timestamp: new Date().toISOString()
});
```

---

## Summary

| Category | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security | 1 | 1 | 0 | |
| Performance | 0 | 0 | 1 | |
| Tests/Coverage | 0 | 1 | 0 | |
| Architecture | 0 | 0 | 1 | |
| Code & File Size | 0 | 1 | 0 | |
| Potential Bugs | 1 | 0 | 0 | |
| Accessibility | 0 | 0 | 0 | ✓ |
| Observability | 0 | 0 | 1 | |
| API Design | 0 | 0 | 0 | |
| Resilience | 0 | 0 | 0 | ✓ |
| DB Migrations | 0 | 0 | 0 | ✓ |
| Concurrency | 0 | 0 | 0 | |
| i18n | 0 | 0 | 0 | ✓ |
| Privacy/Compliance | 0 | 0 | 0 | ✓ |
| Architecture Patterns | 0 | 0 | 0 | |
| Stack-Specific | 0 | 1 | 1 | |
| **Total** | **2** | **4** | **4** | |

---

## Action Items

### Must Fix Before Merge
1. ✅ Add JWT_SECRET environment variable validation (Critical - Security)
2. ✅ Fix race condition in token refresh (Critical - Potential Bugs)

### Should Fix Soon After
3. ⏳ Fix user enumeration vulnerability (Warning - Security)
4. ⏳ Add token structure verification in tests (Warning - Tests)
5. ⏳ Split auth controller into smaller files (Warning - Code & File Size)

### Optional Improvements
6. 💡 Optimize database query to select only needed fields
7. 💡 Refactor middleware into smaller functions
8. 💡 Replace console.error with structured logging

---

## Stack-Specific Notes

### Node.js/Express
- Consider using `helmet` middleware for security headers
- Add rate limiting on auth endpoints using `express-rate-limit`
- Use `joi` or `zod` for input validation instead of manual checks

### JWT Best Practices
- Consider using RS256 (asymmetric) instead of HS256 for multi-service architectures
- Set reasonable token expiration (15 min for access, 7 days for refresh)
- Implement token blacklisting for logout functionality

---

*Generated by Code Review Skill v1.0.0*
