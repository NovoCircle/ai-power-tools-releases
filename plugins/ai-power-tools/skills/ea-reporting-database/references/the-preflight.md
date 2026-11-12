# The preflight (paths B and C)

The long form of `SKILL.md` §5.3. The preflight reads EA's tables over COM, applies the scope, and
**writes nothing**. Direct access (path A) has no preflight operation: the rights are checked first
and the inclusion census (§2b) finds unbound connectors.

```
ea_repository(operation="build_reporting_database", params={"profile_path": "<profile>.json", "preflight_only": true})
```

## What it reports

The rows extracted and kept, and the **crossings**: links from kept content into an excluded area,
by kind (connector, diagram placement, classifier, parent, or a tagged value naming an excluded
element) and the `(excluded)` stubs they need. Then two lists.

## `blocking`: stop

A connector whose stereotype is qualified text with no binding to the technology
(`connector_stereotype_unbound`). Do **not** build while this list is non-empty, on either path.

The fix, with a baseline first (`ea-change-management`), by either route:

- `update_connector` with `StereotypeEx` set to the technology's qualified name for the stereotype;
- or, in EA, re-apply the stereotype from the technology's toolbox, or through Properties >
  Stereotype.

Then run the preflight again. Either route writes to the model.

## `flags`: show, then ask

- `element_multiple_declared_stereotypes`: elements carrying two of the technology's stereotypes.
  If the user continues, each is in both tables; if it is a mistake, remove the extra stereotype in EA.
- `new_root_left_out`: a root package created since the profile was saved. It is not included until the
  user adds it to `roots`, or names it in `exclude` to record the decision.
- `profile_entry_matches_nothing`: an exclusion (or root) naming a package that no longer exists.
- `duplicate_tag_names`: elements with two same-named tags; the layer shows the first.
