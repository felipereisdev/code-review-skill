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

## Precedents

- **Argument arrays bypass the shell**: `execFile`, `execFileSync`, `spawn` and `spawnSync` with the `shell` option unset or `false` start the named program directly and pass each array element to it as one argument, so shell metacharacters in them are not interpreted. Do not report shell injection for user input passed as a data argument to a fixed program that is not a shell or interpreter. **Exception:** `exec` and `execSync`, any call whose `shell` option is `true`, a string naming a shell (for example `shell: '/bin/sh'`) or a value the code does not fix as `false`, which joins the command and its arguments into one shell command line, a shell or interpreter that receives user input as code (`sh -c`, `bash -c`, `cmd /c`, PowerShell `-Command`, `node -e`, `python -c` and similar), user input that chooses the program or its subcommand, Windows `.bat` and `.cmd` files, which run through `cmd.exe`, and user input that starts with `-`, which the program may read as an option (argument injection).
- **Bound placeholders parameterize SQL**: `pg` `$1` value parameters, and `mysql2` `?` placeholders sent through its prepared-statement API (`execute()`, or `prepare()` followed by `statement.execute()`), reach the server separately from the SQL text, so the server never parses those values as SQL. Do not report SQL injection for values passed in the parameter array of those calls. **Exception:** `mysql2` `query()` and `format()`, which escape the values on the client and splice them into the SQL text, so a candidate there is dismissed only after checking that the connection does not enable the `NO_BACKSLASH_ESCAPES` SQL mode (in that mode the inserted backslash is ordinary text and a quote in the value closes the string), that no custom `queryFormat` is configured, and that the values are scalars rather than objects or arrays from a parsed request body, which `query()` expands into SQL fragments; SQL text built with template literals or `+`; and table or column names taken from user input.
