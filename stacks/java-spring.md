# Java / Spring Boot — Code Review Checklist

> This file applies only to packages whose build file declares Spring Boot, as SKILL.md Step 1 says; plain Java code gets none of these items. Check sibling classes for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that the compiler or an analyzer configured in the repository, such as Error Prone or SpotBugs, already reports is not a finding. An item that depends on a version names the Spring Boot, Spring Framework, Spring Security, Hibernate or JDK version that it needs; read it from the build file.

## Transactions and Proxies

- **Self-invocation**: in the default proxy mode, `@Transactional`, `@Async`, `@Cacheable` and method-security annotations such as `@PreAuthorize` apply only to calls that come in through the bean's proxy. A call from another method of the same bean (`this.place(order)` or plain `place(order)`) runs with no transaction, synchronously, uncached or without the authorization check. `@Transactional` never applies to `private` methods; since Spring Framework 6.0 it also applies to `protected` and package-visible methods of class-based proxies, and before 6.0 only to `public` ones.
- **Rollback rules**: by default a transaction rolls back only for unchecked exceptions (`RuntimeException` and `Error`). A checked exception that leaves a `@Transactional` method commits the work done so far unless `rollbackFor` names it, and an exception that the method catches and does not rethrow commits as well.
- **Rollback-only transactions**: when an inner `@Transactional` method that joins the caller's transaction (the default `REQUIRED` propagation) throws, the shared transaction is marked rollback-only. An outer method that catches the exception and returns normally then gets `UnexpectedRollbackException` at commit.
- **Side effects before commit**: a message, email or HTTP call made inside a transaction goes out even when the transaction rolls back afterwards. Publish an event and handle it with `@TransactionalEventListener`, whose default phase runs after the commit.

**Bad** — `place()` is called on `this`, so no transaction is started:

```java
@Service
public class OrderService {
    public void placeAll(List<Order> orders) {
        for (Order order : orders) {
            place(order);
        }
    }

    @Transactional
    public void place(Order order) {
        stock.reserve(order);
        orders.save(order);
    }
}
```

**Good** — the call goes through the proxy of another bean, so each order gets its own transaction:

```java
@Service
public class OrderService {
    private final OrderPlacer placer; // a separate bean whose place(Order) is @Transactional

    public OrderService(OrderPlacer placer) {
        this.placer = placer;
    }

    public void placeAll(List<Order> orders) {
        for (Order order : orders) {
            placer.place(order);
        }
    }
}
```

## JPA and Data Access

- **N+1 queries**: reading a lazy association for each entity of a list runs one query per entity. Fetch what the loop needs with `JOIN FETCH`, `@EntityGraph` or a DTO projection. **Not a finding:** a loop over a small set whose size the code bounds.
- **Open Session in View**: Spring Boot enables `spring.jpa.open-in-view` by default in web applications and logs a warning at startup when it is not set explicitly. While it is on, lazy loading works in controllers and JSON serialization, outside the service's transaction, running extra queries and holding a database connection for the whole request; when it is `false`, the same access throws `LazyInitializationException`. Read the setting before reporting either.
- **Pagination with fetched collections**: a query that fetches a collection with `JOIN FETCH` and is paged with a `Pageable` or `setMaxResults` makes Hibernate load every matching row and apply the page in memory, logging only a warning. Page over the parent ids first and fetch the collections for that page, or set `hibernate.query.fail_on_pagination_over_collection_fetch` so that such a query fails.
- **Lost updates**: a read-modify-write of a row that concurrent requests change, without `@Version` optimistic locking or a pessimistic lock (`@Lock(LockModeType.PESSIMISTIC_WRITE)`), keeps only the last write.
- **Stale entities after bulk updates**: a `@Modifying` `@Query` update or delete bypasses the persistence context, so entities already loaded in it keep their old values unless the query sets `clearAutomatically = true` or the code reloads them.

## Web Layer

- **Bean Validation not running**: constraints on a request object, such as `@NotNull` or `@Size`, run only when the controller parameter has `@Valid` or `@Validated` and a validation provider is on the classpath. Since Spring Boot 2.3 the web starters no longer include one, so the build needs `spring-boot-starter-validation`. Nested objects need `@Valid` on their field.
- **Entities bound from requests**: binding `@RequestBody` or `@ModelAttribute` directly to a JPA entity lets a client set any property that has a setter, such as `role` or `ownerId`, and saving the entity writes them. Bind a dedicated request object, or restrict form binding with `@InitBinder` and `setAllowedFields`. Returning entities can also serialize fields such as `passwordHash`.

**Bad** — a client can send `"role": "ADMIN"` and it is saved:

```java
@PutMapping("/me")
public User update(@AuthenticationPrincipal AppUser me, @RequestBody User user) {
    user.setId(me.id());
    return users.save(user);
}
```

**Good** — only the fields the client may change are bound and validated:

```java
public record UpdateProfile(@NotBlank String displayName, @Email String email) {}

@PutMapping("/me")
public UserView update(@AuthenticationPrincipal AppUser me, @Valid @RequestBody UpdateProfile body) {
    User user = users.findById(me.id()).orElseThrow();
    user.setDisplayName(body.displayName());
    user.setEmail(body.email());
    return UserView.from(users.save(user));
}
```

## Security Configuration

- **Rule order**: `authorizeHttpRequests` checks its rules in order and applies the first one that matches, so a broad `permitAll()` placed before a narrower rule, such as `/api/**` before `/api/admin/**`, opens the narrower paths. `anyRequest()` comes last.
- **Method security not enabled**: `@PreAuthorize` and `@PostAuthorize` have no effect unless method security is enabled, with `@EnableMethodSecurity` (Spring Security 5.6+) or, before it, `@EnableGlobalMethodSecurity(prePostEnabled = true)`; `@Secured` also needs `securedEnabled = true`.
- **Actuator exposure**: Spring Boot exposes only the `health` endpoint over HTTP by default. A change that sets `management.endpoints.web.exposure.include=*`, or adds `heapdump`, without securing the endpoints lets anyone download a heap dump, which holds secrets and session data from memory. **Not a finding:** exposing `env` or `configprops` alone on Spring Boot 3.0+, whose values are sanitized by default unless `show-values` is changed.

## Concurrency

- **Shared state in singletons**: Spring beans are singletons by default and serve requests concurrently, so a mutable field written per request, such as a counter, a `HashMap` cache, a `SimpleDateFormat` or the current user, is shared and races. **Not a finding:** final fields that hold immutable or thread-safe objects (`ConcurrentHashMap`, `AtomicLong`, `DateTimeFormatter`).
- **Virtual threads and `synchronized`**: with `spring.threads.virtual.enabled=true` (Spring Boot 3.2+ on Java 21+), blocking I/O inside a `synchronized` block or method pins the virtual thread to its carrier thread on JDK 21 to 23, so a few slow calls can stall every virtual thread. JDK 24 (JEP 491) removes that pinning; on older JDKs use a `ReentrantLock` around blocking I/O.

## Conventions, not defects

- Field injection versus constructor injection is a preference. It is a finding only with a concrete defect, such as an object created with `new` whose `@Autowired` fields stay `null`.
- Where `@Transactional` sits (service or repository) and `readOnly = true` are design defaults; a finding needs a missing or broken transaction boundary with a scenario, such as a partial write.
- Global exception handling with `@ControllerAdvice` and DTO mapping in general are choices; the items above say when they become findings.

## Sources

- Proxy mode, method visibility and rollback rules: https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html, https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html
- Propagation and `UnexpectedRollbackException`: https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html
- Transaction-bound events: https://docs.spring.io/spring-framework/reference/data-access/transaction/event.html
- Bean scopes: https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html
- `spring.jpa.open-in-view` and `spring.threads.virtual.enabled`: https://docs.spring.io/spring-boot/appendix/application-properties/index.html
- Hibernate fetching and pagination: https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html
- `@Modifying` queries: https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html; locking: https://docs.spring.io/spring-data/jpa/reference/jpa/locking.html
- Validation: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-validation.html; Spring Boot 2.3 release notes: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.3-Release-Notes
- Binding and model design: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-initbinder.html
- `authorizeHttpRequests` and method security: https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html, https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html
- Actuator endpoints: https://docs.spring.io/spring-boot/reference/actuator/endpoints.html
- Virtual threads and pinning: https://openjdk.org/jeps/444, https://openjdk.org/jeps/491

## Precedents

- **Spring Data, JPA and `JdbcTemplate` bind parameters**: derived query methods, `@Query` with named (`:name`) or positional (`?1`) parameters, the Criteria API, and `JdbcTemplate` with `?` arguments send values as bound parameters. Do not report SQL injection for those bound values. **Exception:** JPQL or SQL built by string concatenation or `String.format` and passed to `createQuery`, `createNativeQuery` or `JdbcTemplate`, and sort expressions that reach the query text, such as `JpaSort.unsafe(untrustedExpression)` in a `Sort` passed to a `@Query` method, since a sort expression is query structure rather than a bound value.
- **Spring Security checks CSRF on covered unsafe requests**: a request covered by the selected `SecurityFilterChain` with its `CsrfFilter` enabled is rejected without a valid token when its CSRF matcher requires protection; the default matcher excludes `GET`, `HEAD`, `TRACE` and `OPTIONS`. Do not report missing server-side CSRF validation on an unsafe-method form post after verifying that this active filter and matcher cover it. **Exception:** routes outside every `SecurityFilterChain` (for example outside the chain's `securityMatcher`) or excluded from Spring Security entirely, a selected chain with CSRF disabled (`csrf(csrf -> csrf.disable())` or `csrf().disable()`), requests excluded by `ignoringRequestMatchers` or a custom `requireCsrfProtectionMatcher`, state changes on methods the matcher does not protect, and forms that fail with a 403 because they do not submit a valid token.
- **Thymeleaf `th:text` escapes**: in HTML template mode, `th:text` and `[[...]]` inlining escape HTML, which makes values safe in HTML text; inside a block marked `th:inline="javascript"`, `[[...]]` is instead serialized as an escaped JavaScript value. Do not report XSS for values rendered that way. **Exception:** `th:utext` and `[(...)]` inlining, which do not escape in any mode, `[[...]]` inside a `<script>` block or event-handler attribute without `th:inline="javascript"`, where HTML escaping does not protect JavaScript, and user-controlled URLs in `th:href`, `th:src` or `th:action`, where escaping does not stop a `javascript:` URL.
