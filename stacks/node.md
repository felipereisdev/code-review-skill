# Node.js — Code Review Checklist

> These items are about code that runs on the Node.js runtime: servers, workers, CLIs and build scripts. Code that runs in a browser or in React Native is JavaScript but not Node.js; never apply this file to it. Check sibling modules for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that ESLint or TypeScript as configured in the repository already reports is not a finding. An item that depends on a version names the Node.js or package version that it needs; read it from `engines`, `.nvmrc` or the lockfile.

## Promises and Errors

- **Unhandled rejections**: since Node.js 15, an unhandled promise rejection ends the process by default (`--unhandled-rejections=throw`). A promise started without `await` or `.catch()`, such as `sendWelcomeEmail(user)` in a request handler, crashes the server on its first failure; on Node.js 14 and older it only logs a warning and the error is lost.
- **Express 4 async handlers**: Express 4 does not catch a rejected promise from an `async` route handler or middleware, so the error never reaches the error-handling middleware, the request hangs until the client times out, and the rejection is unhandled. **Not a finding:** Express 5, which passes a rejected promise to `next(err)`, and handlers that catch their errors and call `next(err)` themselves.
- **`forEach` with `async` callbacks**: `items.forEach(async (item) => ...)` does not wait for the callbacks, so the function returns before the work ends and their errors are unhandled. Use `for...of` with `await`, or `await Promise.all(items.map(...))`.
- **`error` events**: an `EventEmitter` that emits `'error'` with no `'error'` listener throws, which crashes the process; streams, sockets and child processes emit it.

**Bad** — with Express 4, a rejected query never reaches the error handler and the request hangs:

```js
app.get('/orders/:id', async (req, res) => {
  const order = await db.getOrder(req.params.id);
  res.json(order);
});
```

**Good** — with Express 4, the error is passed to the error-handling middleware:

```js
app.get('/orders/:id', async (req, res, next) => {
  try {
    const order = await db.getOrder(req.params.id);
    res.json(order);
  } catch (err) {
    next(err);
  }
});
```

## Event Loop and Resources

- **Blocking the event loop**: synchronous APIs such as `fs.readFileSync`, `crypto.pbkdf2Sync`, `zlib.gzipSync` or `child_process.execSync`, and CPU-heavy loops, in a request handler stop every other request until they finish. Use the asynchronous API, or move CPU-bound work to a worker thread. **Not a finding:** synchronous calls at startup, in CLIs and in build scripts.
- **Unbounded buffering**: reading a whole upload, response or file whose size the client controls into memory (`fs.readFile`, or collecting every `data` chunk) can exhaust memory; process it as a stream. **Not a finding:** bodies parsed by `express.json()` or `express.urlencoded()`, which reject bodies over their `limit` (`100kb` by default).
- **Stream errors**: `source.pipe(destination)` does not forward errors or destroy the other stream when one fails, so a failed read leaves the response open and the file descriptor leaked. `stream.pipeline()`, or `pipeline` from `node:stream/promises`, destroys every stream on error and reports it.
- **Database connections**: creating a pool or a connection per request exhausts the database's connection limit. A client checked out with `pool.connect()` must be released on every path (`finally { client.release(); }`); a missed release leaks it until the pool is empty and every request waits. **Not a finding:** `pool.query()`, which checks out and releases a client by itself.
- **Signal handlers**: adding a `SIGTERM` or `SIGINT` listener removes Node.js's default exit for that signal, so a handler that only logs, or that leaves timers, intervals or connections open, keeps the process running until it is killed. **Not a finding:** no handler at all, where Node.js exits on the signal.

**Bad** — a failed query skips `release()`, and the pool runs out of clients:

```js
async function transfer(pool, from, to, amount) {
  const client = await pool.connect();
  await client.query('BEGIN');
  await client.query('UPDATE accounts SET balance = balance - $1 WHERE id = $2', [amount, from]);
  await client.query('UPDATE accounts SET balance = balance + $1 WHERE id = $2', [amount, to]);
  await client.query('COMMIT');
  client.release();
}
```

**Good** — rolls back on failure and always releases the client:

```js
async function transfer(pool, from, to, amount) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query('UPDATE accounts SET balance = balance - $1 WHERE id = $2', [amount, from]);
    await client.query('UPDATE accounts SET balance = balance + $1 WHERE id = $2', [amount, to]);
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}
```

## Security

- **Paths from input**: `path.join(base, name)` normalizes `..` but does not keep the result inside `base` (`path.join('/srv/files', '../../etc/passwd')` is `/etc/passwd`), and `path.resolve(base, name)` returns an absolute `name` as it is. Resolve the path, then check that it starts with `base` followed by `path.sep` (and use `fs.realpath` first when the directory can contain symbolic links). **Not a finding:** `res.sendFile(name, { root })` and `express.static(root)`, which check that the path stays inside `root`.
- **Prototype pollution**: a recursive merge, or a set-by-path helper, that copies keys from request data lets a `__proto__` or `constructor.prototype` key modify `Object.prototype` for the whole process. Skip those keys, or build lookups with `Object.create(null)` or a `Map`. **Not a finding:** a one-level `Object.assign()` or object spread of a parsed body, which does not modify `Object.prototype`.
- **Comparing secrets**: comparing an API key, token or HMAC with `===` takes time that depends on how much of it matches. Use `crypto.timingSafeEqual()`, which throws when the two buffers have different lengths, so compare the lengths first or compare fixed-length digests.
- **Random values for secrets**: `Math.random()` is predictable; tokens, reset codes and IDs that must not be guessed come from `crypto.randomBytes()`, `crypto.randomUUID()` or `crypto.randomInt()`.
- **Environment values are strings**: `process.env.X` is a string or `undefined`, so `if (process.env.FEATURE_ENABLED)` is true for `"false"`, and `process.env.PORT + 1` concatenates. Parse values explicitly.
- **Secrets in logs**: logging request bodies, `authorization` or `cookie` headers, tokens or passwords, even partially, copies them to every log store and to everyone who can read it.

**Bad** — `name` can be `../../etc/passwd`:

```js
const path = require('node:path');
const fs = require('node:fs/promises');

const UPLOADS = '/srv/uploads';

async function readUpload(name) {
  return fs.readFile(path.join(UPLOADS, name));
}
```

**Good** — rejects any name that resolves outside the uploads directory:

```js
const path = require('node:path');
const fs = require('node:fs/promises');

const UPLOADS = '/srv/uploads';

async function readUpload(name) {
  const file = path.resolve(UPLOADS, name);
  if (!file.startsWith(UPLOADS + path.sep)) {
    throw new Error('invalid file name');
  }
  return fs.readFile(file);
}
```

## Conventions, not defects

- The logging library, a JSON log format and `console.log` are choices; a log line is a finding only when it leaks a secret or personal data, or loses an error.
- Security-header middleware such as Helmet is generic hardening; it is a finding only when the change removes a protection that the app relied on and you can name the attack that it reopens.
- A schema validation library (Zod, Joi or another) is a choice; missing validation is a finding when unvalidated input reaches something that needs it, such as a query, a privileged field or a file path.
- Validating every environment variable at startup, and building paths with `path.join` instead of string concatenation, are not findings by themselves; the items above say when values and paths become bugs.

## Sources

- `--unhandled-rejections`: https://nodejs.org/api/cli.html#--unhandled-rejectionsmode
- Express error handling in Express 4 and 5: https://expressjs.com/en/guide/error-handling.html
- `express.json()`, `express.urlencoded()`, `express.static()`: https://expressjs.com/en/5x/api/express/; `res.sendFile()`: https://expressjs.com/en/5x/api/response
- `'error'` events: https://nodejs.org/api/events.html#error-events
- Blocking the event loop: https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- Streams and `pipeline`: https://nodejs.org/api/stream.html#streampipelinesource-transforms-destination-callback
- node-postgres pooling and transactions: https://node-postgres.com/features/pooling, https://node-postgres.com/features/transactions
- Signal events and `process.env`: https://nodejs.org/api/process.html#signal-events, https://nodejs.org/api/process.html#processenv
- `path.join()` and `path.resolve()`: https://nodejs.org/api/path.html
- Prototype pollution: https://nodejs.org/en/learn/getting-started/security-best-practices
- `crypto.timingSafeEqual()`, `randomBytes()`, `randomUUID()`, `randomInt()`: https://nodejs.org/api/crypto.html

## Precedents

- **Argument arrays bypass the shell**: `execFile`, `execFileSync`, `spawn` and `spawnSync` with the `shell` option unset or `false` start the named program directly and pass each array element to it as one argument, so shell metacharacters in them are not interpreted. Do not report shell injection for user input passed as a data argument to a fixed program that is not a shell or interpreter. **Exception:** `exec` and `execSync`, any call whose `shell` option is `true`, a string naming a shell (for example `shell: '/bin/sh'`) or a value the code does not fix as `false`, which joins the command and its arguments into one shell command line, a shell or interpreter that receives user input as code (`sh -c`, `bash -c`, `cmd /c`, PowerShell `-Command`, `node -e`, `python -c` and similar), user input that chooses the program or its subcommand, Windows `.bat` and `.cmd` files, which run through `cmd.exe`, and user input that starts with `-`, which the program may read as an option (argument injection).
- **Bound placeholders parameterize SQL**: `pg` `$1` value parameters, and `mysql2` `?` placeholders sent through its prepared-statement API (`execute()`, or `prepare()` followed by `statement.execute()`), reach the server separately from the SQL text, so the server never parses those values as SQL. Do not report SQL injection for values passed in the parameter array of those calls. **Exception:** `mysql2` `query()` and `format()`, which escape the values on the client and splice them into the SQL text, so a candidate there is dismissed only after checking that the connection does not enable the `NO_BACKSLASH_ESCAPES` SQL mode (in that mode the inserted backslash is ordinary text and a quote in the value closes the string), that no custom `queryFormat` is configured, and that the values are scalars rather than objects or arrays from a parsed request body, which `query()` expands into SQL fragments; SQL text built with template literals or `+`; and table or column names taken from user input.
