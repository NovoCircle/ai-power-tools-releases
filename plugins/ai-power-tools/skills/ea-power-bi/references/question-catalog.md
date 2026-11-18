# The question catalog: what architecture teams ask, and how to check the answers

A generated model is shaped by the customer's technology: a table per stereotype, a column per tag,
a `Con_` table per connector combination. So the questions an architecture team asks cannot be written
against table names. They are written against **roles** ("the application element", "the lifecycle tag",
"the depends-on connector"). A **binding** maps each role to this customer's tables and columns. A
**check** then computes each answer two ways, so that whoever asks Power BI or Copilot has an answer to
compare against.

Tool: [`../../_shared/tools/question_bindings.py`](../../_shared/tools/question_bindings.py). It is pure: it reads the
business-layer definition file and writes text. It runs nothing against a database or Power BI, writes
no measure and builds no report page.

Westbrook Bank is the illustration: the fixture `../../_shared/tools/fixtures/westbrook.question-binding.json` binds the roles
below to the Westbrook definition. Read each value in it as an example to replace. Its `vendor_value` is a placeholder vendor name that is not in the Westbrook data, so Q5 built from the fixture returns no rows; the measured Q5 asked about a vendor the Westbrook model does hold. Your technology has
its own stereotypes, tags and connectors, and nothing here assumes you have the Westbrook model.

---

## 1. The roles

| Kind | Role | Means | Westbrook example |
|---|---|---|---|
| Entity | `application` | The application element | `Business Application` |
| Entity | `vendor_system` | The vendor or supplied system element | `Vendor System` |
| Entity | `depended_on` | What an application depends on or uses | `Business Service` |
| Tag (of `application`) | `lifecycle` | Where it is in its life | `lifecycle` |
| Tag (of `application`) | `criticality` | How critical it is | `criticality` |
| Tag (of `application`) | `regulatory_scope` | The regulations it falls under. May hold several values | `regulatoryScope` |
| Tag (of `application`) | `data_classification` | The sensitivity of the data it holds | `dataClassification` |
| Tag (of `application`) | `business_owner` | Who owns it for the business | `businessOwner` |
| Tag (of `vendor_system`) | `vendor` | Which vendor supplies it | `vendor` |
| Connector | `depends_on` | From `application` to `depended_on` | `Con_Business Application Uses Business Service` |

A role you cannot bind is not an error. The questions that need it are reported as needing it, and
every other question still builds. Bind only what the customer's technology has.

## 2. The binding

A binding is a small JSON file. Entities are table names as the definition names them, tags are column
names of the bound entity's table, the connector is a `Con_` table name:

```json
{
  "entities":   {"application": "<table>", "vendor_system": "<table>", "depended_on": "<table>"},
  "tags":       {"lifecycle": "<column>", "criticality": "<column>"},
  "connectors": {"depends_on": "<Con_ table>"},
  "terms":      {"retired": ["<value>", "<value>"], "critical": ["<value>"]},
  "params":     {"scope_value": "<text>", "subject_application": "<name>"}
}
```

Three steps, in order:

1. **Propose.** `python question_bindings.py propose <definition.json>` lists, for each role, the tables
   and columns whose names look like it. It never chooses. Two tables can both look like the application
   element (one the technology defines, one that exists only because elements carry the stereotype
   without it), and a wrong pick gives a confident wrong answer. Show the person the candidates and ask.
2. **Validate.** `python question_bindings.py validate <definition.json> <binding.json>` checks that every
   table and column exists, that a tag column belongs to the bound entity's table, that the connector
   table joins the bound entities and has `source_guid` and `target_guid`, and that nothing in the file is
   misspelled. A binding that does not validate builds no plan.
3. **Plan.** `python question_bindings.py plan <definition.json> <binding.json>` prints, for each
   question, the SQL and the DAX that compute its answer. `--dialect sql` or `--dialect dax` prints one;
   `--questions Q1,Q8` selects.

**Business terms are the customer's.** "Retired" and "critical" mean whatever the customer says. The
binding lists the values, and the tool never fills them in. A question that needs a term the binding does
not hold is reported as needing it. When a term could mean two things (does "critical" include the second
tier?), ask which, and record the answer next to the result: the same data gives two different counts, and
both are defensible.

**Parameters are the customer's too**: a criticality value, a scope, a vendor, a subject element. Ask for
each. None is defaulted.

## 3. The questions

Q1 to Q11 were asked of Microsoft 365 Copilot in the Westbrook measurements, with their answers computed
by DAX and by SQL from the same data; the two agreed on every question. Q12 to Q15 are questions
architecture teams commonly ask that were not measured. The statements for them are checked on toy data
and owed a run on a real model.

| Id | The question, written against roles | Needs |
|---|---|---|
| Q1 | How many applications do we have? | `application` |
| Q2 | How many applications have criticality `{criticality_value}`? | `application`, `criticality` |
| Q3 | Break the applications down by criticality | `application`, `criticality` |
| Q4 | How many applications are in `{scope_value}` scope? The tag holds several values, so this is a text match | `application`, `regulatory_scope` |
| Q5 | Which vendor systems come from `{vendor_value}`? | `vendor_system`, `vendor` |
| Q6 | Which things does `{subject_application}` depend on? (forward traversal) | `application`, `depended_on`, `depends_on` |
| Q7 | Which applications depend on `{subject_depended_on}`? (reverse traversal) | `application`, `depended_on`, `depends_on` |
| Q8 | Which applications are being retired? | `application`, `lifecycle`, term `retired` |
| Q9 | How many critical applications do we have? | `application`, `criticality`, term `critical` |
| Q10 | Which applications hold `{classification_value}` data? | `application`, `data_classification` |
| Q11 | How many vendor systems are in the model? | `vendor_system` |
| Q12 | Break the applications down by lifecycle | `application`, `lifecycle` |
| Q13 | Which applications have no business owner recorded? | `application`, `business_owner` |
| Q14 | How many applications have no lifecycle recorded? | `application`, `lifecycle` |
| Q15 | How many things does `{subject_application}` depend on? | `application`, `depended_on`, `depends_on` |

What the statements do, so a reader can judge a result:

- **Counts and lists read the business table itself**, so the blank member that the one-side filter adds
  to every entity table (see `SKILL.md` §2) is not counted. This matches the count measures.
- **A tag match is exact** (Q2, Q5, Q10) except Q4, which is a text match. The SQL follows the database's
  collation. DAX comparisons ignore case. If the customer's data differs only by case, the two can differ.
- **Empty means blank or an empty string** (Q13, Q14).
- **Traversals join the connector table to the entity tables on the guid columns.** The DAX does the same
  and does not use the model's relationships, so an inactive relationship (the same entity type at both
  ends of the connector) cannot change the answer.
- **Names are what the `name` column holds.** Two elements with the same name are not told apart; lists
  are distinct names.

## 4. The answer check

`check_plan` takes the plan and runners that the caller supplies, each a function from a statement to
rows, and reports one result per question:

| Result | Means |
|---|---|
| `agree` | The SQL and the DAX gave the same answer (and it equals the person's expected answer, when one was given) |
| `differ` | They differ. Report both and trust neither. Look first at the business term, the collation, and whether the model was refreshed after the database |
| `wrong` | The answer differs from the answer the person said is right |
| `sql_only`, `dax_only` | Only one runner was supplied |
| `not_run` | The question needs a role, term or parameter the binding lacks |

Run the SQL against the reporting database (path A, B or C in `SKILL.md` §1: the views in the EA
database, the reporting database, or the Parquet files read through a SQL endpoint). Run the DAX against
the published or open model, in Power BI Desktop's DAX query view or through the modeling MCP server in
`power-bi-modeling-mcp.md`. The DAX needs a model refreshed from the same data as the SQL, so refresh first
and say when.

The answers are what Copilot's answers are compared with. A Copilot answer that matches is not proof the
model is good, and one that differs is not proof it is wrong: check the term first.

## 5. What is not verified

- The SQL statements are run in the tool's tests on a small database. They have not been run on a full
  model.
- The DAX statements have not been run in an engine by this tool. Run each once in Power BI Desktop on a
  built model before relying on a result, and say so in the report. In particular the traversal
  statements use variables and `IN` over a table.
- Copilot's behavior on Q12 to Q15 is not measured.

## 6. What this does not do

- It writes **no measure** and builds **no report page**. The model keeps its count measures and its
  traversal measures and nothing else (`SKILL.md` §2). Turning a question into a measure changes that rule
  and is a separate decision.
- It does not fix data. A blank lifecycle is reported as a blank lifecycle (Q14); filling it in is
  modeling work for the EA skills.
