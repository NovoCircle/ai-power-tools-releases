# EA MCP operations reference

**Generated — do not edit by hand.** Produced by `tools/gen-operations.py` from the
server's dispatch tables. Re-run it after any server change rather than editing here.

Server version: `3.6.0` · 144 operations across 6 meta-tools.

Every operation is called the same way:

```
<meta_tool>(operation="<name>", params={"arg": value, ...})
```

All arguments go inside `params`. Passing them as top-level keys is the single most
common call error and produces a format error, not a result.

If an operation is not in this list, it does not exist. Do not infer one from a pattern.

---

## `ea_model` — 50 operations

| Operation | What it does |
|---|---|
| `add_parameter` | Add a parameter to an operation. |
| `create_attribute` | Add an attribute to an element. |
| `create_connector` | Create a connector from client (source) to supplier (target). |
| `create_connectors_bulk` | Create multiple connectors in one call with idempotency built in. |
| `create_element` | Create a new element in the given package. |
| `create_element_in_language` | Create an element using a language-qualified type. |
| `create_elements_bulk` | Create multiple elements in one call with idempotency built in. |
| `create_external_reference_element` | Create a placeholder element representing an object in an external system, with the four standardized tagged values applied automatically. |
| `create_operation` | Add an operation to an element. |
| `create_package` | Create a new package under the given parent. |
| `delete_attribute` | Delete an attribute from its parent element. |
| `delete_connector` | Permanently delete a connector. |
| `delete_connector_tagged_value` | Delete a tagged value from a connector by name. |
| `delete_element` | Permanently delete an element. |
| `delete_operation` | Delete an operation from its parent element. |
| `delete_package` | Permanently delete a package and everything inside it (elements, diagrams, nested packages). |
| `delete_tagged_value` | Delete a tagged value from an element by name. |
| `duplicate_package` | Duplicate a package subtree with fresh GUIDs on every package, element, attribute, and operation it contains -- the API equivalent of EA's UI-only "Paste as New" action, which has no COM route (see the section comment above this function for what was checked). |
| `find_composite_diagram_mismatches` | Audit a package (optionally its whole subtree) for elements where the two halves of the composite-diagram mechanism disagree. |
| `find_elements_by_name` | Find elements by name. |
| `find_orphan_elements` | Find elements with no connectors (orphans). |
| `find_packages_by_name` | Find packages by name. |
| `get_connector` | Fetch a connector (relationship) by ID or GUID. |
| `get_connector_tags` | Return all tagged values on a connector across EA's tag stores. |
| `get_connectors_for_element_filtered` | SQL-based connector lookup with direction and type filtering. |
| `get_current_selection` | Return currently-selected elements in the current diagram. |
| `get_element` | Fetch an element by ID or GUID. |
| `get_element_tags` | Return all tagged values on an element across EA's three tag stores. |
| `get_package` | Fetch a package by ID or GUID. |
| `list_attributes` | List all attributes on an element. |
| `list_child_packages` | List immediate child packages of a given package. |
| `list_connector_tagged_values` | List all tagged values on a connector. |
| `list_connectors_for_element` | List all connectors attached to an element (both directions). |
| `list_elements_in_package` | List elements directly contained in a package. |
| `list_operations` | List all operations (methods) on an element, including their parameters. |
| `list_package_tree` | Recursively walk the package hierarchy under `root_package_id`. |
| `list_root_packages` | List all root-level packages (top-level models) in the repository. |
| `list_tagged_values` | List all tagged values on an element. |
| `move_element` | Move an element to a different package. |
| `select_element_in_browser` | Highlight an element in EA's Browser (project tree). |
| `set_composite_diagram` | Set or clear an element's composite (navigation/drill-down) diagram link, writing both halves of the mechanism together so they can never land out of sync (APT-2026-0059). |
| `set_connector_tagged_value` | Create or update a tagged value on a connector. |
| `set_element_appearance` | Set an element's DEFAULT appearance -- background color, font color, border color, border width -- through `Element.SetAppearance`. |
| `set_tagged_value` | Create or update a tagged value on an element. |
| `traverse_element_subgraph` | Return a compact subgraph N hops out from element_id. |
| `update_attribute` | Update an attribute by its GUID. |
| `update_connector` | Update properties on a connector. |
| `update_element` | Update properties on an element. |
| `update_operation` | Update an operation by GUID. |
| `update_package` | Update properties on an existing package. |

---

## `ea_diagram` — 41 operations

| Operation | What it does |
|---|---|
| `add_connectors_to_diagram_bulk` | Add connectors to a diagram's visual layer (t_diagramlinks). |
| `add_element_to_diagram` | Place an existing element on a diagram. |
| `add_elements_to_diagram_bulk` | Place multiple existing elements on a diagram in one call. |
| `add_image` | Load an image FILE into the model's image library (`t_image`) and return its `image_id`, ready to pass to `set_element_image`. |
| `clear_element_image` | Stop drawing a placed element as a custom image, KEEPING the artwork in the model's image library. |
| `collapse_parallel_connectors` | Hide duplicate connectors between the same pair of elements. |
| `create_diagram` | Create a new diagram in a package. |
| `create_diagram_in_language` | Create a diagram using a language-qualified diagram type. |
| `delete_diagram` | Permanently delete a diagram. |
| `expand_parallel_connectors` | Un-hide every hidden link on a diagram -- the inverse of collapsing. |
| `export_diagram_image` | Export a diagram to an image file. |
| `export_diagram_to_visio` | Export a diagram to a Microsoft Visio (.vsdx) file. |
| `find_diagrams_by_name` | Find diagrams by name. |
| `find_icon` | Search the cloud and data-platform icon libraries that ship WITH THE USER'S OWN EA INSTALL for icons by name, ready to pass to `set_element_icon`. |
| `get_current_diagram` | Return the diagram currently open/focused in the EA UI, or None. |
| `get_diagram` | Fetch a diagram with an inline PNG preview. |
| `get_diagram_display` | Read a diagram's display settings, decoded across all three surfaces. |
| `get_diagram_link` | Read one connector's presentation on one diagram, decoded. |
| `get_diagram_png` | Render a diagram as PNG and return the bytes inline. |
| `get_diagram_svg` | Render a diagram as SVG and return the markup inline. |
| `layout_diagram` | Apply an auto-layout to a diagram using EA's Project.LayoutDiagramEx(). |
| `list_diagrams_in_package` | List diagrams in a package, optionally walking children. |
| `list_images` | List what the model's image library (`t_image`) already holds, with enough detail to pick one for `set_element_image`. |
| `neaten_diagram_objects` | Align elements that are ALMOST aligned, so the arrangement reads as deliberate. |
| `open_diagram` | Open a diagram in the EA UI (user-visible). |
| `reload_diagram` | Force a diagram to redraw (useful after bulk edits). |
| `remove_element_from_diagram` | Remove an element's placement from a diagram. |
| `resize_diagram_objects` | Give a selection one size, so varying size stops implying varying importance. |
| `set_custom_style` | Change HOW one placed element is DRAWN on ONE diagram -- its shape, opacity, text alignment, text rotation, border style, or card stack. |
| `set_custom_styles_bulk` | Apply Custom Style to many placements on one diagram in a single write. |
| `set_diagram_display` | Set how a whole diagram is displayed. |
| `set_diagram_link` | Set how one connector is drawn on one diagram. |
| `set_diagram_links_bulk` | Set presentation for many connectors on one diagram in a single pass. |
| `set_diagram_object` | Reposition and/or restyle an element that is ALREADY placed on a diagram, without removing and re-adding it. |
| `set_diagram_object_appearance` | Style ONE element ON ONE DIAGRAM. |
| `set_diagram_objects_appearance_bulk` | Style many elements on one diagram in a single pass. |
| `set_diagram_objects_bulk` | Reposition and/or restyle multiple elements already placed on a diagram in one call. |
| `set_element_icon` | Draw ONE placed element as an icon from EA's own shipped icon libraries, ON ONE DIAGRAM. |
| `set_element_image` | Draw ONE placed element as a custom image ON ONE DIAGRAM. |
| `update_diagram` | Update a diagram's properties. |
| `verify_diagram` | Reload a diagram, render it, and return the image WITH the full placed geometry -- the one call an automated quality check should use. |

---

## `ea_analyze` — 13 operations

| Operation | What it does |
|---|---|
| `describe_table` | Return canonical column names, types, PK, and gotcha notes for an EA repository table (``t_object``, ``t_taggedvalue``, etc.). |
| `execute_sql` | Execute a raw SQL query against the EA repository. |
| `find_paths` | Return every SHORTEST path between two elements, as alternating element/connector hops. |
| `get_element_business_view` | Return a complete, business-language view of an element. |
| `get_traceability_tree` | Return a rooted tree of everything reachable from ``root_id`` along one set of connector types, in one direction. |
| `get_updates_in_range` | Return packages, elements, or diagrams created or modified in a date range. |
| `get_user_activity` | Per-user modification counts in a date range. |
| `list_ea_tables` | List every EA repository table known to the MCP server, with PK. |
| `summarize_connector_patterns` | Source-stereotype -> connector-stereotype -> target-stereotype tuples. |
| `summarize_observed_metaclasses` | For a given stereotype, which EA Object_Types host it. |
| `summarize_stereotype_usage` | Stereotype + Object_Type frequency table for the whole repository. |
| `summarize_tagged_value_usage` | Tagged value usage frequencies, optionally scoped to a stereotype. |
| `trace_connectors` | Return the connected subgraph N hops from ``element_id`` as compact nodes + edges. |

---

## `ea_mdg` — 12 operations

| Operation | What it does |
|---|---|
| `assess_mdg_situation` | Classify the MDG state of the connected repository. |
| `get_embedded_mdgs` | List the MDG technologies stored in the open model. |
| `get_mdg_from_runtime` | Return the stereotype, tagged value and diagram type definitions of the technology EA actually has loaded -- or decline to answer. |
| `get_mdg_search_paths` | Return EA's configured MDG technology search-path directories (Manage Technology > Advanced tab). |
| `install_mdg` | Install an MDG technology into the EA environment. |
| `list_available_modeling_languages` | Enumerate modeling languages available in the connected EA instance. |
| `list_registered_technologies` | Enumerate every technology EA's Manage Technology dialog would show -- name, version, location, and enabled state -- including disabled ones, so a build/deploy workflow can spot the exact failure mode a real customer report hit: a technology registered on the author's workstation silently shadowing (and drifting ahead of, or behind) the model's own copy, with no operation previously surfacing registration/ location/enabled state to make that visible. |
| `parse_mdg_xml` | Parse MDG XML (file path or raw string) into the intermediate format. |
| `publish_package_as_profile` | Publish a package as a UML Profile XML file, with an explicit `version` -- the scriptable equivalent of `Specialize > Publish Technology > Publish Package as UML Profile`. |
| `resolve_display_term` | Translate a technical stereotype/tag name to its business alias. |
| `set_active_mdg` | Record a preferred MDG for the session. |
| `write_mdg_xml` | Emit valid MDG XML from a normalized intermediate metamodel dict. |

---

## `ea_validate` — 1 operations

| Operation | What it does |
|---|---|
| `audit` | Run a YAML sidecar conformance ruleset against the current model. |

---

## `ea_repository` — 27 operations

| Operation | What it does |
|---|---|
| `aggregate_portfolio` | Group elements by tagged value for portfolio reporting. |
| `apply_baseline` | Roll back a package to a prior baseline (destructive). |
| `build_business_layer` | Build the business layer as SQL Server views, from a reporting profile. |
| `build_reporting_database` | Build a SQL Server reporting database from the open repository over COM, for a repository with no direct database access. |
| `check_business_layer` | Check a built business layer without changing it: alignment with the metamodel, and every cell against an independent read of EA. |
| `check_for_updates` | Report whether a newer version of ea-mcp-server is available. |
| `close_project` | Close the currently-open project without exiting EA. |
| `compare_baseline` | Compare a package against one of its baselines and return the diff. |
| `create_baseline` | Create a baseline snapshot of a package. |
| `create_model` | Create a new EA model file at `path` and open it. |
| `export_xmi` | Export a package as XMI for cross-tool interchange. |
| `generate_report` | Run an EA-native report template against a package. |
| `get_reporting_refresh` | The status of a refresh started with `start_reporting_refresh`: running, succeeded or failed, and when finished the full result (row counts per table, flags, alignment, timings, or why it stopped). |
| `get_repository_info` | Return metadata about the currently-open EA project: file path, connection string, EA version, number of root packages. |
| `get_skill_update_diff` | Return the local and remote content of a skill file that has a conflict. |
| `import_xmi` | Import XMI into a package. |
| `install_skills` | Install Claude skills from the public skills bundle into the host's skill directory. |
| `launch_ea` | Start Enterprise Architect on the local machine. |
| `list_available_skills` | List the Claude skills available for installation from the public skills bundle (``NovoCircle/ai-power-tools-skills``). |
| `list_baselines` | List baselines registered against a package. |
| `open_model` | Open an existing EA model file (.qea, .qeax, .eap, .eapx) in the running EA instance. |
| `open_project` | Open a .qea, .qeax, .eap, or .eapx project file. |
| `prune_legacy_skills` | Remove skill directories superseded by a rename or withdrawal. |
| `remove_business_layer` | Drop the business layer: every view in the profile's schema, then the schema. |
| `replay_reporting_database` | Rebuild the reporting database from the last run's kept extract, with no EA connection: the same rows, the same technology, the same result. |
| `resolve_skill_conflict` | Resolve a conflict between a locally-edited skill file and the server version. |
| `start_reporting_refresh` | Start a reporting refresh for a saved profile and return at once with a run id; poll it with `get_reporting_refresh`. |

