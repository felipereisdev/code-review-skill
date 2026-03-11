# Microservices — Code Review Checklist

- **No shared databases**: services do not share database tables; data exchanged via API or events
- **Contract testing**: inter-service contracts tested independently of integration environments
- **Service boundaries**: changes do not introduce tight coupling between services
- **Distributed tracing**: trace IDs propagated across service calls
