# psql.exe

## Contract

Use `psql.exe` via the provided skill to connect target database on local machine by using following command:

```powershell
psql -d appdb
```

## What psql is

`psql` is PostgreSQL’s interactive terminal client.

- Supports interactive SQL (REPL) and non-interactive/batch execution.
- Supports psql-specific meta-commands (backslash commands) for navigation, introspection, formatting, and scripting.

## Running SQL

- Interactive: type SQL and terminate with `;`.
- One-off command:
    - `psql -c "<SQL>"`
- Execute a script file:
    - `psql -f <script.sql>`
- In-session file execution:
    - `\i <file.sql>`

## Introspection and navigation (meta-commands)

Common object discovery/inspection:

- `\l` list databases
- `\c <db>` connect to another database
- `\dn` list schemas
- `\dt` list tables
- `\dv` list views
- `\dm` list materialized views
- `\di` list indexes
- `\df` list functions/procedures
- `\d <name>` describe an object (table/view/index/etc.)
- `\d+ <name>` extended description

Help:

- `\?` psql meta-command help
- `\h <SQL_COMMAND>` SQL syntax help

## Output formatting and export

- Toggle aligned/unaligned output:
    - `\a`
- Expanded/vertical output:
    - `\x [on|off|auto]`
- Configure formatting with `\pset`:
    - formats include `aligned`, `csv`, `tsv`, `html`, etc.
- Redirect query output:
    - `\o <file>` send all output to a file
    - `\o` reset back to terminal

Client-side data import/export:

- `\copy` exports/imports via the client (works when server cannot access local filesystem).
    - Export query result to CSV:
        - `\copy (SELECT ...) TO '<path>' WITH (FORMAT CSV, HEADER)`

## Scripting, variables, and automation

- Pass variables from CLI:
    - `psql -v key=value -f script.sql`
- Use variable substitution in SQL scripts:
    - `:var` forms are supported.
- Useful in script execution:
    - `\set`, `\unset`, `\echo`, `\prompt`
- Write/edit query buffers:
    - `\e` open editor
    - `\w <file>` write current buffer

## Transactions

- Standard SQL transaction control:
    - `BEGIN`, `COMMIT`, `ROLLBACK`
- Supports savepoints:
    - `SAVEPOINT`, `ROLLBACK TO SAVEPOINT`, `RELEASE SAVEPOINT`

## Performance and debugging (high-level)

- Execution plans:
    - `EXPLAIN`, `EXPLAIN ANALYZE`
    - Optional detailed options: `BUFFERS`, `VERBOSE`, and JSON-format output.
- Timing in psql:
    - `\timing ON|OFF`
- Log query output in batch mode:
    - `psql -L <logfile> -f script.sql`

## Backup/restore tooling commonly used alongside psql

- `pg_dump` and `pg_restore` are the primary backup/restore tools.
    - psql is often used to restore plain SQL dumps:
        - `psql -f backup.sql -d <db>`

## Security and operational notes

- Prefer `.pgpass` or a password prompt over embedding credentials in scripts.
- Use SSL/TLS settings (`sslmode`) for remote connections when appropriate.
- `\copy` is often safer than server-side `COPY` for file access permissions.
