# Java / Spring Boot — Code Review Checklist

- **Bean lifecycle**: beans are stateless where possible; stateful beans scoped correctly (`@RequestScope`, `@SessionScope`)
- **Transaction boundaries**: `@Transactional` applied at the service layer, not the repository layer; read-only transactions use `readOnly = true`
- **Lazy vs eager fetch**: JPA fetch types explicit; no unintended lazy loading in detached contexts causing `LazyInitializationException`
- **Exception handling**: `@ControllerAdvice` / `@ExceptionHandler` used for global error handling; exceptions not leaked to the client
- **Dependency injection**: constructor injection used; field injection (`@Autowired` on fields) avoided
- **DTO vs Entity**: entities not exposed directly in API responses; DTOs used for request/response mapping

## Precedents

- **Spring Data, JPA and `JdbcTemplate` bind parameters**: derived query methods, `@Query` with named (`:name`) or positional (`?1`) parameters, the Criteria API, and `JdbcTemplate` with `?` arguments send values as bound parameters. Do not report SQL injection for them. **Exception:** JPQL or SQL built by string concatenation or `String.format` and passed to `createQuery`, `createNativeQuery` or `JdbcTemplate`.
- **Spring Security checks CSRF on covered unsafe requests**: a request covered by the selected `SecurityFilterChain` with its `CsrfFilter` enabled is rejected without a valid token when its CSRF matcher requires protection; the default matcher excludes `GET`, `HEAD`, `TRACE` and `OPTIONS`. Do not report missing server-side CSRF validation on an unsafe-method form post after verifying that this active filter and matcher cover it. **Exception:** routes outside every `SecurityFilterChain` (for example outside the chain's `securityMatcher`) or excluded from Spring Security entirely, a selected chain with CSRF disabled (`csrf(csrf -> csrf.disable())` or `csrf().disable()`), requests excluded by `ignoringRequestMatchers` or a custom `requireCsrfProtectionMatcher`, state changes on methods the matcher does not protect, and forms that fail with a 403 because they do not submit a valid token.
- **Thymeleaf `th:text` escapes**: in HTML template mode, `th:text` and `[[...]]` inlining escape HTML, which makes values safe in HTML text; inside a block marked `th:inline="javascript"`, `[[...]]` is instead serialized as an escaped JavaScript value. Do not report XSS for values rendered that way. **Exception:** `th:utext` and `[(...)]` inlining, which do not escape in any mode, `[[...]]` inside a `<script>` block or event-handler attribute without `th:inline="javascript"`, where HTML escaping does not protect JavaScript, and user-controlled URLs in `th:href`, `th:src` or `th:action`, where escaping does not stop a `javascript:` URL.
