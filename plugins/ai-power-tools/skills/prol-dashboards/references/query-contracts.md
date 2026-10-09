# Query contracts, by family

Detail supporting [`../SKILL.md`](../SKILL.md) §3. Read that section first — it carries the
decisions; this file carries the column sets and the dialect rules.

Verified against Prolaborate 5.6.1.40 on a MySQL-backed repository. Examples use the Westbrook Bank
model; see [`../../_shared/references/westbrook-example.md`](../../_shared/references/westbrook-example.md).

---

## 1. Get the contract from the product, not from memory

Step 2 of the chart wizard has a **`VIEW SAMPLE`** button, reachable through `Skip to Query` with
nothing configured at all. It opens *Configure EA Charts : Sample Query* for **the selected chart
type**, containing the prose contract and a complete generated query **in both MSSQL and MySQL**.

**No data and no source selection are required**, so it works on an empty scope and on chart types
the repository cannot populate.

> **Where the sample's prose disagrees with its generated SQL, trust the SQL.** Tested twice,
> wrong twice: one chart type's prose named a mandatory alias that neither generated query
> contained, and another stated a date format that was reversed. Treat the prose as a hint.

Use the designer path only to learn **how a particular designer field maps to a column** — then read
the generated SQL and keep it as the template.

## 2. The five families

### Axial — Pie, Donut, Bar, Column, Stacked Bar, Stacked Column

```sql
select o.Name,
       o.ea_guid       AS Classguid,     -- identity; drives click-through
       o.Object_Type   AS BaseType,
       o.Stereotype    AS Stereotype,
       <expr>          AS series         -- the slice, bar or color
       [, <expr>       AS GroupName ]    -- optional second dimension
from t_object o ...
```

**The chart aggregates; the query does not.** Return one row per element (or per relationship pair)
and Prolaborate groups by `series` and counts rows. Never write a top-level `GROUP BY`.

> **With `GroupName` present, `GroupName` is the axis category and `series` is the color.** This is
> the reverse of what the designer labels imply — `Y-Axis` compiles to `series`. Verified twice
> independently.

Bar and Stacked Bar generate **byte-identical SQL**; so do Column and Stacked Column. The second
dimension is a designer field, not a property of the chart type, and the pairs differ only in
rendering — clustered versus stacked.

### Level-numbered — Landscape, Nested Pie, Heat Map, Integration Map

```sql
select distinct
       o.Object_ID   AS objectid1,
       o.Name        AS displayname1,
       o.ea_guid     AS classguid,
       o.Object_Type AS basetype1,
       o.Stereotype  AS stereotype1,
       <expr>        AS groupname,       -- optional grouping
       <expr>        AS displaylabel,    -- REQUIRED
       <expr>        AS series,          -- optional color
       ''            AS connstartid1,
       ''            AS connendid1
from t_object o ...
```

Note the casing difference between families: **`GroupName` in the axial family, lower-case
`groupname` here.** Integration Map adds `conType` and `conStereotype`.

A Landscape that nests through connectors needs the connector direction right. In the model used for
verification, the hierarchy connector's **Start was the child and End the parent**, so descending
meant `Target To Source`. **Derive this from a row count rather than assuming it** — the count of
parent-child connectors should equal (elements − roots).

### Scatter — Bubble

```sql
select o.Name, o.ea_guid AS Classguid, o.Object_Type AS BaseType, o.Stereotype AS Stereotype,
       <expr> AS xvalue,
       <expr> AS yvalue,
       <expr> AS series,
       <expr> AS chartvalue      -- only when sized by Sum
from t_object o ...
```

**Size is `chartvalue` summed per `series`.** Without it, size is the row count per `series`.

> **Bubble's axes must be numeric, and the designer cannot supply them.** It accepts a text property
> without complaint and produces a chart with hundreds of series and one visible bubble. **A real
> Bubble needs hand-written SQL or numeric tagged values** — the one chart type where the designer
> path is actively a trap.

### Timeline — Road Map

```sql
select o.Object_ID AS objectid, o.Name AS displayname,     -- note: NO trailing 1
       o.ea_guid AS Classguid, o.Object_Type AS BaseType, o.Stereotype AS Stereotype,
       <expr> AS starttime,      -- strings; no CAST is applied
       <expr> AS endtime,
       <expr> AS groupname,
       <expr> AS series
from t_object o ...
```

Dates arrive as **strings** and are parsed client-side.

> **A hand-written Road Map must emit `MM-dd-yyyy`.** The product's own sample says `dd-mm-yyyy` and
> is wrong. With the wrong order only rows whose day-of-month is 12 or less draw at all — which
> looks like sparse data, not a bug.

> **Duplicate `groupname` values collapse.** One bar survives per distinct `groupname`, not one per
> row. `groupname` is a key, not a lane.

From the designer, start and end dates can **only** come from tagged values. `CreatedDate` and
`ModifiedDate` are offered for color and grouping but never for the axis.

### Single value — Cards

```sql
select count(*) as cards from t_object where ...
```

**The result column must be aliased `cards`.** That alias is the whole contract. A card is exactly
one number — anything else (a ratio, a percentage, a rollup) needs the query path, reached through
`Skip to Query`.

Percentages: use `Symbol: Percentage` and `Prefix/Suffix: Suffix` in the presentation step. **Do not
put a `%` in the SQL** — the widget appends it, and a text result breaks the card.

### Tabular — Reports

The axial family **minus `series`**. Every aliased column renders as a column, in `SELECT` order,
headed by the alias text, except:

- `classguid` — consumed, not displayed;
- any alias prefixed `hide_` — carried but hidden.

The row hyperlink and element icon require the display column to be aliased exactly `Name`, plus
`classguid`, `basetype` and `stereotype`.

## 3. SQL dialect is a property of the repository

Prolaborate executes your SQL on the **underlying EA repository database**, and one instance can
front several repositories on **different engines** — MySQL, MariaDB, SQL Server, PostgreSQL,
SQLite. **The syntax is repository-specific.**

> **Establish the dialect per repository before writing any query.** Build one chart through the
> designer and read the generated SQL, or read `VIEW SAMPLE`, which prints two dialects side by
> side. Markers: `elt()` and `@rownum :=` mean MySQL or MariaDB; `TOP`, `ISNULL` and bracketed
> identifiers mean SQL Server.

**A dialect error is reported as `No results found`** — indistinguishable from a legitimately empty
result. There is no error message.

| Need | MySQL / MariaDB | SQL Server |
|---|---|---|
| Limit rows | `LIMIT n` | `TOP n` or `OFFSET … FETCH` |
| Cast to integer | `CAST(x AS SIGNED)` | `CAST(x AS INT)` |

### There is exactly one real restriction

A query that does not begin with `SELECT` is refused outright, with an explicit message about
non-SELECT statements. **No CTEs, no temp tables, no procedures.** Recursion must be unrolled into
`UNION` branches, one per level of depth.

Everything else that appears blocked is a dialect mismatch, not a guard.

## 4. Top-N — use `ROW_NUMBER()`

MySQL and SQL Server are the two engines seen most often and they share **no** row-limiting keyword.
`ROW_NUMBER()` works on both and is the form to teach.

```sql
join (select z.oid from (
        select o2.Object_ID as oid,
               row_number() over (order by count(distinct a2.Object_ID) desc) as rk
        from … group by o2.Object_ID
      ) z where z.rk <= 10) t10 on t10.oid = o.Object_ID
```

Window functions need MySQL 8+, MariaDB 10.2+, SQL Server 2012+ or SQLite 3.25+. On older
repositories, fall back to the dialect-specific form.

Bar and Column widgets have **no top-N or sort setting of their own**, so the limiting always
happens in SQL.

## 5. Confirmed working on a MySQL repository

`JOIN`, derived tables, `UNION`, `IN (subquery)`, `GROUP BY` inside a subquery, `COUNT`,
`COUNT(DISTINCT …)`, `CASE WHEN`, `ROUND`, decimal literals, `LOWER`, `ORDER BY`,
`ROW_NUMBER() OVER (…)`, `LIMIT`, `REGEXP`, and `CAST` with a MySQL type name.
