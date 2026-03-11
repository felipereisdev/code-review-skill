# Node.js — Code Review Checklist

- **Error handling**: async errors caught with try/catch or `.catch()`; no unhandled promise rejections
- **Environment variables**: validated at startup; not accessed raw throughout the codebase
- **Stream usage**: large data processed with streams, not loaded entirely into memory
- **Graceful shutdown**: process handles `SIGTERM`/`SIGINT` and cleans up connections
- **Concurrency**: CPU-intensive work offloaded to worker threads or external processes
- **Logging**: structured logging (JSON) with appropriate log levels; no `console.log` in production; no sensitive data (passwords, tokens, PII) logged even partially
- **Security headers**: Helmet or equivalent middleware applied for HTTP security headers
- **Connection pooling**: database and HTTP connections pooled and reused
- **Input validation**: request payloads validated with a schema library (Zod, Joi, etc.)
- **Path handling**: file paths built with `path.join`/`path.resolve`, not string concatenation
