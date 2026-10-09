# The path choice, in words

How the business layer reaches Power BI is **answerable from a fact about the customer's estate**.
It is not a preference, and it is not ours to make for them. This file holds the questions to ask,
what each answer commits them to, and the wording for the two questions that follow.

Read `SKILL.md` §1 first; this is the long form of it.

---

## 1. The questions, in order

1. **"Can you reach the EA database directly - is it SQL Server, and may you create views in it?"**
   A repository held in a file (`.qea`) has no database server to connect to. A repository reached
   through a cloud connection (Pro Cloud Server) has no direct database access for the person
   asking. Either rules direct access out, and asking first means the customer hears a constraint
   rather than a refusal.
2. **"If not, can you run a SQL Server for a reporting database?"** AI Power Tools fills it over
   EA's own interface from the open repository. It needs a Windows account that may create the
   database.
3. **"If neither, are Parquet files on this machine enough?"**

Someone with direct access may still choose a reporting database or Parquet: to keep views out of
the production database, or because Power BI should not query it. All three paths leave out the
packages the user excludes.

---

## 2. The decision table

| If the customer says... | Path | Storage mode | What to state |
|---|---|---|---|
| "I can reach the EA database, it is SQL Server, and I may create views" | **A - direct access**: views in their own schema inside the EA database | **DirectQuery** (live), or Import | The views live in the production database and EA's own tables are never altered. DirectQuery queries that database, and its speed at the scale of a large repository is not measured. Regenerate the views when the technology or the inclusion choice changes |
| "I cannot reach the database, or do not want views in it, but I can run SQL Server" | **B - reporting database**: views in a separate SQL Server database | **Import** | A snapshot, rebuilt in full on every refresh with no history. A failed refresh leaves the previous data live. Queries never touch the production database |
| "No database access, and no database to run" | **C - Parquet files** | **Import** | A snapshot, rewritten on every refresh, read by Power BI Desktop on this machine. `pyarrow` is needed to write the files. OneLake upload is not yet available (APT-2026-0362) |
| "I want Power BI to read the repository live" | **A in DirectQuery**, and only if they can reach the database | DirectQuery | Say plainly that every query reads the production database. For any other estate there is no live option: B and C are snapshots, and a snapshot is not a substitute for live data |

**Do not quietly build a snapshot when the customer asked for live data.** The report keeps working
and the numbers go stale silently.

---

## 3. What is identical across the three paths, and why that matters

The generator reads one definition file. Everything a customer sees is the same on every path:

| | |
|---|---|
| The tables | the business tables - entity, `Con_`, tag-row and the Table Directory - plus EA's nine tables, hidden |
| The names, columns and types | exactly as `ea-reporting-database` defines them |
| The relationships | declared by the generator, the business layer filtering EA's tables, with the same active and inactive states |
| The measures | one per inactive relationship, on its `Con_` table |
| The descriptions, hidden flags and layout | the same |

Only two things vary: **where a table's rows come from** (a view in the EA database, a view in the
reporting database, or a Parquet file) and **the storage mode**. A test emits all three paths for
Westbrook Bank and compares the TMDL with those two things set aside; everything else must be
identical.

**So do not sell the paths as three different Power BI capabilities.** They are one model with three
sources. A customer who moves from one path to another keeps the report: it is built on the same
tables and column names.

---

## 4. The two questions that follow, and their answers

**"Can it refresh automatically?"**

The reporting layer can, with an AI agent in charge of the schedule - never Windows Task Scheduler.
A scheduled task in Claude Cowork, connected to the EA machine, calls `start_reporting_refresh`,
polls for the result and reports it. EA must be running with the repository open on that machine.
What Power BI does next depends on the path:

- **A, DirectQuery:** nothing; the views are read live.
- **B:** Power BI's own scheduled refresh against the SQL Server, through an on-premises data
  gateway, for a published model; Refresh in Desktop otherwise.
- **C:** rewrite the files (the local step in `SKILL.md` 4.2), then Refresh in Desktop. A published
  model cannot refresh from files until OneLake upload is available (APT-2026-0362).

Scheduled refresh in the Power BI service and the gateway have **not been tested with this model**.
Do not assert either way.

**"Can I move the files?"**

Not without regenerating. A Parquet folder, and a SQL server and database, are written into the
project, so the project belongs to where it was generated for. Regenerate rather than editing a
partition by hand - a hand-edited TMDL file is rejected whole, not line by line.

---

## 5. How to put the choice

Put all three on the table, in one message, with the consequence attached to each - not one option
at a time, and not a recommendation dressed as a question. The customer is choosing between things
that are differently true about their estate, and they can only do that if they can see the three
together.

Then stop and wait. A customer who was never asked will reasonably assume they got the option they
would have chosen.
