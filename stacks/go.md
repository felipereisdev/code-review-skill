# Go — Code Review Checklist

- **Error wrapping**: errors wrapped with `fmt.Errorf("...: %w", err)` to preserve context; not discarded
- **Goroutine leaks**: goroutines have a clear exit path; channels are closed; `context` cancellation propagated
- **Context propagation**: `context.Context` passed as first argument through call chains; not stored in structs
- **Defer usage**: `defer` used for cleanup (close, unlock); not used in loops where it would delay execution
- **Interface design**: interfaces defined at the consumer, not the producer; small, focused interfaces preferred
- **Error types**: sentinel errors or typed errors used for programmatic handling; plain strings for log-only errors

## Precedents

- **`html/template` escapes by context**: ordinary, untrusted string values rendered with `html/template` are escaped for their HTML, attribute, CSS, URL or JavaScript context. Do not report XSS solely because such a value is interpolated by `html/template`. **Exception:** values marked as trusted content (`template.CSS`, `template.HTML`, `template.HTMLAttr`, `template.JS`, `template.JSStr`, `template.URL` or `template.Srcset`), including values returned by helpers or nested in data, whose safety the code that creates them must establish, and output written with `text/template`, which does not escape.
- **`database/sql` placeholders parameterize values**: values passed as arguments to `Query`, `QueryRow` or `Exec` with `?` or `$1` placeholders are sent separately from the SQL. Do not report SQL injection for them. **Exception:** SQL text built with `fmt.Sprintf`, `+` or `strings.Join`, including table names, column names and `ORDER BY` fields, which placeholders cannot carry.
- **Loop variables are per iteration since Go 1.22**: in a module whose `go.mod` declares `go 1.22` or later, a variable declared by the `for` statement itself (`for i := ...` or `for _, v := range ...`) is a new variable in each iteration. Do not report goroutines or closures that capture such a loop-declared variable. **Exception:** modules whose `go.mod` declares `go 1.21` or lower, files whose `//go:build` line sets an older Go version, loops that assign to variables declared outside the loop (`for _, v = range ...` with `=`), and closures that read other variables or pointed-to values that all iterations share.
