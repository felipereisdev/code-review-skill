# Python / Django / FastAPI / Flask — Code Review Checklist

> Check sibling modules for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that a type checker (mypy, pyright) or a linter (Ruff, Flake8, Pylint) configured in the repository already reports is not a finding. Apply a framework section only when the package declares that framework; the other sections apply to all Python code. An item that depends on a version names the Python or package version that it needs.

## Language Pitfalls

- **Mutable default arguments**: a default such as `[]`, `{}` or `set()` is created once, when the `def` statement runs, so every call that mutates it changes the same object, and data from one call or request appears in the next. Default to `None` and create the object in the body. **Not a finding:** a mutable default that the function never mutates, stores or returns, and `dataclasses.field(default_factory=list)`.
- **Late-binding closures**: a `lambda` or nested function created in a loop reads the loop variable when it runs, not when it is created, so every callback sees the last value. Bind it as a default argument (`lambda item=item: ...`) or with `functools.partial`.
- **Over-broad `except`**: a bare `except:` or `except BaseException:` also catches `KeyboardInterrupt`, `SystemExit` and, since Python 3.8, `asyncio.CancelledError`, so a cancelled task or a shutdown keeps running. An `except Exception:` that only logs, or passes, on a path whose failure must stop the operation reports success after a failed write. **Not a finding:** a handler that logs and re-raises, and a top-level worker loop that logs a failed job and moves on to the next by design.
- **Naive and aware datetimes**: ordering a naive `datetime` (`datetime.now()`, `datetime.utcnow()`) against an aware one with `<` or `>`, or subtracting one from the other, raises `TypeError`, whereas `==` returns `False` without an error, so a check written as `==` fails silently instead of crashing. With Django's `USE_TZ = True`, model datetimes are aware, so use `django.utils.timezone.now()`. `datetime.utcnow()` returns a naive value that most APIs read as local time, and it is deprecated since Python 3.12.

**Bad** — the list is shared by every call that omits `tags`:

```python
def add_tag(tag, tags=[]):
    tags.append(tag)
    return tags
```

**Good** — each call that omits `tags` gets a new list:

```python
def add_tag(tag, tags=None):
    if tags is None:
        tags = []
    tags.append(tag)
    return tags
```

## Async Code

- **Blocking calls in `async def`**: `requests`, `time.sleep`, a synchronous database driver or a large file read inside an `async def` stops the event loop, so every other request on that worker waits. Use an async client, or `await asyncio.to_thread(...)` (Python 3.9+). **Not a finding:** the same call in a FastAPI path operation or dependency declared with plain `def`, which FastAPI runs in a thread pool, and blocking calls during startup.
- **Coroutines never awaited**: calling an `async def` function without `await` only creates a coroutine object, so the work never happens (Python warns `coroutine ... was never awaited`).
- **Unreferenced tasks**: the event loop keeps only weak references to tasks, so a task from `asyncio.create_task(...)` whose result is not stored can be garbage-collected before it finishes, and its exception is never seen. **Not a finding:** tasks that are awaited, kept in a collection until they finish, or created in an `asyncio.TaskGroup` (Python 3.11+).

**Bad** — a blocking HTTP call inside `async def` stalls every request on the worker:

```python
@app.get("/rates")
async def rates():
    resp = requests.get(RATES_URL, timeout=5)
    return resp.json()
```

**Good** — with plain `def`, FastAPI runs the blocking call in its thread pool:

```python
@app.get("/rates")
def rates():
    resp = requests.get(RATES_URL, timeout=5)
    return resp.json()
```

## Django

- **Queries in loops**: reading a foreign key or a reverse relation for each row of a queryset, in Python or in a template loop, runs one query per row. Use `select_related()` for foreign keys and one-to-one relations, and `prefetch_related()` for many-to-many and reverse relations. **Not a finding:** a loop over a small set whose size the code bounds.
- **Lost updates**: `account.balance -= amount` followed by `account.save()` from two concurrent requests keeps only one change. Use an `F()` expression (`Account.objects.filter(pk=pk).update(balance=F("balance") - amount)`), or `select_for_update()` inside `transaction.atomic()`.
- **Side effects inside transactions**: an email, a queued task or an external call made inside `transaction.atomic()`, or anywhere in a view when `ATOMIC_REQUESTS = True`, happens even when the transaction rolls back, and a task queued there can run before the commit and not find its row. Use `transaction.on_commit()`.
- **Bulk operations skip model logic**: `QuerySet.update()`, `bulk_create()` and `bulk_update()` do not call `save()` or send the `pre_save` and `post_save` signals, and `update()` does not set `auto_now` fields. A change that replaces a `save()` loop with them silently drops that logic.
- **Object-level access**: `get_object_or_404(Invoice, pk=pk)` in a view that serves a user's own data, with no filter on `request.user` and no permission check, lets any signed-in user read or change another user's record by changing the id. In Django REST Framework, `has_object_permission()` runs only when the view calls `get_object()`; list views need a `get_queryset()` filtered to the user.
- **Production settings**: `DEBUG = True` in the settings that production uses shows tracebacks and configuration to visitors, and a `SECRET_KEY` committed to the repository lets anyone who reads it forge signed values such as password reset tokens.
- **Missing migrations**: a model change that leaves a schema difference no migration applies fails at run time only when a query or write meets the difference, and only in the way the old schema rejects it. A table or column that the model expects but the database lacks (a new table, an added field, or the new name of a renamed field) fails with a missing-table or missing-column error when a query or write names it. An unapplied field removal leaves its column in place, so a query that names the column can still succeed. An insert that omits a retained nullable column can succeed too, while a retained `NOT NULL` column that the insert does not fill can fail a constraint instead. A changed column type or length also leaves the column in place, so it fails only where the backend enforces the old type or length: an unapplied `CharField(max_length=32)` changed to 64 stores a 40-character value without error on SQLite, which does not enforce `VARCHAR(n)` length, but on PostgreSQL the same write fails with `value too long for type character varying(32)`. Name the particular operation or value that the old schema rejects. A change to migration state only, such as a field's `help_text`, `verbose_name` or `validators`, changes no column, so a missing migration for it does not fail a query. **Not a finding:** when CI runs `makemigrations --check`.

## FastAPI and Flask

- **Response fields**: a path operation that returns an ORM object or a dict with no `response_model` and no return type annotation serializes every field it holds, such as `password_hash`. FastAPI filters the output through the declared response model.
- **Missing auth dependency**: a route added without the dependency that its sibling routes use for authentication, such as `Depends(get_current_user)`, is public. **Not a finding:** a route on a router or app created with `dependencies=[...]`, which applies them to every route that it includes.
- **Flask debug mode**: `app.run(debug=True)`, `FLASK_DEBUG=1` or `flask run --debug` in a deployed configuration exposes the Werkzeug debugger, which runs arbitrary Python code from the browser.
- **Files from user paths**: `send_file(os.path.join(UPLOADS, name))` with a user-controlled `name` can serve any file; `send_from_directory(UPLOADS, name)` refuses paths outside that directory.

## Security

- **Shell commands**: `subprocess` calls with `shell=True`, `os.system()` and `os.popen()` pass a command line to a shell, so input in it can run other commands. **Not a finding:** an argument list without `shell=True`, which reaches the program as separate arguments (input that picks the program, or that starts with `-`, still needs a check).
- **Unsafe deserialization**: `pickle.loads()` and `shelve` on data from a request, a queue or a shared cache can run code; so can `yaml.load()` with `yaml.Loader` or `yaml.UnsafeLoader`, and `yaml.load(data)` without a `Loader` on PyYAML before 5.1. `yaml.safe_load()` and `json` build only plain data.
- **Paths from input**: `os.path.join(base, name)` returns `name` when it is absolute and keeps `..`, so it does not keep the result inside `base`. Resolve with `os.path.realpath()` and check `os.path.commonpath([base, resolved]) == base`.
- **Outbound HTTP timeouts**: `requests` has no default timeout, so a call without `timeout=` to a server that never answers hangs the worker. **Not a finding:** `httpx`, which applies a five-second default timeout.

## Conventions, not defects

- Type hints and a passing type checker are tooling: a missing annotation is never a finding by itself.
- The settings library (`django-environ`, `python-decouple`, Pydantic `BaseSettings`) is the team's choice; a finding needs a committed secret or a setting that silently falls back to an unsafe value.
- Pydantic models or DRF serializers instead of dict access, and raw SQL, are findings only when unvalidated input reaches something that needs the validation, such as a query, a privileged attribute or a file path; the precedents below say when the framework already covers it.

## Sources

- Default argument values: https://docs.python.org/3/reference/compound_stmts.html#function-definitions
- Late-binding lambdas: https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result
- `CancelledError`, `create_task`, `TaskGroup`, `to_thread`: https://docs.python.org/3/library/asyncio-exceptions.html, https://docs.python.org/3/library/asyncio-task.html
- Blocking code in asyncio: https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code
- `datetime.utcnow()`: https://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow
- `dataclasses` mutable defaults: https://docs.python.org/3/library/dataclasses.html#mutable-default-values
- FastAPI `def` and `async def`, response models, router dependencies: https://fastapi.tiangolo.com/async/, https://fastapi.tiangolo.com/tutorial/response-model/, https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Django querysets (`select_related`, `prefetch_related`, `update()`, bulk methods, `select_for_update()`): https://docs.djangoproject.com/en/stable/ref/models/querysets/
- `F()` expressions: https://docs.djangoproject.com/en/stable/ref/models/expressions/#f-expressions
- Transactions and `on_commit()`: https://docs.djangoproject.com/en/stable/topics/db/transactions/
- `auto_now`: https://docs.djangoproject.com/en/stable/ref/models/fields/#datefield
- Time zones: https://docs.djangoproject.com/en/stable/topics/i18n/timezones/
- `DEBUG` and `SECRET_KEY`: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/, https://docs.djangoproject.com/en/stable/ref/settings/#secret-key
- `makemigrations --check`: https://docs.djangoproject.com/en/stable/ref/django-admin/#makemigrations
- Django REST Framework object permissions: https://www.django-rest-framework.org/api-guide/permissions/
- Flask debugger and `send_from_directory`: https://flask.palletsprojects.com/en/stable/debugging/, https://flask.palletsprojects.com/en/stable/api/#flask.send_from_directory
- `subprocess` security: https://docs.python.org/3/library/subprocess.html#security-considerations
- `pickle`: https://docs.python.org/3/library/pickle.html; PyYAML `load`: https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
- `os.path.join`: https://docs.python.org/3/library/os.path.html#os.path.join
- Timeouts: https://requests.readthedocs.io/en/latest/user/advanced/#timeouts, https://www.python-httpx.org/advanced/timeouts/

## Precedents

- **ORMs and DB-API parameters bind values**: Django ORM filters, SQLAlchemy query expressions and `cursor.execute(sql, params)` send values as query parameters. Do not report SQL injection for values passed that way. **Exception:** Django `raw()`, `extra()` and `RawSQL()` or SQLAlchemy `text()` with formatted strings, and SQL text built with f-strings, `%` or `.format()` before it reaches `execute()`.
- **Django and Flask templates autoescape**: Django templates, and Flask's Jinja2 templates named `.html`, `.htm`, `.xml` or `.xhtml` (or `.svg` from Flask 2.2 on) and Flask strings rendered with `render_template_string()` escape ordinary untrusted string values rendered with `{{ value }}` while autoescaping is on, which is the default for both. That makes them safe in HTML text and in quoted, non-executable attribute values. Do not report XSS for such string values rendered that way. **Exception:** the `|safe` filter, `mark_safe()`, `Markup()`, Flask/Jinja objects implementing `__html__()`, including custom or helper-produced ones, whose result MarkupSafe treats as trusted HTML without escaping, so the code that produces it must establish its safety, `{% autoescape off %}`, an app or engine with autoescaping disabled (`app.jinja_env.autoescape = False`, or Django `Engine(autoescape=False)`), Flask templates with other extensions such as `.txt` or `.j2`, a bare `jinja2.Environment()`, which does not autoescape by default, user-controlled URLs in `href`, `src` or `action`, where escaping does not stop a `javascript:` URL, unquoted attribute values (`<input value={{ value }}>`), where a space starts a new attribute such as `onmouseover`, and values inside `<script>` blocks, which need `json_script` or `|tojson` instead, and values inside event-handler attributes, which should be read from `data-` attributes by a listener, because raw `|tojson` output ends a double-quoted attribute (`|tojson|forceescape` escapes it there).
- **Django checks CSRF tokens on unsafe methods**: `CsrfViewMiddleware`, on by default, rejects requests with any method other than `GET`, `HEAD`, `OPTIONS` or `TRACE` that lack a valid token, and it does not check those four safe methods. Do not report missing CSRF protection on an unsafe-method Django view that the middleware covers. **Exception:** views decorated with `@csrf_exempt`, projects that removed the middleware from `MIDDLEWARE`, Django REST Framework views, which enforce CSRF only with `SessionAuthentication`, and views that change state on `GET`, `HEAD`, `OPTIONS` or `TRACE`, which the middleware never checks.
- **FastAPI validates typed parameters**: path, query and body parameters declared with Pydantic models or type annotations are validated before the handler runs, and invalid input gets a 422 response. Do not report missing type validation for them. **Exception:** parameters typed as `dict` or `Any`, bodies read from the raw `Request`, constraints the type does not state, such as ranges, lengths or formats not declared with `Field()` or `Annotated`, and validators that replace or skip the declared type's checks, such as `PlainValidator`, `@field_validator(..., mode='plain')`, `SkipValidation` or a wrap validator that does not call its handler.
