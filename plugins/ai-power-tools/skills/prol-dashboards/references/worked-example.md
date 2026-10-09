# Worked example — a Westbrook Bank application portfolio dashboard

Detail supporting [`../SKILL.md`](../SKILL.md). A full pass: probe, choose, build, verify, hand back
a layout plan.

Model: the Westbrook Bank reference model — see
[`../../_shared/references/westbrook-example.md`](../../_shared/references/westbrook-example.md).
Applications are `WBABusinessApplication` on the `Component` metaclass. The `criticality` tag has
four permitted values, `lifecycle` five.

The SQL below is written for a **MySQL-backed** repository. Confirm the dialect first (§3 of
[query-contracts.md](query-contracts.md)).

---

## The request

> *"Build me a dashboard showing our application portfolio — how many applications we have, how
> they split by criticality, how criticality relates to lifecycle, and which applications the most
> other things depend on."*

## Step 1 — probe before choosing

Run the census ([data-probes.md](data-probes.md) §2). The things that decide the design:

| Finding | Consequence |
|---|---|
| `criticality` has **4** distinct values | a Pie is appropriate — under the seven-value limit |
| `lifecycle` has **5** | a good second dimension for a stack |
| Applications number in the dozens | "which depend on most" needs a **top-N**, not all of them |
| `Uses` connectors exist, stored **bare** in `t_connector.Stereotype` | dependency counting is possible; filter on the bare name |

> **Check the stereotype storage form before writing the filter.** Westbrook's connector
> stereotypes are stored bare in `t_connector.Stereotype`, including `Uses`, which the WBA
> technology now declares (the binding is in `t_xref`). What Prolaborate itself holds for a
> declared one was not re-measured. Reading the resolved value from Execute's Identified
> Placeholders settles it in seconds; guessing costs hours.

## Step 2 — the four metric cards

One tile, four Card blocks. Each is `Skip to Query` with a single value aliased `cards`.

**Total applications**

```sql
select count(*) as cards
from t_object o
where o.Stereotype = 'WBABusinessApplication'
```

**Mission-critical applications**

```sql
select count(*) as cards
from t_object o
join t_objectproperties p on p.Object_ID = o.Object_ID and p.Property = 'criticality'
where o.Stereotype = 'WBABusinessApplication'
  and p.Value = 'Mission-Critical'
```

**Applications with no business owner** — the number that prompts action

```sql
select count(*) as cards
from t_object o
where o.Stereotype = 'WBABusinessApplication'
  and o.Object_ID not in (
      select p.Object_ID from t_objectproperties p
      where p.Property = 'businessOwner' and p.Value <> ''
  )
```

**Ownership coverage, as a percentage**

```sql
select round(
         (select count(distinct o2.Object_ID)
            from t_object o2
            join t_objectproperties p2 on p2.Object_ID = o2.Object_ID
             and p2.Property = 'businessOwner' and p2.Value <> ''
           where o2.Stereotype = 'WBABusinessApplication') * 100.0
         /
         (select count(*) from t_object o3
           where o3.Stereotype = 'WBABusinessApplication')
       , 0) as cards
```

In the Card presentation step set `Symbol: Percentage` and `Prefix/Suffix: Suffix`.
**Do not put a `%` in the SQL** — the widget appends it and a text result breaks the card.

> **Execute every card and read the number before saving.** Then run one query that would return
> zero or something absurd if your key assumption were wrong. A number that agrees with your
> expectation deserves the same scepticism as one that does not — during verification a rollup
> query returned exactly the expected figure because its join was matching nothing.

## Step 3 — criticality split (Pie)

Four values, so a Pie is honest here.

```sql
select o.Name,
       o.ea_guid     AS Classguid,
       o.Object_Type AS BaseType,
       o.Stereotype  AS Stereotype,
       p.Value       AS series
from t_object o
join t_objectproperties p on p.Object_ID = o.Object_ID and p.Property = 'criticality'
where o.Stereotype = 'WBABusinessApplication'
```

One row per application; the chart counts them. In the presentation step, `Build Chart by` decides
whether slices read as percentages or counts — pick deliberately.

## Step 4 — criticality against lifecycle (Stacked Column)

```sql
select o.Name,
       o.ea_guid     AS Classguid,
       o.Object_Type AS BaseType,
       o.Stereotype  AS Stereotype,
       pc.Value      AS series,       -- criticality -> color and legend
       pl.Value      AS GroupName     -- lifecycle   -> axis category
from t_object o
join t_objectproperties pc on pc.Object_ID = o.Object_ID and pc.Property = 'criticality'
join t_objectproperties pl on pl.Object_ID = o.Object_ID and pl.Property = 'lifecycle'
where o.Stereotype = 'WBABusinessApplication'
```

> **`GroupName` is the axis and `series` is the color** — the reverse of what the designer's
> `X-Axis` and `Group values in X-axis` labels suggest. Build it the other way round and the chart
> is not wrong so much as transposed, which is harder to notice.

## Step 5 — top 10 by dependants (Column)

"Which applications do the most other things depend on" is a count-per-thing bar: **one row per
dependency pair**, with `series` as the application name. The bar height is the number of rows.

```sql
select o.Name,
       o.ea_guid     AS Classguid,
       o.Object_Type AS BaseType,
       o.Stereotype  AS Stereotype,
       o.Name        AS series
from t_object o
join t_connector c on c.End_Object_ID = o.Object_ID and c.Stereotype = 'Uses'
join (select z.oid from (
        select o2.Object_ID as oid,
               row_number() over (order by count(distinct c2.Connector_ID) desc) as rk
        from t_object o2
        join t_connector c2 on c2.End_Object_ID = o2.Object_ID and c2.Stereotype = 'Uses'
        where o2.Stereotype = 'WBABusinessApplication'
        group by o2.Object_ID
      ) z where z.rk <= 10) t10 on t10.oid = o.Object_ID
where o.Stereotype = 'WBABusinessApplication'
```

`ROW_NUMBER()` rather than `LIMIT` or `TOP`, because those two share no syntax between MySQL and
SQL Server and this query should survive a repository move.

**Name the widget for what it shows.** If you later change the rank cut-off, change the title in the
same edit — a tile titled "Top 10" showing twelve bars is a defect a reader will find before you do.

## Step 6 — the landscape

Build this one through the **designer**, not by hand: it is the fastest way to get the
level-numbered contract right, and the designer handles the connector traversal.

- Group 1 must be the **top tier** of the hierarchy. Starting from a middle tier silently produces a
  partial landscape.
- Set the hierarchy connector's stereotype, and **set no Type filter** — a Westbrook `part-of`
  connector may be an Aggregation, and a Type filter of `Association` hides it completely.
- Direction: derive it rather than assuming. If Start is the child and End the parent, descending is
  `Target To Source`. Confirm by row count — parent-child connectors should equal elements minus
  roots.
- **Rename the level labels.** They default to `Level-0`, `Level-1`, which ship straight to the
  reader.

## Step 7 — verify, then hand back the layout

Verify each widget from a surface other than the one you built it on: re-open the configuration, and
check the rendered tile against the Execute row count.

Then give the user the plan, and say that this skill cannot apply it:

```
Application Landscape           c1 r0   2 x 3
Portfolio Summary (4 cards)     c3 r0   1 x 2
Criticality split (pie)         c0 r3   2 x 3
Criticality x lifecycle (stack) c2 r3   2 x 3
Top 10 by dependants (column)   c0 r6   2 x 3
```

With the three notes from [layout.md](layout.md) §3: drag from the crosshair handle, expect pushes
to cascade, and save the dashboard afterwards.

> **Say plainly that the tiles will arrive 1x1 and look wrong until the plan is applied.** A user
> who was not told assumes the skill failed.
