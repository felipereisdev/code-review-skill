# Rust — Code Review Checklist

> Check sibling modules and crates for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that `rustc`, Clippy or `rustfmt`, as the repository configures them, or a dependency scanner such as `cargo audit` or `cargo deny` that it runs, already reports is not a finding. Read the edition and `rust-version` from `Cargo.toml`, the release profile from `[profile.release]`, and crate versions from `Cargo.toml` and `Cargo.lock`. Apply an item that names a crate, such as Tokio, sqlx or axum, only when the package declares that crate directly; an item that names a version applies only to that version.

## Panics and Errors

- **Panics on external input**: `unwrap()`, `expect()`, indexing (`v[i]`), slicing (`&s[a..b]`, which also panics when a `str` index is not on a character boundary), integer division by zero and `RefCell::borrow_mut()` while a borrow is active all panic. Report one that a value from a request, a file, a message or another process can reach. In a thread or a Tokio task the panic unwinds that thread or task (a spawned task's `JoinHandle` returns an error); with `panic = "abort"` in the profile it ends the whole process. **Not a finding:** a check just before that makes the panic impossible, tests, build scripts, and startup code that is meant to stop on invalid configuration.
- **Integer overflow in release builds**: arithmetic overflow panics in debug builds, but the release profile has `overflow-checks = false` by default, so `+`, `-` and `*` wrap silently there. An `as` cast between integer types truncates or wraps, and from a float to an integer saturates. A length, an offset, a price or a quantity computed from input that way can wrap to a small or negative-looking value and pass a later bounds or balance check. Use `checked_*`, `saturating_*` or `try_from`. **Not a finding:** `overflow-checks = true` in the release profile, which turns the wrap into a panic (still a crash when input can reach it), and values whose range the code already bounds.
- **Errors dropped**: `let _ = writer.flush();`, `.ok();` or `unwrap_or_default()` on the result of a write, a commit, a lock release or a send that later code relies on turns a failure into silent data loss. `#[must_use]` warns about an unused `Result`, but `let _ =` silences it. **Not a finding:** errors that the code cannot act on and that do not change any later state, such as a failed log write.

## Unsafe Code and FFI

- **Unsafe without its invariant**: an `unsafe` block is correct only when the code establishes the conditions that the called function documents: a valid, aligned and live pointer for `*ptr` and `slice::from_raw_parts`, an index in bounds for `get_unchecked`, valid UTF-8 for `str::from_utf8_unchecked`, initialized elements after `Vec::set_len`, and matching layout for `transmute`. Report a changed `unsafe` block whose condition depends on a value the surrounding code does not check, such as an index from input. A wrong `unsafe impl Send` or `unsafe impl Sync` on a type with unsynchronized interior mutability allows data races that the compiler would otherwise reject. **Not a finding:** an `unsafe` block whose `// SAFETY:` comment states a condition that the code visibly establishes.
- **Pointer to a dropped temporary**: `CString::new(name)?.as_ptr()` in one expression drops the `CString` at the end of the statement, so the pointer passed to the C function dangles. Bind the `CString` to a variable that lives until the call returns. The same holds for `as_ptr()` on a temporary `Vec` or `String`.

**Bad** — the `CString` is dropped before `open_device` reads the pointer:

```rust
let path = CString::new(device_name)?.as_ptr();
let fd = unsafe { open_device(path) };
```

**Good** — the `CString` lives until the call returns:

```rust
let path = CString::new(device_name)?;
let fd = unsafe { open_device(path.as_ptr()) };
```

## Async Code (Tokio)

- **Blocking a runtime thread**: `std::thread::sleep`, `std::fs`, a blocking HTTP client (`reqwest::blocking`), a synchronous database driver or a long CPU loop inside an `async fn` blocks the Tokio worker thread that runs it, so every other task scheduled on that thread waits; on a `current_thread` runtime, every task waits. Use the async equivalent (`tokio::time::sleep`, `tokio::fs`) or move the work to `tokio::task::spawn_blocking`. **Not a finding:** a `std::sync::Mutex` locked briefly and never held across an `.await`, which the Tokio documentation recommends over `tokio::sync::Mutex` for short critical sections.
- **Cancellation in `select!`**: when one branch of `tokio::select!` completes, the futures of the other branches are dropped. A branch whose future is not cancellation safe, such as `AsyncReadExt::read_exact` or `read_to_end` on a stream, loses the bytes it had already read when the loop runs `select!` again. The Tokio documentation lists which methods are cancellation safe. The same drop happens to a handler future when `tokio::time::timeout` expires or, in axum and hyper, when the client disconnects, so two writes separated by an `.await` can stop after the first one. **Not a finding:** cancellation-safe futures, such as `mpsc::Receiver::recv` or `TcpListener::accept`, and work moved to a spawned task, which is not cancelled when its handle is dropped.
- **Unbounded queues and spawns**: `mpsc::unbounded_channel()` or one `tokio::spawn` per incoming item without a limit lets memory and task count grow with the input rate when the consumer is slower. Use a bounded channel, a `Semaphore` or a `JoinSet` with a cap. **Not a finding:** a fixed set of producers whose rate the code bounds.

**Bad** — the file read and the sleep block a runtime worker thread:

```rust
async fn reload(path: &Path) -> std::io::Result<Config> {
    let text = std::fs::read_to_string(path)?;
    std::thread::sleep(Duration::from_millis(200));
    Ok(parse(&text))
}
```

**Good** — the async file API and timer yield to other tasks:

```rust
async fn reload(path: &Path) -> std::io::Result<Config> {
    let text = tokio::fs::read_to_string(path).await?;
    tokio::time::sleep(Duration::from_millis(200)).await;
    Ok(parse(&text))
}
```

## Queries and Commands

- **SQL text built from input**: `sqlx::query(&format!("SELECT * FROM users WHERE name = '{name}'"))`, the same with `diesel::sql_query`, or `QueryBuilder::push` with a value from input lets the input change the SQL. Bind the value with `.bind()`, `push_bind` or the `query!` macros. An identifier, such as a column name for `ORDER BY`, cannot be bound: map it from a fixed list.
- **Shell commands built from input**: `Command::new("sh").arg("-c").arg(format!("convert {input} out.png"))` runs the input through a shell. Pass each value as its own `.arg()` to the program itself. A value that starts with `-` can still become an option of that program unless `--` comes first. On Windows, Rust before 1.77.2 did not escape arguments to a `.bat` or `.cmd` file safely (CVE-2024-24576).

**Bad** — the name becomes part of the SQL text:

```rust
let rows = sqlx::query(&format!("SELECT id FROM users WHERE name = '{name}'"))
    .fetch_all(&pool)
    .await?;
```

**Good** — the name is a bound parameter:

```rust
let rows = sqlx::query("SELECT id FROM users WHERE name = $1")
    .bind(&name)
    .fetch_all(&pool)
    .await?;
```

## Conventions, not defects

- `clone()` instead of a borrow, `impl Trait` instead of a generic parameter, the choice between `anyhow` and `thiserror`, and module layout follow the repository's conventions; they are findings only with a measured cost or a broken contract.
- `unwrap()` and `expect()` in tests, examples and build scripts are not findings.
- A Clippy lint that the repository does not enable (for example from `clippy::pedantic`) is a style preference, not a finding.

## Sources

- Integer overflow and `overflow-checks`: https://doc.rust-lang.org/book/ch03-02-data-types.html#integer-overflow, https://doc.rust-lang.org/cargo/reference/profiles.html#overflow-checks; `panic = "abort"`: https://doc.rust-lang.org/cargo/reference/profiles.html#panic; casts: https://doc.rust-lang.org/reference/expressions/operator-expr.html#numeric-cast
- Unsafe code and undefined behavior: https://doc.rust-lang.org/reference/behavior-considered-undefined.html, https://doc.rust-lang.org/nomicon/; `CString::as_ptr`: https://doc.rust-lang.org/std/ffi/struct.CString.html#method.as_ptr
- `Command`: https://doc.rust-lang.org/std/process/struct.Command.html; CVE-2024-24576: https://blog.rust-lang.org/2024/04/09/cve-2024-24576.html
- Tokio blocking, `spawn_blocking` and `Mutex`: https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html, https://docs.rs/tokio/latest/tokio/sync/struct.Mutex.html; `select!` cancellation safety: https://docs.rs/tokio/latest/tokio/macro.select.html#cancellation-safety
- sqlx binding and `QueryBuilder`: https://docs.rs/sqlx/latest/sqlx/fn.query.html, https://docs.rs/sqlx/latest/sqlx/struct.QueryBuilder.html
- axum body limit: https://docs.rs/axum/latest/axum/extract/struct.DefaultBodyLimit.html

## Precedents

- **Safe Rust rejects memory errors and data races**: in code without `unsafe`, the borrow checker and the `Send` and `Sync` bounds reject use-after-free, dangling references and data races at compile time. Do not report a memory-safety bug or a data race in safe code that compiles. **Exception:** `unsafe` blocks and functions, `unsafe impl Send` or `unsafe impl Sync`, FFI calls, unsafe code in a dependency that the change calls in a way its documented safety contract forbids, and logical races (a check and an action under separate lock acquisitions, or across a database and memory), which the compiler does not see.
- **sqlx binds parameters**: `sqlx::query("... WHERE id = $1").bind(id)`, `QueryBuilder::push_bind` and the `query!` and `query_as!` macros send values as bound parameters, never as SQL text. Do not report SQL injection for values passed that way. **Exception:** SQL text built with `format!`, `push_str` or `QueryBuilder::push` from input, and identifiers or sort directions from input, which binding cannot carry.
- **`Command` does not use a shell**: `std::process::Command::new(program).arg(value)` passes each argument to the program without a shell, so shell metacharacters in `value` have no effect. Do not report shell injection for arguments passed that way. **Exception:** a program that is a shell or an interpreter (`sh -c`, `bash -c`, `cmd /C`, `powershell -Command`) given a string built from input, a value that the program reads as an option because it starts with `-` and no `--` comes before it, and `.bat` or `.cmd` files on Windows with Rust before 1.77.2.
- **axum limits request bodies**: since axum 0.6, the `Bytes`, `String`, `Json` and `Form` extractors reject a body larger than 2 MB unless `DefaultBodyLimit` changes the limit. Do not report an unbounded request body for those extractors. **Exception:** `DefaultBodyLimit::disable()` or a raised `DefaultBodyLimit::max`, a body read as a stream (`Body`, `into_data_stream`) without a limit of its own, and other frameworks.
