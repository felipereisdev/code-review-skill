# Docker — Code Review Checklist

- **Minimal base image**: slim or alpine variants used where possible; no unnecessary tools in production image
- **Multi-stage builds**: build dependencies not present in the final image
- **No secrets in image**: secrets not passed as `ENV` or `ARG` in build; mounted at runtime
- **Non-root user**: container runs as a non-root user
- **Layer caching**: `COPY` and `RUN` instructions ordered to maximize layer cache reuse (dependencies before source code)
- **Pinned versions**: base image tags pinned to a specific version, not `latest`
