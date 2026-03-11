# Java / Spring Boot — Code Review Checklist

- **Bean lifecycle**: beans are stateless where possible; stateful beans scoped correctly (`@RequestScope`, `@SessionScope`)
- **Transaction boundaries**: `@Transactional` applied at the service layer, not the repository layer; read-only transactions use `readOnly = true`
- **Lazy vs eager fetch**: JPA fetch types explicit; no unintended lazy loading in detached contexts causing `LazyInitializationException`
- **Exception handling**: `@ControllerAdvice` / `@ExceptionHandler` used for global error handling; exceptions not leaked to the client
- **Dependency injection**: constructor injection used; field injection (`@Autowired` on fields) avoided
- **DTO vs Entity**: entities not exposed directly in API responses; DTOs used for request/response mapping
