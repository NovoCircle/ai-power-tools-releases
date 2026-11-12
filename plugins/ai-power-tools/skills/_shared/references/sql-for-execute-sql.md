# Writing `execute_sql` queries

Read this before you send SQL to `execute_sql`. A statement EA cannot run does not come back as an
error: EA shows a blocking dialog that the server cannot dismiss, and the session waits until
someone clicks OK. Server 3.6.5 or later refuses the common mistakes before EA sees them; this page
says what to write so you are not refused, and what the check does not catch.

## The rules

1. **Know the dialect.** On a `.qea` file the dialect is SQLite: use `LENGTH`, `IFNULL` (or
   `COALESCE`), `datetime('now')` and `LIMIT n`. `LEN`, `ISNULL`, `GETDATE`, `DATALENGTH` and `TOP n`
   are refused with `sql_prepare_failed`, with SQLite's message and the SQLite spelling. On a SQL
   Server repository the opposite holds: `TOP n`, `LEN`, `ISNULL`. Check the repository type with
   `get_repository_info` before you write a query that depends on it.
2. **Text takes single quotes.** `WHERE Stereotype = 'WBAVendorSystem'`. Double-quoted text is read
   as a column name, so `WHERE Stereotype = "WBAVendorSystem"` asks for a column that does not
   exist. Double an embedded single quote: `'Customer''s data'`.
3. **Bracket reserved words.** A column that is also an SQL word has to be written in square
   brackets: `[Default]`, `[Constraint]`, `[Value]`, `[Type]`, `[Status]`, `[Key]`, `[Order]`,
   `[Position]`, `[Path]`, `[Const]`, `[Scope]`. `a.Default` is a syntax error; `a.[Default]` is
   right. `describe_table` lists each table's reserved columns in `reserved_word_columns`.
4. **Qualify a column two tables share.** `Package_ID` is on both `t_object` and `t_package`, so a
   join that writes bare `Package_ID` is ambiguous. Alias each table and write `o.Package_ID`.
5. **Use the real column names.** Do not guess them; call `describe_table` first. Two that are
   guessed wrongly more than any others: `t_connectortag` holds the connector id in `ElementID`
   (not `ConnectorID`) and the value in `VALUE`; `t_xref` has `Client`, `Supplier`, `Type`,
   `Description` and `Behavior`, and `Type` and `Constraint` need brackets. The connector key on
   `t_connector` is `Connector_ID`.
6. **Give every calculated column a name with `AS`.** `COUNT(*) AS n`, `SUM(x) AS total`,
   `a || b AS label`, `1 AS one`. A count, a sum, a concatenation, a literal and a subquery in the
   select list all need one. Without it the call is refused with `unaliased_expression`, naming the
   column, because EA uses the column name as an XML element name and cannot name an expression. An
   alias that is not a valid XML name (letters, digits and underscores, not starting with a digit;
   `AS [My Col]` fails) is refused with `invalid_column_alias`. A plain column, `alias.column` and
   `*` need no alias.

```sql
SELECT Stereotype, Connector_Type, COUNT(*) AS n
FROM t_connector
GROUP BY Stereotype, Connector_Type
```

## What the server checks, and what it does not

`execute_sql` runs three checks before EA sees the statement:

| Check | Refusal | Notes |
|---|---|---|
| Column names against the EA schema | `invalid_column`, with `did_you_mean` | Qualified `alias.column` references on any query; bare names only when the query names one EA table. Nothing here checks quoting, so rule 2 is yours to follow. |
| The select list | `unaliased_expression`, `invalid_column_alias` | Reads the outermost `SELECT` only (the first one of a `UNION`). A subquery's own select list is not checked. |
| SQLite prepare, on a `.qea` only | `sql_prepare_failed`, with `detail` | The statement is prepared against the model file, read-only; EA is not disturbed. This is what catches `TOP n`, `LEN(`, an unbracketed `a.Default` and an ambiguous `Package_ID`. It does not reliably catch double-quoted text, which SQLite may accept as a string. |

The SQLite check does not run on an encrypted `.qeax`, on a locked or unreadable file, on a
repository that is not a `.qea`, or on more than one statement; the statement then goes to EA
unchecked, so the rules above are all you have. `skip_validation=True` bypasses the three checks;
use it only for dialect-specific SQL you have read twice. It never bypasses the write gate:
`allow_writes=False` refuses any non-`SELECT` statement with `write_blocked`, and `execute_sql`
accepts `INSERT`, `UPDATE` and `DELETE` by default, so ask before you write.

If a call is refused, fix the statement from the message; do not retry it with `skip_validation`.
