# Packages, Known Defects, Idempotency, and Error Recovery — Full Detail

Detail supporting [`../SKILL.md`](../SKILL.md) §2, §3, §8, §11, and §12. Read those sections
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
```sql
-- Step 1: collect all package IDs in the subtree
-- (recursive CTE not available in EA's SQLite — use repeated queries or execute_sql loop)
SELECT COUNT(*) FROM t_object WHERE Package_ID IN (<pkg_id>, <child1>, <child2>, ...)
```

2. Compare against the test's expected range. If the element would push the count above
the upper bound, find an alternative package.

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
   SELECT COUNT(*) FROM t_object WHERE Stereotype LIKE 'WBA%'
   SELECT COUNT(*) FROM t_package WHERE ea_guid IS NOT NULL
   ```
3. Compare counts against the spec. Identify the last completed element.
4. Resume from the next element in the build order — do not rebuild already-created content.

### Fixing a wrong name

Use `ea_model("update_package")` or `ea_model("update_element")` immediately. Both take the
new value inside `properties`, not as a top-level `name`:
```
ea_model(operation="update_package", params={"package_id": <id>, "properties": {"Name": "Correct Name"}})
```
Then re-verify with SQL.

### Fixing a wrong parent (package in wrong location)

There is no `move_package` tool in v1. Options:
1. `ea_analyze(operation="execute_sql", params={"sql": "UPDATE t_package SET Parent_ID = <correct_parent> WHERE Package_ID = <id>"})` — direct SQL fix, verify afterward.
2. Delete and recreate the package (only viable if it has no children yet).

### Fixing a connector stereotype

To remove a stereotype from a connector, clear it through `properties`, not a top-level
`stereotype` key:
```
ea_model(operation="update_connector", params={"connector_id": <id>, "properties": {"StereotypeEx": ""}})
```
Then verify with SQL that `Stereotype` is blank in `t_connector`.
