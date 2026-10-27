# Docker — Code Review Checklist

> These items are about Dockerfiles, Compose files and the `docker build` and `docker run` commands in the repository's scripts and CI. Check sibling Dockerfiles and Compose files for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code, judged on the effective configuration: the Dockerfile and build context that the build actually uses, Compose override files, and the flags of the command that starts the container. A problem that hadolint or another linter configured in the repository already reports is not a finding. Docker's build checks (Buildx 0.15 and later) run on every build but only print warnings unless the Dockerfile sets `# check=error=true`; a Dockerfile with that directive already fails on what they report.

## Secrets in Images

- **Secrets in `ARG` or `ENV`**: build arguments are visible in `docker history` and in max-mode provenance attestations, and `ENV` values persist in the image and in every container started from it, so a token passed either way is readable by anyone who can pull the image. Pass build-time secrets with a secret mount (`RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci`, built with `--secret id=npmrc,src=...`), which exposes the value only to that `RUN` instruction and does not store it in the image. **Not a finding:** `ARG` and `ENV` for values that are not secret, such as versions, and secrets that only the running container receives (`docker run -e`, Compose `secrets` or the orchestrator's secrets), which are not stored in the image.
- **Files deleted in a later layer**: image layers are immutable, and each layer records only the changes of its instruction. A key, credential or private file that one instruction copies or downloads and a later instruction deletes is still in the earlier layer, which ships with the image. **Not a finding:** a file created and deleted within the same `RUN` instruction, and a file that exists only in an earlier stage of a multi-stage build that the final stage does not copy (see Precedents).

**Bad** — the token is recorded with the `RUN` instruction and is visible to anyone who runs `docker history` on the image:

```dockerfile
FROM node:22-slim
WORKDIR /app
ARG NPM_TOKEN
COPY package.json package-lock.json ./
RUN echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > .npmrc \
    && npm ci --omit=dev \
    && rm .npmrc
COPY . .
CMD ["node", "server.js"]
```

**Good** — the `.npmrc` comes from a secret mount, built with `docker build --secret id=npmrc,src=$HOME/.npmrc .`, and is not stored in any layer:

```dockerfile
FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci --omit=dev
COPY . .
CMD ["node", "server.js"]
```

## Build Correctness

- **`apt-get update` in its own `RUN`**: Docker caches `RUN apt-get update` as a separate layer, so a later change to the `apt-get install` line reuses the old package index, and the install can fail or install outdated packages. Run `apt-get update` and `apt-get install` in the same `RUN` instruction.
- **File ownership after `USER`**: `COPY` and `ADD` create files owned by UID and GID 0 unless they use `--chown`. When the change adds `USER app` and the application writes to a copied directory (uploads, a cache, an SQLite file), the write fails at runtime with a permission error. Copy with `--chown=app:app`, or create the writable directories with that owner. **Not a finding:** files that the application only reads, when their mode lets the user read them.

**Bad** — after the first build, editing the package list reuses the cached `apt-get update` layer:

```dockerfile
FROM debian:bookworm-slim
RUN apt-get update
RUN apt-get install -y --no-install-recommends curl ca-certificates
```

**Good** — the index is refreshed whenever the install line changes:

```dockerfile
FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

## Runtime and Privileges

- **Signals to the application**: `docker stop` sends `SIGTERM` to the container's main process and `SIGKILL` after a grace period (10 seconds by default for Linux containers). The shell form of `ENTRYPOINT` or `CMD` runs the command under `/bin/sh -c`, which does not pass signals on. Whether the application still gets `SIGTERM` depends on the shell, which may replace itself with a single simple command, but a command list (`CMD ./migrate && node server.js`), or an entrypoint script that starts the application without `exec`, keeps the shell as the main process: the application never receives `SIGTERM` and is killed when the grace period ends, without finishing in-flight requests or running its shutdown code. Use the exec form (`CMD ["node", "server.js"]`) and start the application with `exec` in entrypoint scripts. **Not a finding:** a shell-form command that starts with `exec`.
- **Privileged containers and the Docker socket**: `--privileged` (Compose `privileged: true`) gives the container all capabilities and access to every host device, and mounting `/var/run/docker.sock` lets the container control the Docker daemon, which runs as root unless it is rootless. Either way, code that compromises the container controls the host. Report a change that adds either to a service that does not manage containers itself, such as a web application or a worker that processes untrusted input.
- **Published ports without a host address**: a published port without a host IP (Compose `ports: ["5432:5432"]`, `docker run -p 6379:6379`) binds to all host interfaces, so a database, cache or admin port meant for local use is reachable from other machines, and Compose warns that this bypasses host firewall rules. Bind it to `127.0.0.1` (`"127.0.0.1:5432:5432"`), or connect over the Compose network without publishing it. **Not a finding:** ports meant to be public, such as the web server's.

**Bad** — the shell stays the main process, so `node server.js` never receives `SIGTERM` and is killed after the grace period:

```sh
#!/bin/sh
# docker-entrypoint.sh, used as ENTRYPOINT ["/docker-entrypoint.sh"]
set -e
node migrate.js
node server.js
```

**Good** — `exec` replaces the shell, so the server receives `SIGTERM` and can shut down cleanly:

```sh
#!/bin/sh
# docker-entrypoint.sh, used as ENTRYPOINT ["/docker-entrypoint.sh"]
set -e
node migrate.js
exec node server.js
```

## Conventions, not defects

- Slim or Alpine base images, pinned tags or digests, the order of instructions for cache reuse and `HEALTHCHECK` are build and operations choices; they are findings only with a concrete effect in this change, such as a base image switch that breaks a native dependency.
- Running as root is generic hardening by itself. It becomes part of a finding when the change gives the container a path to the host (see the privileges item) or when the repository's rules require a non-root user.

## Sources

- Build secrets: https://docs.docker.com/build/building/secrets/
- Dockerfile reference (`ARG`, `ENV`, `COPY --chown`, `RUN --mount`, shell and exec forms): https://docs.docker.com/reference/dockerfile/
- Best practices (`apt-get`, `USER`, `exec` in entrypoint scripts): https://docs.docker.com/build/building/best-practices/
- Image layers: https://docs.docker.com/get-started/docker-concepts/building-images/understanding-image-layers/
- Build checks: https://docs.docker.com/build/checks/
- `docker stop`: https://docs.docker.com/reference/cli/docker/container/stop/
- `--privileged`: https://docs.docker.com/engine/containers/run/; daemon attack surface: https://docs.docker.com/engine/security/
- Published ports: https://docs.docker.com/engine/network/port-publishing/; Compose `ports` and `privileged`: https://docs.docker.com/reference/compose-file/services/

## Precedents

- **Earlier build stages do not ship**: in a multi-stage build whose final stage starts `FROM` an independent base image (not an earlier stage), only the final stage's own filesystem becomes the image, and a file that exists only in an earlier stage is in the image only if a final-stage instruction puts it there. A `RUN --mount=from=<stage>` mount makes that stage readable only while its command runs and is not itself part of the image. Do not report build tools, dev dependencies or source files in an earlier stage as shipped after checking that no final-stage instruction copies, extracts or embeds them into the final stage's filesystem. **Exception:** a final stage that starts `FROM` an earlier stage, directly or through another stage, which inherits that stage's whole filesystem; files the final stage copies with `COPY --from=<stage>`; final-stage `RUN` commands that copy, extract or embed contents of an earlier stage mounted with `--mount=from=<stage>` into a path outside the mount (for example `RUN --mount=from=build,target=/stage cp /stage/src/private.env /private.env`), which persist them in the image; and builds that select an earlier stage with `--target` (or Compose `build.target`).
- **`.dockerignore` keeps files out of the build context**: paths matched by the ignore file that actually applies to the Dockerfile and build context in use are not sent to the builder, so `COPY . .` cannot copy them. Do not report `COPY . .` as copying `.env`, `.git` or `node_modules` when that effective ignore file excludes them. **Exception:** a Dockerfile-specific ignore file (`<Dockerfile name>.dockerignore` next to the Dockerfile, such as `prod.Dockerfile.dockerignore`), which replaces the root `.dockerignore` for that Dockerfile, a build context whose root is not the directory holding the `.dockerignore` (check the `docker build` path or the Compose `context`), patterns that match only at the context root (`.env` does not exclude `config/.env`, but `**/.env` does), and later `!` lines that include a path again.
