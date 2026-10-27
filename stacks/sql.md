# SQL — Code Review Checklist

> Check sibling SQL files for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed SQL. A problem that a SQL linter the repository runs, such as SQLFluff or Squawk, already reports is not a finding. This file covers changed `.sql` files: schema migrations, views, functions and procedures, seeds and queries. SQL written inside the code of another language follows that language's stack file, and lock and rollout rules for schema changes come from the DB Migrations category when its trigger matches. Many rules differ between databases: read the dialect from the repository, such as the migration tool's configuration, the database driver in the package manifest, a Compose or CI database image, or syntax the files already use (`SERIAL` or `$$` bodies for PostgreSQL, `AUTO_INCREMENT` for MySQL, `IDENTITY` and `GO` for SQL Server). An item that names a database applies only when that evidence shows it; when the dialect is unknown, report only what holds in every database the evidence leaves open.

## Correctness

- **Comparisons with `NULL`**: `col = NULL` and `col <> NULL` are never true; use `IS NULL` and `IS NOT NULL`. `NOT IN (SELECT ...)` returns no rows at all when the subquery returns a `NULL`, so a filter such as "customers not in the blocked list" silently matches nobody. Use `NOT EXISTS`, or exclude `NULL` in the subquery.
- **Writes without the intended filter**: an `UPDATE` or `DELETE` without a `WHERE`, or with one that a join or a missing parenthesis around `OR` widens, changes every matching row. In PostgreSQL, `UPDATE ... FROM` with a join that matches several source rows for one target row updates it with one of them, and which one is not predictable.
- **Order without a unique key**: `LIMIT` or `OFFSET` without an `ORDER BY`, or with an `ORDER BY` on a column that is not unique, returns rows in an order that the database may change between executions, so pages repeat or skip rows. Add a unique column, such as the primary key, as the last sort key.
- **Integer division and truncation**: in PostgreSQL and SQL Server, dividing two integers truncates (`3 / 4` is `0`), so a ratio or percentage computed that way is wrong; MySQL's `/` returns a decimal. Cast one side first. In MySQL without strict mode, an `INSERT` of a too-long string or an out-of-range number stores a truncated or clipped value with only a warning; strict mode (`STRICT_TRANS_TABLES`, the default since MySQL 5.7) rejects it.
- **Time zones and ranges**: PostgreSQL `timestamp` (without time zone) stores the wall-clock value and drops the zone, while `timestamptz` stores an instant; mixing them shifts times by the session's zone. MySQL `TIMESTAMP` stores UTC and only covers 1970 to 2038-01-19, while `DATETIME` stores the value as given.
- **Case-insensitive comparisons**: MySQL's default collations are case-insensitive, so a `UNIQUE` index treats `Ann@Example.com` and `ann@example.com` as the same value and `WHERE token = ?` matches tokens that differ only in case; PostgreSQL compares case-sensitively by default.

**Bad** — one `NULL` in `blocked.customer_id` makes the query return no rows:

```sql
SELECT id FROM customers
WHERE id NOT IN (SELECT customer_id FROM blocked);
```

**Good** — `NOT EXISTS` is not affected by `NULL` values:

```sql
SELECT c.id FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM blocked b WHERE b.customer_id = c.id);
```

## Schema and Constraints

- **Uniqueness checked only by the application**: a "check that it does not exist, then insert" sequence without a `UNIQUE` constraint lets two concurrent requests insert duplicates. Add the constraint and handle the conflict (`ON CONFLICT` in PostgreSQL and SQLite, `ON DUPLICATE KEY` in MySQL, `MERGE` with a lock hint in SQL Server).
- **`UNIQUE` and `NULL`**: PostgreSQL, MySQL and SQLite allow many `NULL` values in a `UNIQUE` column (PostgreSQL 15 adds `NULLS NOT DISTINCT`), while SQL Server allows one. A uniqueness rule that the code expects to cover rows with a `NULL` column does not hold in the first three.
- **Foreign keys without an index**: PostgreSQL does not create an index on the referencing columns of a foreign key, so deleting or updating a parent row scans the child table and holds locks during the scan. MySQL InnoDB creates that index itself.
- **Constraints that are ignored**: MySQL before 8.0.16 parses `CHECK` constraints but does not enforce them. Report a change that relies on a `CHECK` on such a version.
- **Key types that run out**: an `INT` or `SERIAL` primary key stops at 2,147,483,647, after which inserts fail. Report it for a table that the repository describes as high-volume, such as events or logs.

## Security and Privileges

- **Dynamic SQL from parameters**: in a function or procedure, `EXECUTE 'SELECT ... ' || p_name` (PL/pgSQL), `EXEC('...' + @name)` (T-SQL) or `PREPARE` from `CONCAT` (MySQL) puts the parameter into the SQL text, so the caller can change the statement. Pass values with `EXECUTE ... USING`, `sp_executesql` parameters or `EXECUTE ... USING` in MySQL, and quote identifiers with `format('%I', ...)` or `QUOTENAME`.
- **`SECURITY DEFINER` without a fixed `search_path`**: a PostgreSQL function declared `SECURITY DEFINER` runs with its owner's privileges and resolves unqualified names through the caller's `search_path`, so a caller who can create objects in a schema that comes earlier can run their own code as the owner. Add `SET search_path = ...` to the function, listing only trusted schemas with `pg_temp` last, or qualify every name.
- **Grants wider than needed**: `GRANT ALL`, grants `TO PUBLIC`, and `CREATE` on a shared schema give every role those rights. PostgreSQL 15 removed the default `CREATE` privilege of `PUBLIC` on the `public` schema; a migration that grants it back reopens it.
- **Real credentials in seeds**: a seed or fixture file with a real password hash, API key or production email exposes it to everyone who can read the repository.

**Bad** — the parameter is part of the SQL text:

```sql
CREATE FUNCTION count_rows(p_table text) RETURNS bigint AS $$
DECLARE n bigint;
BEGIN
  EXECUTE 'SELECT count(*) FROM ' || p_table INTO n;
  RETURN n;
END;
$$ LANGUAGE plpgsql;
```

**Good** — the identifier is quoted with `%I`, and only allowed tables are accepted:

```sql
CREATE FUNCTION count_rows(p_table text) RETURNS bigint AS $$
DECLARE n bigint;
BEGIN
  IF p_table NOT IN ('orders', 'invoices') THEN
    RAISE EXCEPTION 'table % is not allowed', p_table;
  END IF;
  EXECUTE format('SELECT count(*) FROM %I', p_table) INTO n;
  RETURN n;
END;
$$ LANGUAGE plpgsql;
```

## Performance

- **Predicates that cannot use an index**: a function or cast on an indexed column (`WHERE lower(email) = $1`, `WHERE created_at::date = $1`), a leading wildcard (`LIKE '%term'`) or a comparison with a value of another type (a MySQL `VARCHAR` column compared with a number) makes the database scan the table instead of using the index. Add an expression index or compare the column as stored. **Not a finding:** small tables, and an expression index that matches the predicate.
- **`SELECT *` in views**: PostgreSQL and MySQL expand `*` when the view is created, so the view does not pick up columns added later. Report a view that the change creates with `*` when the code expects later columns to appear.

## Conventions, not defects

- Upper or lower case keywords, identifier quoting style, CTEs versus subqueries, and file naming follow the repository's conventions.
- Missing indexes on columns that no changed query filters or joins on, and normalization choices, are design opinions, findings only with a concrete query that the change makes slow or wrong.

## Sources

- PostgreSQL: comparisons and `NOT IN` (https://www.postgresql.org/docs/current/functions-comparison.html, https://www.postgresql.org/docs/current/functions-subquery.html), `UPDATE ... FROM` (https://www.postgresql.org/docs/current/sql-update.html), `LIMIT` and order (https://www.postgresql.org/docs/current/queries-limit.html), date and time types (https://www.postgresql.org/docs/current/datatype-datetime.html), unique indexes and `NULLS NOT DISTINCT` (https://www.postgresql.org/docs/current/indexes-unique.html), foreign keys (https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- PostgreSQL: dynamic SQL in PL/pgSQL (https://www.postgresql.org/docs/current/plpgsql-statements.html#PLPGSQL-STATEMENTS-EXECUTING-DYN), `SECURITY DEFINER` (https://www.postgresql.org/docs/current/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY), row security (https://www.postgresql.org/docs/current/ddl-rowsecurity.html), views (https://www.postgresql.org/docs/current/sql-createview.html), PostgreSQL 15 release notes (https://www.postgresql.org/docs/release/15.0/), transactional DDL and errors in transactions (https://www.postgresql.org/docs/current/tutorial-transactions.html)
- MySQL: `TIMESTAMP` and `DATETIME` (https://dev.mysql.com/doc/refman/8.4/en/datetime.html), strict mode (https://dev.mysql.com/doc/refman/8.4/en/sql-mode.html), `CHECK` constraints (https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html), foreign keys (https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html), default collations (https://dev.mysql.com/doc/refman/8.4/en/charset-server.html), collation names and `_ci` (https://dev.mysql.com/doc/refman/8.4/en/charset-collation-names.html), implicit commits (https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html), prepared statements (https://dev.mysql.com/doc/refman/8.4/en/sql-prepared-statements.html, https://dev.mysql.com/doc/refman/8.4/en/execute.html)
- SQL Server: `sp_executesql` (https://learn.microsoft.com/en-us/sql/relational-databases/system-stored-procedures/sp-executesql-transact-sql), unique constraints (https://learn.microsoft.com/en-us/sql/relational-databases/tables/create-unique-constraints), division (https://learn.microsoft.com/en-us/sql/t-sql/language-elements/divide-transact-sql)

## Precedents

- **Bound parameters are never SQL text**: values passed as bound parameters (`$1`, `?`, `:name`, `@p1`), or through `EXECUTE ... USING` and `sp_executesql` parameters, are never parsed as SQL. Do not report SQL injection for such values. **Exception:** identifiers, keywords or sort directions concatenated into the statement, dynamic SQL built by concatenation inside a function or procedure even when the caller passed it a parameter, and `LIKE` patterns, where `%` and `_` in the value still change what matches.
- **One statement applies to all its rows or to none**: a single `INSERT`, `UPDATE` or `DELETE` is atomic, so an error in it leaves no row of that statement changed. Do not report a partial update within one statement. **Exception:** MySQL tables on a non-transactional engine such as MyISAM, MySQL without strict mode, where invalid values are adjusted with a warning instead of failing, scripts of several statements without an explicit transaction, where an error leaves the earlier statements applied, and DDL that commits implicitly, as in MySQL.
- **Row-level security denies by default**: in PostgreSQL, a table with `ENABLE ROW LEVEL SECURITY` and no policy that applies to a role returns no rows to that role and rejects its writes. Do not report rows exposed to a role that no policy grants. **Exception:** the table owner, which bypasses row security unless `FORCE ROW LEVEL SECURITY` is set, superusers and roles with `BYPASSRLS`, permissive policies, which combine with `OR` and can widen access, views, which check row security as their owner unless created with `security_invoker` (PostgreSQL 15+), `SECURITY DEFINER` functions, and other databases.
