# The inclusion choice

What a reporting build includes beyond the MDG is the user's decision, made once, shown with
counts, and saved. Nothing downstream second-guesses it. Every figure below is an illustration
from a small Westbrook Bank-shaped fixture; substitute your own technology, stereotypes and
model.

Code: `../../_shared/tools/inclusion.py`. It is pure: rows in, plain data out. Its tests run with
`python -m pytest ../../_shared/tools/test_inclusion.py -q` and need no EA.

---

## 1. The three options

| # | Option | What the build holds |
|---|---|---|
| 1 | **Only what my MDG defines** | The MDG's element stereotypes and connector stereotypes. Nothing else |
| 2 | **Everything in the repository** | Option 1, plus every observed element key and connector key |
| 3 | **Show me the gaps** | Option 1, plus the gaps the user includes; each gap is included, excluded, or sent to the MDG skills |

"Observed" is keyed the way the build keys it, and the choice is only meaningful in those terms:

| | Key | Example |
|---|---|---|
| Element, bound to a profile | the `FQName` | `BMM::Goal` |
| Element, ad hoc | stereotype text and metaclass | `VendorApplication` on `Component` |
| Element, no stereotype | metaclass alone | `Requirement` |
| Connector, bound | the `FQName` | `BMM::Influences` |
| Connector, ad hoc | the stereotype text | `extends` |
| Connector, no stereotype | the base type | `Association` |

A stereotype counts as the MDG's only when it is **bound to the MDG's profile namespace**. The
same name carried ad hoc, or bound to another language, is a gap, never the declared stereotype.
A connector's key drops the base type, so one stereotype on two base types is one key.

---

## 2. Run the census, then analyze

Both censuses come from the same `t_xref` rows (`ea_census.build_stereotype_index`); the rows the
censuses were taken from go to `analyze` as well, because it needs a name to show for each gap and
the metaclass of unstereotyped elements.

**Where the inputs come from.** Each is a list of row dicts keyed by column name, read with
`ea_analyze(operation="execute_sql", params={"sql": ..., "include_xml": False})`. The rows come back
under the `rows` key of the result (`{"rows": [...], "row_count": n, ...}`), and every value is a
string: NULL and empty text are both `""`, and an id is `"12"`, not `12`. Compare ids with ids from
the same kind of row, or convert both sides with `int()`.

**Take the census over the scope, not the whole repository, and read only the scope.** The scope is
the root packages in `scope.roots` and every sub-package under them, minus each package in
`scope.exclude` and its sub-packages. The two readings give different answers: a defect or a gap
outside the scope would otherwise stop the preflight or be offered as a decision, and the build
would never have read it. Read `t_package` whole (it is small), work out the in-scope package ids,
and filter the other reads by them in SQL, so a large repository's tables are never read whole. A
connector is in scope when either end's element is; keep only the `t_xref` rows whose `Client` is
an in-scope element or connector GUID.

| Name | Read with |
|---|---|
| `packages` | `SELECT Package_ID, Parent_ID, ea_guid, Name FROM t_package` |
| `objects` | `SELECT * FROM t_object WHERE Package_ID IN (<in-scope ids>)` |
| `connectors` | `SELECT * FROM t_connector WHERE Start_Object_ID IN (<in-scope object ids>) OR End_Object_ID IN (<in-scope object ids>)`, the object ids being `SELECT Object_ID FROM t_object WHERE Package_ID IN (<in-scope ids>)` |
| `xref_rows` | the Stereotypes rows of `t_xref` (`WHERE Name = 'Stereotypes'`) whose `Client` is an in-scope element GUID or connector GUID, as two reads: `Client IN (SELECT ea_guid FROM t_object WHERE Package_ID IN (<in-scope ids>))` and the same over the in-scope connectors |
| `mdg` | the dict `ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "<id>"})` returns |

A scope with no packages has nothing to read. A very long id list can exceed the database's
statement limit: split it into groups of about 500 ids and join the rows. The server refuses an SQL
result of more than 64 MB of XML as unreadable. How large each of these reads is on a large
repository has not been measured; filtering by package is what keeps them small, and a scope that
covers nearly the whole repository saves little.

```python
import sys
sys.path.insert(0, r"<skills-dir>/_shared/tools")
from ea_census import build_stereotype_index, census_elements, census_connectors
from inclusion import analyze, resolve_answer, new_since_saved

def rows(sql):   # ea_analyze(operation="execute_sql", params={"sql": sql, "include_xml": False})["rows"]
    ...

packages = rows("SELECT Package_ID, Parent_ID, ea_guid, Name FROM t_package")
by_guid = {p["ea_guid"]: p for p in packages}
children = {}
for p in packages:
    children.setdefault(p["Parent_ID"], []).append(p["Package_ID"])

def subtree(guids):
    ids, todo = set(), [by_guid[g]["Package_ID"] for g in guids if g in by_guid]
    while todo:
        pid = todo.pop()
        if pid not in ids:
            ids.add(pid)
            todo.extend(children.get(pid, []))
    return ids

in_scope = subtree(profile["scope"]["roots"]) - subtree(profile["scope"]["exclude"])
ids = ", ".join(sorted(in_scope, key=int))
in_objects = f"SELECT Object_ID FROM t_object WHERE Package_ID IN ({ids})"
objects = rows(f"SELECT * FROM t_object WHERE Package_ID IN ({ids})")
connectors = rows(f"SELECT * FROM t_connector WHERE Start_Object_ID IN ({in_objects}) "
                  f"OR End_Object_ID IN ({in_objects})")
in_connectors = (f"SELECT ea_guid FROM t_connector WHERE Start_Object_ID IN ({in_objects}) "
                 f"OR End_Object_ID IN ({in_objects})")
xref_rows = (rows("SELECT * FROM t_xref WHERE Name = 'Stereotypes' AND Client IN "
                  f"(SELECT ea_guid FROM t_object WHERE Package_ID IN ({ids}))")
             + rows(f"SELECT * FROM t_xref WHERE Name = 'Stereotypes' AND Client IN ({in_connectors})"))

index = build_stereotype_index(xref_rows)
a = analyze(census_elements(objects, index), census_connectors(connectors, index), mdg,
            objects, connectors)          # namespace= if it cannot be inferred
```

Before the profile exists there are no roots yet: take them from the user, then run this. A
connector with one end in an excluded package stays in scope through its other end; the build
keeps it with an `(excluded)` stub at the far end.

`a.options()` gives option 1 and option 2 by count; `a.gaps` is the option 3 list; `a.unbound_connectors`
and `a.multi_stereotyped` are the defects of §3.

`Coverage` holds, per option: declared and observed **element keys**, distinct **elements**,
declared and observed **connector keys**, and **connectors**. An element in two tables counts once
in `elements`. Counts are of keys and instances, not tables: how many connector tables a key
yields depends on the allowed source and target combinations, which the build decides.

Unstereotyped diagram furniture (`Package`, `Note`, `Text`, `Boundary`) is not model content and
never gets a table, so it is neither counted nor offered as a gap.

**Option 2's element count can understate what the server builds.** The census leaves out elements
that carry only EA's own internal stereotypes (`a.ea_internal_elements` of them, and
`a.ea_internal_connectors` for connectors), and the server's "everything" does not. Show that number
beside option 2, so the person knows the count is a floor by that much. The count has not been
compared with a build on a large repository.

---

## 3. Two data defects, which are not gaps

A gap is a question for the user. These are mistakes in the repository, fixed there.

**A connector bound to no profile.** Its stereotype is qualified text (`WBA::Flows`) but no
`FQName` binds it, so EA never recorded the binding. **The preflight stops.** `resolve_answer`
refuses to produce a profile for any option while one exists. The defect carries the fix:

- the MDG declares the stereotype: `update_connector` with `StereotypeEx` set to the qualified
  name, `<profile namespace>::Flows`; or re-apply the stereotype in EA from the toolbox or
  Properties > Stereotype, which is the same fix by hand;
- it declares no such stereotype: clear `StereotypeEx`, or have the MDG skills declare it.

Take a baseline first (`ea-change-management`); either route writes to the model, and with the
governance gate's stereotype application (`the-governance-gate.md` §4) it is one of the two writes
in this skill. Then re-run the census.

**An element with two declared stereotypes.** It is flagged, with the count and the combination.
If the user continues, it is placed in **both** tables - pass
`continue_with_double_stereotypes=True`. Without that, `resolve_answer` refuses. An element
carrying one declared stereotype and one from another language is ordinary and is not flagged.

---

## 4. Ask the question

Put all three, with the counts, every time a profile is created. Say what option 3 offers in
numbers too: how many element keys and connector keys are gaps and how many elements and connectors
they hold. For each gap show the key, its count and the example name, so the user can recognize it.

Then record the answer:

```python
answer = resolve_answer(a, 1)                 # or 2
answer = resolve_answer(a, 3, {gap.id: "include" | "exclude" | "update_mdg" for ...})
profile["inclusion"] = answer.inclusion       # exactly the profile's inclusion section
profile["inclusion_choice"] = answer.record() # stored beside it; see §5
```

`answer.inclusion` is `{"observed_elements": "all" | [{"stereotype", "metaclass"}, ...],
"observed_connectors": "all" | [<connector key>, ...]}`. Option 1 is two empty lists; option 2 is
`"all"` twice. A gap id is `element:<key>` or `connector:<key>`.

**"Update the MDG" is a hand-off, not an answer.** Declaring the gap is the MDG skills' job
(`ea-mdg-model-build`); the census reruns afterwards and the gap is then declared, so it is no
longer a gap. `resolve_answer` treats it as not decided and refuses to produce a profile while any
gap is undecided or marked for an update. Say so, hand off, re-run the census, ask again.

A bound stereotype seen on several metaclasses is saved with one entry per metaclass: the server
keys it by its most common metaclass and, on an exact tie, by whichever it met first, so one entry
per metaclass matches either way.

**No one to ask.** An unattended run (a scheduled agent) uses the profile's saved `inclusion` and
`inclusion_choice` as they are, and still flags drift (§6). If either is missing it stops, reports the
counts of §2 and asks. It never picks an option and builds nothing without one.

After the answer the metamodel is fixed. Do not re-open the choice mid-build.

---

## 5. What the profile cannot remember

The profile lists only what is included. A gap the user **excluded**, and which option was chosen,
are not in it, so by itself a refresh could not tell "excluded" from "new". Store
`answer.record()` beside the profile (`inclusion_choice`; the server ignores unknown keys). It holds
the option, the excluded gap ids, and what the MDG declared at the time.

---

## 6. Refresh: flag, never decide

On every refresh, re-run both censuses and call:

```python
for item in new_since_saved(a, profile["inclusion"], profile.get("inclusion_choice")):
    print(item.kind, item.key, item.count, item.example, item.detail)
```

It reports, and decides nothing:

- `new_element_key` / `new_connector_key` - a gap not in the saved lists and not excluded (option 3
  only: option 1 is a deliberate "MDG only" and option 2 already covers everything);
- `mdg_stereotype_added` / `mdg_stereotype_removed` / `mdg_version_changed` - the MDG is not what it
  was when the choice was made.

Show these to the user and ask. A new ad hoc connector stereotype added after setup is reported as
`new_connector_key` with its count and an example, and the build uses the saved choice until the
user answers. The unbound-connector stop of §3 applies on every refresh as well.

If there is no saved record, the option is inferred: `"all"` on both sides is option 2, anything
else is option 3 and every unlisted gap is reported.

---

## 7. The short route: only what my MDG defines, governance gate declined

The question is still asked (or the saved answer used, section 4). This is the route when the answer
is option 1 and the person declines to stereotype what that leaves out:

1. Census over the scope (section 2). Stop on a connector bound to no profile, and ask about elements
   with two declared stereotypes (section 3).
2. `resolve_answer(a, 1)`. Save `inclusion` and `inclusion_choice` in the profile.
3. Run the governance gate once (`the-governance-gate.md`), so the person sees what option 1 leaves
   out, and take their decline.
4. Build, and report the left-out counts with the result (`SKILL.md` §9).
