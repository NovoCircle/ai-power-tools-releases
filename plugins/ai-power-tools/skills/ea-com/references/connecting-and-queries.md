# Connecting and running SQL

Full detail behind the "Connecting" and "SQL access" sections of `../SKILL.md`.
Every snippet on this page was run against a live EA session with the Westbrook Bank
demo model open, and the output shown is what that run actually printed (element
names and counts are read from the model, so they reflect its current content).

## Connecting

```python
import win32com.client

app = win32com.client.GetActiveObject("EA.App")
repo = app.Repository
print(repo.ConnectionString)
```

Verified output: `<model-dir>\WestbrookBank.qea`.

`GetActiveObject("EA.App")` attaches to the currently running EA instance via
`win32com.client.GetActiveObject` — it does not launch EA, and does not accept a
project path. It fails if EA is not running or no project is open. Under this
late-bound connection style (no `makepy`/`gencache`), the failure is a
`pywintypes.com_error`; wrap it in retries for scripts that may run before EA has
finished starting:

```python
import time
import pywintypes
import win32com.client

def connect(retries=3, delay=2.0):
    last_err = None
    for attempt in range(retries):
        try:
            return win32com.client.GetActiveObject("EA.App").Repository
        except pywintypes.com_error as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delay)
    raise RuntimeError(f"Could not connect to EA after {retries} attempts: {last_err}")
```

Verified live: `connect()` and `connect(retries=10, delay=3.0)` both returned a
working `Repository` whose `.ConnectionString` matched the open project.

## Project info

```python
repo.ConnectionString   # -> "<model-dir>\WestbrookBank.qea"
repo.Models             # -> collection of root ("Model") packages; .Count == 3 in Westbrook Bank
```

`repo` (the `Repository` COM object returned by `app.Repository`) is your escape
hatch for any method not covered by a small wrapper — everything in this skill is a
direct call on it.

## The sql() helper

`Repository.SQLQuery()` returns an XML string, not rows. Earlier drafts of this
helper parsed `<Row>` **attributes** (`row.attrib`) — that returns an empty dict for
every row, because EA puts each column in a **child element**, not an attribute:

```xml
<Row><Object_ID>64</Object_ID><Name>Legacy Report Distribution Server</Name><Stereotype>WBABusinessApplication</Stereotype></Row>
```

The correct helper:

```python
import xml.etree.ElementTree as ET

def sql(query):
    """Run a SELECT via Repository.SQLQuery and parse EA's XML result into a list of dicts."""
    raw = repo.SQLQuery(query)
    root = ET.fromstring(raw)
    return [{child.tag: child.text for child in row_el} for row_el in root.iter("Row")]
```

Verified live:

```python
>>> sql("SELECT Object_ID, Name, Stereotype FROM t_object WHERE Stereotype = 'WBABusinessApplication'")
[{'Object_ID': '64', 'Name': 'Legacy Report Distribution Server', 'Stereotype': 'WBABusinessApplication'}, ...]
# 45 rows total

>>> sql("SELECT Object_ID, Name FROM t_object WHERE Name = 'Definitely Not A Real Element Name 12345'")
[]
```

Both the populated and empty-result cases return a plain list, no exception.

## execute() — DML

```python
def execute(query):
    """Run non-SELECT SQL against the repository. Always returns None -- verify with sql()."""
    return repo.Execute(query)
```

Verified live: `repo.Execute("UPDATE t_objectproperties SET Value = '...' WHERE ...")`
returned `None` even though the update visibly succeeded on read-back. Do not treat
`execute()`'s return value as a success flag — always follow it with a `sql()` read
of the row you changed.

## GetElementsByQuery vs GetElementSet

**`Repository.GetElementsByQuery` does not run SQL.** Its signature is
`GetElementsByQuery(queryName, searchTerm)` — a *named model search*, not a query
string. Passing SQL as `queryName` does not silently return nothing under a live,
late-bound connection — it raises:

```python
>>> repo.GetElementsByQuery(
...     "SELECT Object_ID FROM t_object WHERE Stereotype = 'WBABusinessApplication'", "")
com_error(-2147352567, 'Exception occurred.',
          (11, 'Enterprise Architect', 'Search Not Found', None, 0, 0), None)
```

The correct call for bulk element retrieval by SQL is `GetElementSet(sql, type)`
with `type=2` ("SQL query against `t_object`"):

```python
>>> elements = repo.GetElementSet(
...     "SELECT Object_ID FROM t_object WHERE Stereotype = 'WBABusinessApplication'", 2)
>>> elements.Count
45
>>> [ (e.Name, e.Stereotype) for e in elements ][:2]
[('Legacy Report Distribution Server', 'WBABusinessApplication'),
 ('SFTP Batch Gateway', 'WBABusinessApplication')]
```

Verified live for both the populated case (45 elements, correct `.Name`/`.Stereotype`)
and the empty case (`GetElementSet("...WHERE Stereotype = 'NoSuchStereotypeXYZ'", 2)`
returned a collection with `.Count == 0`, no error).

## Malformed SQL blocks on a modal dialog, not a Python exception

This is the trap most likely to hang an unattended script, and it was found while
verifying this skill, not copied from memory. Querying a table or column that
doesn't exist raises a blocking "SQL API Open FAILED" dialog inside EA's UI *before*
`SQLQuery()` returns anything to Python — the COM call blocks until a human dismisses
it, and only then comes back as an XML error payload (parsed by `sql()` above as an
empty list), not a Python exception.

Reproduced live, twice:

```python
>>> sql("SELECT COUNT(*) AS n FROM t_stereotype")
```
EA dialog (blocking until dismissed):
```
Enterprise Architect (Build: 1716 - 64 bit)
Sparx Systems Database API [0x00001072]
SQL API Open FAILED with error: no such table: t_stereotype
Context:
SELECT COUNT(*) AS n FROM t_stereotype
```
After the dialog is dismissed, `sql()` returns `[]` — not an exception.

This corrects an earlier claim in this skill that `t_stereotype` is simply *empty*
for MDG-only models (`SELECT COUNT(*) FROM t_stereotype -> 0`). In this schema the
table does not exist at all, and querying it does not fail quietly — it blocks the
whole script on a dialog only a human can dismiss. **Always query `t_object` for
stereotypes** (see below), never `t_stereotype`, against an EA 17 SQLite-backed
model.

The same thing happens for any bad column name, including the classic
`t_attribute.Default_Value` mistake documented below:

```python
>>> sql("SELECT a.Name, a.Default_Value FROM t_attribute a LIMIT 1")
```
EA dialog: `SQL API Open FAILED with error: no such column: a.Default_Value`.
After dismissal: `[]`.

Follow the "any COM call that may trigger a dialog" guidance in
[`../../_shared/references/latency.md`](../../_shared/references/latency.md) for
*every* `SQLQuery()` call whose SQL you haven't already validated, not just for DML.

## Useful tables

| Table | Contents |
|-------|----------|
| `t_object` | Elements (Class, Component, etc.) |
| `t_connector` | Relationships between elements |
| `t_diagram` | Diagrams |
| `t_package` | Packages |
| `t_attribute` | Attributes on elements |
| `t_operation` | Operations/methods on elements |
| `t_objectproperties` | Tagged values |
| `t_xref` | Cross-references (stereotypes, constraints) |

## SQLite schema notes (EA 17, verified live)

### Stereotypes: query t_object, not t_stereotype

`t_stereotype` does not exist in this EA 17 SQLite-backed schema (see the dialog
trap above). Always query `t_object` for stereotype information, including
MDG-defined stereotypes:

```python
>>> sql("SELECT DISTINCT Stereotype FROM t_object WHERE Stereotype IS NOT NULL AND Stereotype != ''")[:3]
[{'Stereotype': 'WBAVendorSystem'}, {'Stereotype': 'WBABusinessApplication'}, {'Stereotype': 'WBADataAsset'}]
```

### t_attribute's default-value column is [Default], bracket-quoted

```python
>>> sql("SELECT a.Name, a.[Default], a.Type FROM t_attribute a LIMIT 1")
[{'Name': 'testAttr', 'Default': 'hello', 'Type': 'String'}]
```

`[Default]` requires bracket quoting because `DEFAULT` is a SQL reserved word.
`a.Default_Value` (no such column) triggers the blocking dialog above.

### Tagged values

```python
>>> sql("SELECT tv.Object_ID, tv.Property, tv.Value FROM t_objectproperties tv WHERE tv.Object_ID = <element_id>")
```

## Common patterns

### Find all elements of a stereotype

```python
# sql() helper -- recommended, returns parsed list of dicts
rows = sql("""
    SELECT o.ea_guid, o.Name, o.Stereotype
    FROM t_object o
    WHERE o.Stereotype = 'WBABusinessApplication'
""")

# GetElementSet -- returns an EA.Collection of live element objects
elements = repo.GetElementSet(
    "SELECT Object_ID FROM t_object WHERE Stereotype = 'WBABusinessApplication'", 2)
for elem in elements:
    print(elem.Name, elem.Stereotype)
```

### Read tagged values for an element

```python
rows = sql(f"""
    SELECT p.Property, p.Value
    FROM t_objectproperties p
    WHERE p.Object_ID = (
        SELECT Object_ID FROM t_object WHERE ea_guid = '{element_guid}'
    )
""")
```

Both patterns verified live against the Westbrook Bank demo model.
