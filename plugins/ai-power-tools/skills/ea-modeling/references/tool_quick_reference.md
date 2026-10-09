# Quick Reference: Most-Used Tools

Full tool index supporting [`../SKILL.md`](../SKILL.md) §14. See the numbered sections of
`SKILL.md` for the decision points behind each row; this table is the cheat-sheet, not the
explanation.

| Task | Tool | Notes |
|------|------|-------|
| Orient in repo | `ea_model("list_root_packages")` | Always first |
| Get repo info | `ea_repository("get_repository_info")` | Confirms EA connection; check before any writes |
| Create package | `ea_model("create_package")` | Verify `&` names (may encode as `&amp;`) |
| Create one element | `ea_model("create_element")` | Pass `properties=`, `tagged_values=` inline |
| Create MDG element | `ea_model("create_element_in_language")` | Resolves the base metaclass; prefer over `create_element` for MDG types. No `tagged_values` — tag after with `update_element` |
| Create many elements | `ea_model("create_elements_bulk")` | Idempotent; use for >5; supports `language_id`+`language_type` per spec |
| Set one tag | `ea_model("set_tagged_value")` | Use only for after-the-fact updates |
| Create connector | `ea_model("create_connector")` | Verify endpoints exist first |
| Create many connectors | `ea_model("create_connectors_bulk")` | Idempotent |
| Create diagram | `ea_diagram("create_diagram")` | Then `ea_diagram("update_diagram")` StyleEx |
| Create MDG diagram | `ea_diagram("create_diagram_in_language")` | Sets base type + StyleEx in one call |
| Add one element to diagram | `ea_diagram("add_element_to_diagram")` | Use for one-offs |
| Add many to diagram | `ea_diagram("add_elements_to_diagram_bulk")` | Idempotent; use for ≥3 |
| Bulk verify | `ea_analyze("execute_sql")` | Most reliable tool; use liberally |
| Describe table schema | `ea_analyze("describe_table")` | Use before writing non-trivial SQL |
| Fix names | `ea_model("update_package")` / `ea_model("update_element")` | Works even in v1 |
| Fix parent | `ea_analyze("execute_sql")` UPDATE | Only way in v1 for packages |
| Layout diagram | `ea_diagram("layout_diagram")` | Called automatically by `ea_diagram("add_elements_to_diagram_bulk")` |
| Repair connector lines | `ea_diagram("add_connectors_to_diagram_bulk")` | Run when connector lines are missing from a diagram |
| Summarize model | `ea_analyze("summarize_stereotype_usage")` | Token-cheap repo overview |

**Default response shape:** mutating tools return a minimal `{ok, *_id, guid, name, applied_*}`
envelope. Pass `verbose=True` only if you actually need the full serialization in the
response — see [`token_and_session_management.md`](token_and_session_management.md).
