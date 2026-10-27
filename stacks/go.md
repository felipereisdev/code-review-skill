# Go — Code Review Checklist

> Check sibling packages for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that the compiler, `go vet` or a linter configured in the repository already reports is not a finding. An item that depends on a Go version names the `go` line of `go.mod` that it needs.

## Errors

- **Dropped errors**: an error discarded with `_` or never checked, on a call whose failure changes the result (`rows.Scan`, `json.Unmarshal`, `tx.Commit`, or `Close` of a file that was written), lets the code continue with zero values or report success after a failed write. **Not a finding:** errors that the callee documents as always `nil`, such as writes to a `bytes.Buffer` or `strings.Builder`, and an ignored `Close` of a file that was only read.
- **Matching wrapped errors**: `err == ErrNotFound` or a type assertion such as `err.(*NotFoundError)` misses an error that a lower layer wrapped with `%w`; use `errors.Is` and `errors.As` (Go 1.13+). Wrapping with `%v` instead of `%w` breaks a caller that matches the cause with `errors.Is`. **Not a finding:** wrapping style or message wording where no caller inspects the error, and `err == io.EOF` on a `Read` result, because `Read` returns `io.EOF` itself, never wrapped.
- **Typed nil in an `error`**: a function whose result type is `error` and that returns a `nil` pointer of a concrete error type returns a non-nil interface, so the caller's `err != nil` is true on success. Return the literal `nil`.
- **Panics in goroutines**: `net/http` recovers a panic in the handler goroutine and aborts only that request, but a panic in a goroutine that the code starts with `go` is recovered by nobody and ends the whole process.

**Bad** — returns a non-nil `error` even when validation passes:

```go
func validate(o Order) error {
	var verr *ValidationError
	if o.Qty <= 0 {
		verr = &ValidationError{Field: "qty"}
	}
	return verr // a nil *ValidationError is still a non-nil error
}
```

**Good** — returns the `nil` interface on success:

```go
func validate(o Order) error {
	if o.Qty <= 0 {
		return &ValidationError{Field: "qty"}
	}
	return nil
}
```

## Goroutines and Channels

- **Goroutine leaks**: a goroutine that sends on an unbuffered channel, or waits to receive, after the other side has returned (on a timeout, `ctx.Done()` or an early error) blocks forever and keeps its memory and everything it references; on a per-request path the leak grows with traffic. Give the channel room for every send that can be abandoned, or make the sender also select on `ctx.Done()`.
- **Data races**: a map, slice or struct field that one goroutine writes while another reads or writes it, with no mutex, channel or `sync/atomic` between them, is a data race. Concurrent map writes can stop the program with `fatal error: concurrent map writes`, which `recover` cannot catch. `net/http` runs handlers concurrently, so package-level variables and fields of a handler struct are shared by all requests. **Not a finding:** state that a single goroutine owns, and values read after `wg.Wait()` or a channel receive that orders them after the writes.
- **`sync.WaitGroup` counting**: `wg.Add(1)` inside the goroutine it counts can run after `wg.Wait()` has returned, so `Wait` does not wait for it. Call `Add` before the `go` statement, or use `wg.Go` (Go 1.25+).
- **Closing channels**: sending on a closed channel and closing a channel twice both panic. Only the sole sender, or a coordinator after all senders have finished, closes a channel.

**Bad** — the goroutine blocks forever when the context ends first:

```go
func fetch(ctx context.Context, url string) (*Result, error) {
	ch := make(chan *Result)
	go func() { ch <- slowFetch(ctx, url) }()
	select {
	case r := <-ch:
		return r, nil
	case <-ctx.Done():
		return nil, ctx.Err() // nobody ever receives from ch
	}
}
```

**Good** — a buffer of one lets the abandoned send complete, so the goroutine exits:

```go
func fetch(ctx context.Context, url string) (*Result, error) {
	ch := make(chan *Result, 1)
	go func() { ch <- slowFetch(ctx, url) }()
	select {
	case r := <-ch:
		return r, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}
```

## Context and Cancellation

- **Lost `cancel`**: `context.WithCancel`, `WithTimeout` and `WithDeadline` return a `cancel` function that must run on every path; a path that skips it keeps the child context and its timer alive until the parent ends. `go vet` reports this as `lostcancel` when the repository runs it.
- **Ignored context**: a blocking call on a request path that cannot be cancelled, such as `http.Get`, `db.Query` instead of `db.QueryContext`, or `time.Sleep`, keeps working after the client has gone or the deadline has passed. Pass the request's `ctx` (`http.NewRequestWithContext`, `QueryContext`, or a `select` on `ctx.Done()`).
- **Work that must outlive the request**: the context of an incoming server request is cancelled when the client's connection closes or when `ServeHTTP` returns, so work started with it after the response, such as sending an email, is cancelled midway. Use `context.WithoutCancel(ctx)` (Go 1.21+) or a new background context with its own timeout.
- **Contexts in structs**: the `context` package says not to store a `Context` in a struct, but that alone is a convention. Report it only when a stored request context is used after its request has ended, so that later calls fail with `context canceled`.

## Resources

- **HTTP response bodies**: a `resp.Body` that is not closed on every path, including non-2xx responses, leaks the connection. `defer resp.Body.Close()` belongs after the `err` check, because `resp` is `nil` when `err` is not.
- **HTTP clients**: `http.Get`, `http.DefaultClient` and an `http.Client` without `Timeout` wait forever for a server that never answers, unless every request carries a context with a deadline. A new `http.Client` with a new `Transport` per request defeats connection reuse and can exhaust sockets under load. **Not a finding:** a request made with `http.NewRequestWithContext` whose context has a deadline.
- **`database/sql` rows**: a `*sql.Rows` that is not closed (`defer rows.Close()`) keeps its connection out of the pool. After the `rows.Next()` loop, `rows.Err()` reports an error that ended the loop early; without that check a partial result is returned as complete. `QueryRow(...).Scan` returns `sql.ErrNoRows` when there is no row; check it with `errors.Is`.
- **`defer` in loops**: deferred calls run when the surrounding function returns, not at the end of each iteration, so `defer f.Close()` in a loop over many files keeps all of them open until then and can hit the open-file limit. Move the loop body into its own function, or close explicitly.
- **Timers in loops**: in a module whose `go.mod` declares `go 1.22` or lower, each `time.After` in a long-running `select` loop allocates a timer that is not freed until it fires. **Not a finding:** the same code when the main module declares `go 1.23` or later, where unreferenced timers are collected without `Stop`.

**Bad** — panics when the request fails, because `resp.Body` is evaluated when the `defer` statement runs and `resp` is `nil`:

```go
resp, err := client.Do(req)
defer resp.Body.Close()
if err != nil {
	return err
}
if resp.StatusCode != http.StatusOK {
	return fmt.Errorf("unexpected status %d", resp.StatusCode)
}
```

**Good** — closes the body on every path after a successful request:

```go
resp, err := client.Do(req)
if err != nil {
	return err
}
defer resp.Body.Close()
if resp.StatusCode != http.StatusOK {
	return fmt.Errorf("unexpected status %d", resp.StatusCode)
}
```

## Security

- **Paths from input**: `filepath.Join(base, name)` cleans `..` but does not keep the result inside `base`: `filepath.Join("/srv/files", "../../etc/passwd")` is `/etc/passwd`. Reject names for which `filepath.IsLocal` (Go 1.20+) is false, or open them through an `os.Root` (Go 1.24+), which refuses paths that leave its directory. **Not a finding:** request paths served by `http.FileServer(http.Dir(root))`, which keeps them inside `root`, except through symbolic links inside `root` that point outside it.
- **Commands**: `exec.Command(name, args...)` starts the program directly, without a shell, so shell metacharacters in `args` are not shell injection. Input does become code or options in `exec.Command("sh", "-c", script)` with input in `script`, when input picks the program, and when an argument from input starts with `-`, which the program may read as an option.
- **Randomness for secrets**: `math/rand` and `math/rand/v2` are not for security-sensitive values, however they are seeded. Tokens, passwords, nonces and session IDs come from `crypto/rand`.
- **Server timeouts**: an `http.Server` that untrusted clients reach directly, with no `ReadHeaderTimeout` or `ReadTimeout`, lets a client hold connections open by sending headers slowly. Report it only when the change adds or exposes such a server and nothing in front of it that the repository configures, such as a proxy or load balancer, sets a timeout.

## Conventions, not defects

- Where an interface is declared, how small it is, and whether errors are sentinel values or types follow the package's existing convention (Consistency Check). They are findings only when a caller provably cannot tell apart an error that it must handle differently.
- Naming, receiver names and package layout are style: `gofmt` and the linters the repository configures enforce what the team decided.

## Sources

- Language semantics (`defer`, `for` loops, map iteration): https://go.dev/ref/spec
- Error wrapping and matching: https://go.dev/blog/go1.13-errors, https://pkg.go.dev/errors; `io.EOF`: https://pkg.go.dev/io#EOF
- Typed nil errors: https://go.dev/doc/faq#nil_error
- Data races and maps: https://go.dev/ref/mem, https://go.dev/doc/faq#atomic_maps
- `sync.WaitGroup` and `WaitGroup.Go`: https://pkg.go.dev/sync#WaitGroup
- Contexts, `WithoutCancel`, `lostcancel`: https://pkg.go.dev/context, https://pkg.go.dev/cmd/vet
- `net/http` clients, response bodies, server timeouts, request contexts, handler panics and `http.Dir`: https://pkg.go.dev/net/http
- `database/sql` rows: https://pkg.go.dev/database/sql#Rows, https://go.dev/doc/database/querying
- Timer collection since Go 1.23: https://go.dev/doc/go1.23
- `filepath.IsLocal` and `os.Root`: https://pkg.go.dev/path/filepath#IsLocal, https://pkg.go.dev/os#Root
- Commands: https://pkg.go.dev/os/exec
- Randomness: https://pkg.go.dev/math/rand/v2, https://pkg.go.dev/crypto/rand

## Precedents

- **`html/template` escapes by context**: ordinary, untrusted string values rendered with `html/template` are escaped for their HTML, attribute, CSS, URL or JavaScript context. Do not report XSS solely because such a value is interpolated by `html/template`. **Exception:** values marked as trusted content (`template.CSS`, `template.HTML`, `template.HTMLAttr`, `template.JS`, `template.JSStr`, `template.URL` or `template.Srcset`), including values returned by helpers or nested in data, whose safety the code that creates them must establish, and output written with `text/template`, which does not escape.
- **`database/sql` placeholders parameterize values**: values passed as arguments to `Query`, `QueryRow` or `Exec` with `?` or `$1` placeholders are sent separately from the SQL. Do not report SQL injection for them. **Exception:** SQL text built with `fmt.Sprintf`, `+` or `strings.Join`, including table names, column names and `ORDER BY` fields, which placeholders cannot carry.
- **Loop variables are per iteration since Go 1.22**: in a module whose `go.mod` declares `go 1.22` or later, a variable declared by the `for` statement itself (`for i := ...` or `for _, v := range ...`) is a new variable in each iteration. Do not report goroutines or closures that capture such a loop-declared variable. **Exception:** modules whose `go.mod` declares `go 1.21` or lower, files whose `//go:build` line sets an older Go version, loops that assign to variables declared outside the loop (`for _, v = range ...` with `=`), and closures that read other variables or pointed-to values that all iterations share.
