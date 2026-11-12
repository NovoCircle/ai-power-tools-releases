# Packages, Known Defects, Idempotency, and Error Recovery — Full Detail

Detail supporting [`../SKILL.md`](../SKILL.md) §2, §3, §8, §11, §12 and the concurrency limits in §1. Read those sections
first for the one-line defect summaries and when each fix applies; this file carries the full
defensive code.

---

## 1. Creating the root package

### Root package parent (REQ-001) — fixed in v1.0.0

EA's repository root can be at parent ID 0 or 1 depending on how the project was created.
Always confirm the correct parent before creating your top-level package:

**Correct approach:**
```
ea_model(operation="list_root_packages", params={})
# → find the ID of your intended parent (often 0 or 1 depending on server version)
ea_model(operation="create_package", params={"name": "WestbrookBank", "parent_package_id": <root_id>})
```

After creation, **verify** with SQL:
```
ea_analyze(operation="execute_sql", params={"sql": "SELECT Package_ID, Name, Parent_ID FROM t_package WHERE Name = 'WestbrookBank'"})
```

If `Parent_ID` is `1` but you wanted `0`, fix it immediately:
```
ea_analyze(operation="execute_sql", params={"sql": "UPDATE t_package SET Parent_ID = 0 WHERE Name = 'WestbrookBank'"})
```

(On the demo model a root package's mirror object sits in package 1 whether the package's
`Parent_ID` is 0 or 1, so this one change needs no matching edit. For any other move, see §5.)

This fix must be done before building any child packages — child `Parent_ID` values are set
at creation time and will be correct relative to their parent regardless of the root fix.

---

## 2. Package names containing `&`

### Ampersand encoding (REQ-002) — fixed in v1.0.0

EA's COM layer HTML-encodes `&` on some paths. A package named `"Operations & Support"`
may be stored as `"Operations &amp; Support"`, breaking all path-based lookups.

**Defensive pattern — always verify after creating a package whose name contains `&`:**

```python
# 1. Create the package (name will be stored with &amp;)
result = ea_model(operation="create_package", params={"name": "Operations & Support", "parent_package_id": <id>})
pkg_id = result["package_id"]

# 2. Verify stored name
ea_analyze(operation="execute_sql", params={"sql": f"SELECT Name FROM t_package WHERE Package_ID = {pkg_id}"})
# → will show "Operations &amp; Support"

# 3. Fix immediately with update_package
ea_model(operation="update_package", params={"package_id": pkg_id, "properties": {"Name": "Operations & Support"}})

# 4. Re-verify
ea_analyze(operation="execute_sql", params={"sql": f"SELECT Name FROM t_package WHERE Package_ID = {pkg_id}"})
# → should now show "Operations & Support"
```

**Affected characters:** `&` → `&amp;`. Also watch for `<`, `>`, `"` if they appear in
names.

---

## 3. Element placement and package tree counts

### The recursive count problem

Tests (and EA's own metrics) count elements **recursively** through a package tree. The
total for a capability area includes all elements in all sub-packages at every depth.

**Critical placement rule:** Services and shared infrastructure elements that have a
conceptual "home" in one capability area but serve multiple areas should be placed in a
**top-level capability package** or in a shared infrastructure package — NOT inside a
sub-package of the capability area that happens to own them.

Placing a service inside a sub-package adds it to the recursive count of every ancestor
package, which can push parent-level counts above their expected bounds.

**How to check before placing an element:**

1. Find the target package's current recursive count:
```
-- Step 1: collect every package id in the subtree (any depth):
ea_model("list_package_tree", {"root_package_id": <pkg_id>, "include_element_counts": true})
-- Step 2: count the elements in those packages, leaving out the package mirror rows:
SELECT COUNT(*) AS n FROM t_object WHERE Package_ID IN (<pkg_id>, <child1>, <child2>, ...)
  AND Object_Type <> 'Package'
```

`list_package_tree` follows `Parent_ID` to any depth (`max_depth`, default 10), so the id list is
complete. `WITH RECURSIVE` also works on a SQLite model file and the server does not block it, but
it has not been run through EA's own query call; `sql_schema.md` §7 has the form. Without the
`Object_Type` filter, each child package adds one to the count.

2. Compare the count with the range the person gave you, or with the count you took before the
build. If the element would push it above the upper bound, find another package. If nobody gave a
range and you took no earlier count, report the count and say there was no range to check against.

---

## 4. Idempotency — check before creating

Never assume the repository is empty. Always check for prior existence before creating:

```python
# Check package
ea_analyze(operation="execute_sql", params={"sql": "SELECT Package_ID FROM t_package WHERE Name = 'WestbrookBank' AND Parent_ID = 0"})

# Check element
ea_model(operation="find_elements_by_name", params={"name": "Customer Portal", "exact": True})
# or:
ea_analyze(operation="execute_sql", params={"sql": "SELECT Object_ID FROM t_object WHERE Name = 'Customer Portal' AND Package_ID = <pkg_id>"})

# Check connector
ea_analyze(operation="execute_sql", params={"sql": """
    SELECT Connector_ID FROM t_connector
    WHERE Start_Object_ID = <src> AND End_Object_ID = <tgt> AND Stereotype = 'Uses'
"""})
```

If the entity already exists, skip creation and record its existing ID.

---

## 5. Error recovery patterns

### Partial build recovery

If a build session is interrupted mid-way:
1. Call `ea_repository(operation="get_repository_info", params={})` and `ea_model(operation="list_root_packages", params={})` to confirm the EA connection.
2. Use SQL to audit what has been created vs. what the spec requires:
   ```sql
   SELECT COUNT(*) AS n FROM t_object WHERE Stereotype LIKE 'WBA%'
   SELECT COUNT(*) AS n FROM t_package WHERE ea_guid IS NOT NULL
   ```
3. Compare counts against the spec. Identify the last completed element.
4. Resume from the next element in the build order — do not rebuild already-created content.

### Check every write's result, not only `ok`

`ea_rejected_write` means EA refused the write, and `detail` has EA's reason. An update that
supplies nothing, or whose properties are all rejected, returns `ok: false`
(`no_properties_given`, `nothing_applied`) and carries `changed: <n>`; a partial update is
`ok: true` with the refused properties in `rejected_properties` and `rejected_tagged_values`.
`sql_result_unreadable` means a read could not be parsed (for example it was too large): narrow
the query, and do not read it as "no rows". `duplicate_package` returns `partial: true` and
`rejected_writes` when EA refuses part of the copy. An unknown id returns a `*_not_found` result
(`element_not_found`, `package_not_found`, `connector_not_found` and so on); an empty tag list now
means the element has no tags. These results come from server 3.6.5 or later.

### Fixing a wrong name

Use `ea_model("update_package")` or `ea_model("update_element")` immediately. Both take the
new value inside `properties`, not as a top-level `name`:
```
ea_model(operation="update_package", params={"package_id": <id>, "properties": {"Name": "Correct Name"}})
```
Then re-verify with SQL.

### Fixing a wrong parent (package in wrong location)

There is no `move_package` operation. A package is stored twice: a `t_package` row, and a mirror
`t_object` row (`Object_Type = 'Package'`, the same `ea_guid`) whose `Package_ID` is the id of
the package that contains it. A raw edit of `t_package.Parent_ID` alone leaves the mirror in the
old place, and the package tree and its twin record disagree. Move **both**, then read both back.

1. Get the package's GUID and note its contents count:
   ```
   ea_analyze(operation="execute_sql", params={"sql": "SELECT Package_ID, ea_guid, Parent_ID FROM t_package WHERE Package_ID = <id>"})
   ea_analyze(operation="execute_sql", params={"sql": "SELECT COUNT(*) AS n FROM t_object WHERE Package_ID = <id>"})
   ```
2. Update both records (two calls, same new parent id):
   ```
   ea_analyze(operation="execute_sql", params={"sql": "UPDATE t_package SET Parent_ID = <new_parent> WHERE Package_ID = <id>"})
   ea_analyze(operation="execute_sql", params={"sql": "UPDATE t_object SET Package_ID = <new_parent> WHERE Object_Type = 'Package' AND ea_guid = '<guid from step 1>'"})
   ```
3. Read both back; the two numbers must be equal and equal the new parent:
   ```
   ea_analyze(operation="execute_sql", params={"sql": """
       SELECT p.Package_ID, p.Parent_ID, m.Object_ID, m.Package_ID AS mirror_parent
       FROM t_package p
       JOIN t_object m ON m.ea_guid = p.ea_guid AND m.Object_Type = 'Package'
       WHERE p.Package_ID = <id>"""})
   ```
   Then re-run the contents count from step 1: it must be unchanged.
4. A raw write does not reach an EA session that already has the package cached. Ask the
   person to reload the package in the Browser (right-click it, *Contents*, *Reload Current
   Package*) or reopen the model.

If the write is refused (a permission layer in your client can refuse `execute_sql` writes),
stop and ask the person to approve it, or to move the package in EA itself by dragging it in
the Project Browser. Do not report the package as moved until step 3 shows both records at the
new parent. When a `move_package` operation exists, use it instead.

Or delete and recreate the package, which is only viable if it has no children yet.

### Fixing a connector stereotype

To remove a stereotype from a connector, clear it through `properties`, not a top-level
`stereotype` key:
```
ea_model(operation="update_connector", params={"connector_id": <id>, "properties": {"StereotypeEx": ""}})
```
Then verify with SQL that `Stereotype` is blank in `t_connector`.

---

## 6. Concurrency limits, per operation

EA's COM layer is single-threaded and serializes every call; parallel writes race in its
internal caches. Run all writes one at a time.

| Operation | Max parallel calls | Notes |
|---|---|---|
| `ea_model("create_package")` | 1 (sequential only) | The package tree is not thread-safe |
| `ea_model("create_element")` / `ea_model("create_elements_bulk")` | 1 at a time | Bulk is preferred over many parallel singles |
| `ea_model("create_connector")` / `ea_model("create_connectors_bulk")` | 1 at a time | Same COM constraint |
| `ea_analyze("execute_sql")` (read-only) | Up to ~3 | Safer, still best kept sequential |
| `ea_model("get_element")`, `ea_model("get_package")`, `ea_diagram("get_diagram")` | Up to ~3 | Read-only; usually safe |
