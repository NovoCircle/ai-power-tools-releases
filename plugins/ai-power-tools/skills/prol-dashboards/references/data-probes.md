# Data probes — characterize a repository before choosing widgets

Detail supporting [`../SKILL.md`](../SKILL.md) §1. Read that section first.

The queries here were executed against a live MySQL-backed repository. **The illustrative readings
are Westbrook Bank figures, not measured output** — they show how to interpret a result, not what
any particular repository contains.

Run these in the chart wizard's query console: add a chart, `Skip to Query`, paste, `Execute`, read
the preview, then **Cancel without saving**. The console runs arbitrary `SELECT` statements and is
the cheapest read surface in the product.

---

## 1. Why probe first

| Chart | Silently useless when |
|---|---|
| Pie, Donut | the grouping column has too many distinct values |
| Bar, Column | same, plus no natural ordering |
| Stacked anything | the second dimension has one value, or hundreds |
| Bubble | the axes are not numeric, **or are numeric with no variance** |
| Road Map | no date-like tagged values |
| Landscape, Nested Pie | no hierarchy connector |
| Integration Map | the elements have no connectors between them |

**None of these fail loudly.** Each produces a chart that renders and is wrong or unreadable.

## 2. Probe A — the census

```sql
select 'elements' as metric, count(*) as value from t_object
union all select 'distinct Object_Type',          count(distinct Object_Type) from t_object
union all select 'distinct element Stereotype',   count(distinct Stereotype)  from t_object
union all select 'distinct Status',               count(distinct Status)      from t_object
union all select 'distinct Phase',                count(distinct Phase)       from t_object
union all select 'distinct Complexity',           count(distinct Complexity)  from t_object
union all select 'connectors',                    count(*)                    from t_connector
union all select 'distinct connector Stereotype', count(distinct Stereotype)  from t_connector
union all select 'tagged value names',            count(distinct Property)    from t_objectproperties
```

How to read it, with Westbrook Bank as the illustration:

| Reading | Means |
|---|---|
| `distinct element Stereotype` = 14 | the WBA stereotype set; usable as a Bar, **too many for a Pie** |
| a tagged value with 4 permitted values, such as `criticality` | **ideal for a Pie or Donut** |
| a tagged value with 5 permitted values, such as `lifecycle` | good Bar, good second dimension for a stack |
| `distinct Complexity` = 3 | technically numeric, **almost no range** — a poor Bubble axis |
| `connectors` greater than zero | Integration Map is viable |
| `distinct connector Stereotype` = 8 | one of them may be the hierarchy — see Probe C |

> **Run this before proposing anything.** One query, and it rules chart types in and out before any
> are built.

## 3. Probe B — which tagged values are usable

```sql
select p.Property as tag,
       count(*)                                           as rows_total,
       sum(case when p.Value regexp '^[0-9]+([.][0-9]+)?$'
                then 1 else 0 end)                        as numeric_vals,
       sum(case when p.Value regexp '^[0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{1,4}$'
                then 1 else 0 end)                        as datelike_vals,
       count(distinct p.Value)                            as distinct_vals
from t_objectproperties p
where p.Value is not null and p.Value <> ''
group by p.Property
order by count(distinct p.Value) desc
limit 20
```

**`distinct_vals` is the column that matters.** In testing, one tag returned thousands of perfectly
numeric values and **exactly one distinct value** — valid as a number, useless as a Bubble axis,
because every bubble would be the same size.

> **A column is a usable measure only when it is numeric AND varies.** "Is it a number" is the
> question people ask and it is the wrong one.

> **Dialect warning — this is the least portable query in this skill.** `REGEXP` is MySQL and
> MariaDB. SQL Server has no `REGEXP` and needs `LIKE` patterns or `TRY_CONVERT`; PostgreSQL uses
> the `~` operator. Rewrite per engine and check against `VIEW SAMPLE`.

Sort by `distinct_vals`, not by volume. Sorting by row count surfaces high-volume boolean and enum
tags and buries the date-bearing ones you are usually hunting for.

## 4. Probe C — is there a hierarchy

Needed by Landscape and Nested Pie. **Not yet executed — treat as a design.**

```sql
select c.Stereotype, c.Connector_Type, count(*) as n,
       count(distinct c.Start_Object_ID) as distinct_children,
       count(distinct c.End_Object_ID)   as distinct_parents
from t_connector c
group by c.Stereotype, c.Connector_Type
order by count(*) desc
```

A plausible hierarchy connector has many distinct children and markedly fewer distinct parents.
Confirm by counting: **parent-child connectors should equal (elements − roots)**.

> **Do not filter connectors by `Connector_Type` to find a hierarchy.** A hierarchy is frequently an
> Aggregation rather than an Association, and a Type filter that looks harmless hides it completely.
> This cost a full day during verification.

**Do not assume the stereotype is stored qualified because an MDG declares it.** In Westbrook Bank
the WBA technology declares the connector stereotypes `Uses`, `Flows` and `realizes`, and
`t_connector.Stereotype` still holds them bare (measured on the model, EA 17.1, 2026-10-07); the
binding to the technology is in `t_xref` (`FQName=WestbrookBankArchitecture::Uses`). Others, such
as `part-of`, come from no technology. What Prolaborate itself holds for a declared connector
stereotype was not re-measured. **Read the resolved value from Execute's Identified Placeholders
rather than guessing either form** — a filter written for one form fails silently on the other.

Depth must be probed one level at a time with self-joins — the single-`SELECT` restriction forbids a
recursive CTE.

## 5. Probes D and E — proposed, not executed

**Probe D — cardinality within the chosen scope.** The census is repository-wide; a dashboard is
usually scoped to a package, and cardinality inside that package governs readability. Thread a
package predicate through Probe A.

**Probe E — connectivity.** The proportion of scoped elements with any connector at all. An
Integration Map over elements that are mostly unconnected is a cloud of dots.

## 6. Cardinality thresholds

**These are conventional charting judgments, not measurements from this product.** They are a
default to argue with.

| Distinct values | Reasonable | Unreasonable |
|---|---|---|
| 2–7 | Pie, Donut | |
| 2–15 | Bar, Column; second dimension of a stack | Pie, above about 7 |
| 15–40 | Bar or Column with rotated labels, or a top-N | Pie, Donut, any stack |
| 40+ | **top-N only**, or a Report | every chart type |

**One threshold is a finding, not a convention:** Nested Pie and Heat Map need a hand-typed
label-to-color row **per value**. Above a handful of values that is unreasonable work, independent
of readability.

## 7. What this does not yet do

- Probes C, D and E have not been run.
- The thresholds in §6 are convention.
- Everything is repository-wide; there is no scope-aware variant.
- No SQL Server forms. Probe B in particular will not run there.
- Nothing links a question in English to a probe result automatically. §2 of
  [`../SKILL.md`](../SKILL.md) is a table a human or an agent reads, not a procedure.
