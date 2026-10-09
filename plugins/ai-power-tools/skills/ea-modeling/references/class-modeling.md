# Class-Level Modeling — Attributes, Operations, Parameters

Detail supporting [`../SKILL.md`](../SKILL.md) §4 (element creation). Read that section first for
the create-element decision points; this file covers the next layer down — attributes,
operations, and operation parameters on an already-created element.

All calls are `ea_model(operation="<name>", params={...})`.

---

## 0. The identifier map — read this before calling anything here

Attributes and operations each expose **two different identifiers** in every response
(`create_*`, `list_*`, `update_*` all return both). Which call needs which one is not
consistent, and guessing wrong fails immediately with `missing_required_params`:

| Object | Small int field | GUID field | `update_*` wants | `delete_*` wants |
|---|---|---|---|---|
| Attribute | `attribute_id` (= `t_attribute.ID`) | `guid` (= `t_attribute.ea_guid`) | `attribute_guid` | `element_id` + `attribute_id` |
| Operation | `method_id` (= `t_operation.OperationID`, **not** `t_method`) | `guid` (= `t_operation.ea_guid`) | `method_guid` | `element_id` + `method_id` |
| Parameter | `parameter_id` — always **`null`** in `list_operations`, omitted entirely from `add_parameter`'s own response (see §4) | `guid` (= `t_operationparams.ea_guid`) | no dedicated update op exists | no dedicated delete op exists |

**Confirmed live, both objects:** `update_attribute` takes `attribute_guid`; `delete_attribute`
takes `element_id` + `attribute_id`. `update_operation` takes `method_guid`; `delete_operation`
takes `element_id` + `method_id`. Same split, same shape, on both object kinds — this is not a
one-off inconsistency, it's the pattern. Expect it to bite the first time you write generic
"update this thing I just created" code that assumes one id serves both calls.

Where the ids come from in practice:
- **Right after `create_attribute` / `create_operation`:** both ids are in the response already
  — no extra call needed.
- **Any other time:** call `list_attributes` / `list_operations` (§3) and read `attribute_id` /
  `guid` (or `method_id` / `guid`) off the row you want. Match by `name`, since there is no
  find-by-name for attributes or operations.

`t_operation` is the real EA table (`OperationID` primary key). **`t_method`** also exists in
this schema (`describe_table("t_method")` returns it) but is unrelated to operations — it has
only `Object_ID, Name, Scope, Type` and no id column at all. Don't be misled by the name; the
tool's `method_id` field is an `ea_model` naming choice, not a pointer into `t_method`.

---

## 1. Worked sequence

Carrier elements per canon (`_shared/references/westbrook-example.md` §2): `WBADataAsset` and
`WBAAIModel` are both declared **Class** metaclass, and that is the metaclass
`create_element_in_language` resolves for each.

### 1a. Create the carrier element

```python
ea_model(operation="create_element_in_language", params={
    "package_id": pkg_id,
    "name": "CustomerRiskProfile",
    "language_id": "WBA",
    "language_type": "WBADataAsset",
})
# -> "resolved_object_type": "Class", "resolved_stereotype": "WBADataAsset",
#    "definition_source": "model"
```

> **Pass the registered technology id.** `WBA` is what EA registers and what
> `create_element_in_language` resolves against; `WestbrookBankArchitecture` is the display name
> of the profile inside it. Check the id with `ea_mdg(operation="get_mdg_from_runtime",
> params={"tech_id": "WBA"})` — the stereotype list it returns is read out of the technology EA
> has loaded, and `definition_source` on the creation response echoes where the resolution came
> from.

The same call creates every other carrier the technology declares, `WBAAIModel` included:

```python
ea_model(operation="create_element_in_language", params={
    "package_id": pkg_id,
    "name": "FraudScoringModel",
    "language_id": "WBA",
    "language_type": "WBAAIModel",
})
# -> "resolved_object_type": "Class", "resolved_stereotype": "WBAAIModel"
```

Everything below (attributes, operations, parameters) works identically regardless of which path
created the element — these operations key off `element_id`, not off how the element was made.

### 1b. Attributes — with type and default

```python
ea_model(operation="create_attribute", params={
    "element_id": elem_id,
    "name": "assetId",
    "type": "String",
    "default": "UNSET",
})
# -> {"ok": true, "attribute_id": 2, "guid": "{...}", "name": "assetId",
#     "type": "String", "default": "UNSET", ...}
```

The top-level `default` param (alias: `default_value`) sets `t_attribute.Default` directly and is
the recommended form. `properties={"Default": "UNSET"}` also works and takes precedence if both
are supplied in the same call — but there's no reason to reach for `properties` for this one
field. Use the raw EA column name inside `properties` for anything else beyond
`name`/`type`/`element_id` — same pattern as `update_element` elsewhere in this skill. `Default`,
`Type`, `Scope`, and `Const` are reserved words in `t_attribute` (bracket them in raw SQL, but
that doesn't apply to the `properties` dict keys — those are just the column names).

### 1c. Operations — with a return type

```python
ea_model(operation="create_operation", params={
    "element_id": elem_id,
    "name": "validate",
    "properties": {"ReturnType": "Boolean"},
})
# -> {"ok": true, "method_id": 2, "guid": "{...}", "name": "validate",
#     "return_type": "Boolean", "parameters": [], ...}
```

`Notes` works the same way (`properties={"ReturnType": "void", "Notes": "..."}` in one call).
Note the response key is `return_type` (snake_case, normalized) while the property you set it
with is `ReturnType` (EA's raw property name) — the tool renames on the way out but not on the
way in.

### 1d. Parameters

```python
ea_model(operation="add_parameter", params={
    "element_id": elem_id,
    "method_id": 2,
    "name": "strict",
    "type": "Boolean",
    "default": "true",
})
# -> {"ok": true, "guid": "{B2A7...}", "name": "strict", "type": "Boolean",
#     "kind": "in", "default": "true"}
```

The response has no `parameter_id` field at all — `t_operationparams` has no integer id column,
only a `guid` — so don't look for one. `default` is optional and, when supplied, persists. A call
that raises means nothing was written (see §3b for what can cause that).

---

## 2. What `list_attributes` / `list_operations` return, and how to read them

```python
ea_model(operation="list_attributes", params={"element_id": elem_id})
```

Returns an **array**, one dict per attribute, each shaped exactly like a `create_attribute`
response:

```json
[
  {"attribute_id": 2, "guid": "{DC3E...}", "name": "assetId", "type": "String",
   "default": "UNSET", "visibility": "Public", "notes": "", "stereotype": "",
   "is_static": false, "is_const": false, "is_collection": false, "container": "",
   "containment": "Not Specified", "lower_bound": "1", "upper_bound": "1",
   "classifier_id": 0, "parent_id": 9459}
]
```

`list_operations` is the same shape per-operation, plus a nested `parameters` array:

```json
[
  {"method_id": 2, "guid": "{D9F1...}", "name": "validate", "return_type": "Boolean",
   "notes": "", "visibility": "Public", "stereotype": "", "is_static": false,
   "is_abstract": false, "concurrency": "Sequential", "code": "", "behavior": "",
   "parent_id": 9459,
   "parameters": [
     {"parameter_id": null, "guid": "{B2A7...}", "name": "strict", "type": "Boolean",
      "kind": "in", "default": "<none>", "notes": "", "position": 0}
   ]}
]
```

Reading it:
- There is **no `find_attributes_by_name` / `find_operations_by_name`.** To get an id or guid for
  an attribute/operation you didn't just create, call `list_attributes`/`list_operations` for the
  owning element and filter by `name` yourself.
- Order matches EA's internal `Pos` column — the order the browser would show, not creation
  order if any have been reordered since.
- `parameter_id` is **always `null`** in `list_operations` — `t_operationparams` has no integer id
  column, so there is nothing for this field to ever hold. Use the parameter's `guid` or its
  `name` (unique per operation — see §3b) if you ever need to refer back to one.
- An unset attribute/parameter default reads back as `""` immediately after creation in the tool
  response, but as the **literal string `"<none>"`** if you read it back later (via
  `update_operation`'s echo, or via raw SQL on `t_operationparams.Default` /
  `t_attribute.Default`). `<none>` is EA's own placeholder text for "no default set", not a bug in
  the wrapper — but the inconsistency between what a fresh create response shows (`""`) and what
  a later read shows (`"<none>"`) is worth knowing before you write a check like
  `if default == "":`.

---

## 3. Failure modes actually hit

### 3a. Setting a default on an attribute or parameter

Use the top-level `default` param on `create_attribute` (alias `default_value`) or on
`add_parameter` — both honor it and it persists. `properties={"Default": ...}` still works for
`create_attribute` too (and wins if you somehow pass both in the same call), but there's no reason
to reach for it just for this one field. See §1b and §1d for worked examples.

### 3b. `add_parameter` — no throw, no phantom id, and what a raised error actually means

`add_parameter` does not raise for a normal, successful write. Its response has **no
`parameter_id` field at all** — not `null`, simply absent — because `t_operationparams` has no
integer id column; the response carries `guid` instead. `default`, when supplied, persists (see
§3a) and reads back correctly in the same call.

A raised error here means the write did not happen — verified by refreshing and reading the
operation's `Parameters` collection back before reporting success, not by trusting the write call
in isolation. Two ways this can happen:
- An unknown `method_id`.
- **A parameter name that already exists on the same operation.** EA does not raise for this and
  does not overwrite the existing row in place — it silently no-ops the second write. A second
  `add_parameter` call for a name already present on that operation therefore raises here rather
  than reporting a false success or quietly creating nothing. If you actually want to change an
  existing parameter, there is no update op for it (§3d) — recreate the owning operation, or drop
  to raw SQL against `t_operationparams`.

Retrying after a raised error is safe in the sense that it cannot silently duplicate or silently
overwrite anything — either nothing was written and the retry is a normal second attempt, or the
name collides with something already there and the retry raises again for the same reason. It is
not useful to retry the exact same call expecting a different outcome, though: nothing about a
plain retry changes an unknown `method_id` or an already-taken name.

### 3c. `create_element_in_language` fails outright for a stereotype the technology doesn't declare

`unknown_language_type` is a hard stop, not a partial write — nothing is created. Check
`ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "WBA"})` first if a `language_type`
you expect might not be one the loaded technology declares.

### 3d. There is no `update_parameter` or `delete_parameter`

`ea_model`'s operation list (confirmed by calling each with empty `params` and reading the
`valid_operations` list back in the error) has no dedicated parameter update or delete call.
`add_parameter` is the only parameter-mutating operation, and it is **not** an upsert — a name
that already exists on the operation raises rather than updating the existing row (§3b). To change
or remove a parameter, either recreate the owning operation or drop to raw SQL
(`UPDATE`/`DELETE ... FROM t_operationparams WHERE OperationID = ? AND Name = ?`) — there is no
MCP-level update or delete for this one object kind, unlike every other object covered in this
file.

### 3e. `execute_sql` can time out on a live, shared repository

One verification query (`t_operation` joined to `t_operationparams` with no `WHERE`) timed out
outright while EA was in active use elsewhere. Scope SQL verification queries with a `WHERE`
clause on a known `Object_ID`/`OperationID` rather than joining broad tables unfiltered, especially
against a repository other sessions may also be touching.

---

## 4. Verification checklist for a new attribute/operation

After any create or update, don't trust the echoed response for anything you didn't explicitly
set — confirm with a targeted `list_attributes`/`list_operations` call, or SQL scoped to the one
`element_id`/`OperationID` you touched:

```sql
SELECT ID, Object_ID, Name, [Type], [Default] FROM t_attribute WHERE Object_ID = <element_id>;
SELECT OperationID, Object_ID, Name, [Type] FROM t_operation WHERE Object_ID = <element_id>;
SELECT OperationID, Name, [Type], [Default] FROM t_operationparams WHERE OperationID = <method_id>;
```

`[Default]`, `[Type]`, `[Scope]`, `[Const]`, `[Kind]` are reserved words across these tables —
bracket them in raw SQL (see `ea_analyze("describe_table")` for the full reserved-word list per
table).
