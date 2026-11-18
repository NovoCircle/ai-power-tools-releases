# YAML Rule Grammar Reference

Full grammar for the rules you write in Phase 3 of `ea-ruleset-author/SKILL.md`. Read
this before writing your first rule, then come back to it whenever you need the exact
shape of a template or table.

---

## Start with the meta block

```yaml
# {Language} Conformance Ruleset
# Language:     {Language full name and version}
# Enforced by:  AI Power Tools for Sparx EA — validate_model tool
#
# Stereotype note:
#   <How EA names the stereotypes for this language>
#
# Sources:
#   [S1] {Primary spec} — {URL}
#   [S2] {Secondary source} — {URL}

meta:
  version: "1.0"
  language: {Language name}
  organization: "(your organization)"
  mdg_family: {MDG family name as it appears in EA's MDG list}
  description: >
    {One paragraph summary of what the ruleset checks.}
  severity_levels:
    error:   {What error means for this language}
    warning: {What warning means}
    info:    Advisory note; not a conformance violation
```

## Rule template

```yaml
  - id: {LANG}-{CAT}-{NNN}
    name: {Short human-readable name}
    description: >
      {2-4 sentences. Explain WHY this rule exists, what spec section it comes
      from, and what the violation means architecturally. Cite your sources.
      Example: "An Assignment relationship must originate from an Active Structure
      element. [S1 §5.2]"}
    category: {category_code_lowercase}
    severity: error        # error | warning | info
    demo_trigger: false    # true for ~30% of rules

    selector:
      type: connector      # connector | element
      connector_stereotype: {StereotypeName}     # for connector selectors
      # OR for element selectors:
      stereotypes:
        any_of: ["{StereotypeName}"]

    condition:
      type: connector_endpoint_stereotype        # see condition types below
      source_must_be_one_of:
        - StereotypeName1
        - StereotypeName2
      target_must_be_one_of:
        - StereotypeName3
      # Leave source_must_be_one_of or target_must_be_one_of out to allow any endpoint on that side.
      # At least one list must be present; an empty list is an error.

    remediation:
      short: >
        {One sentence telling the modeler exactly what to do to fix this.
        Be concrete: "Use Serving instead of Realization here."}
      auto_fixable: false
```

## Condition type reference

| `condition.type` | Use for | Key fields |
|-----------------|---------|-----------|
| `connector_endpoint_stereotype` | Connector source and target stereotype constraints. Leave a list out to allow any endpoint on that side; at least one list must be present and neither may be empty. | `source_must_be_one_of`, `target_must_be_one_of` |
| `relationship_table` | Connector source **and** target, as a pair, against a standard's allowed-relationship table carried in the ruleset | `table`, `skip_endpoints`, `unknown_endpoint` (ignore\|warn\|error); the table lives in the top-level `tables:` |
| `connector_count` | Element must have N connectors of a given stereotype or EA connector type, or, with neither, of any kind | `connector_stereotype` and/or `connector_type`, `direction` (incoming\|outgoing only), `min`, `max` (non-negative whole numbers, `min` not above `max`) |
| `contained_in` | Element must sit in the containers the rule lists, outward | `path`: one step per level, each `stereotype_one_of` and/or `name_one_of` |
| `contains_count` | Element must hold N direct children of a kind | `child` (`stereotype_one_of` and/or `name_one_of`), `min`, `max` |
| `tagged_value_required` | Element or connector must have the tags, non-empty. A tag may carry `value_must_be_one_of`: it must then be present and its value must be in the list. A missing tag and a value outside the list are each a violation; the second names the allowed values. | `tags: [{name, must_be_non_empty}]`, or `tags: [{name, value_must_be_one_of}]` for a mandatory tag with a closed list |
| `tagged_value_constraint` | Tag must be one of an enum when it holds a value; a missing or empty tag passes | `tags: [{name, value_must_be_one_of}]` |

An element selector takes `tagged_value_required`, `tagged_value_constraint`, `connector_count`, `contained_in`, `contains_count` and `tagged_value_type_shipped`. A connector selector takes `relationship_table`, `connector_endpoint_stereotype`, `tagged_value_required` and `tagged_value_constraint`. The tag conditions and `tagged_value_filter` work with a connector selector too; a violation's `element_id` is then the connector id and `element_name` gives the connector's stereotype or type and its two ends, such as `Uses: Customer Portal -> Legacy Ledger`. A finding states what is wrong (`tag lifecycle is Deprecated`), not the rule that was broken.

The condition types `connector_ends`, `related`, `chain`, `any_of`, `all_of`, `not`, `forbidden` and `unique` are in "The extended grammar" below.

A key that a selector or condition does not read is an error (`invalid_rule_shape`, with the field and the allowed list), not something the engine ignores. A rule with no selector, no condition or no `type` is also refused. Rule-level keys such as `implements` and `coverage` are not checked. Run the ruleset through `ea_validate` once and fix every `invalid_rule_shape` before relying on a clean result.

A connector rule is in scope under `package_id` when either end is in the package.

## Writing connector endpoint rules

The most powerful rule type. Write them in this order:

1. List ALL valid source stereotypes (err toward inclusion — EA's MDG may have inherited
   subtypes you don't know about)
2. List ALL valid target stereotypes
3. Write the description explaining WHY these constraints exist
4. Set severity: `error` — endpoint violations are always structural

**EA stereotype names:** write the name as EA stores it, measured against a real model. A bare name (`ArchiMate_Assignment`) matches the stereotype column exactly: a name one character off selects nothing, and a rule that selects nothing reports no violations, which reads like a clean model. A qualified name (`WBA::Uses`, the technology id and the stereotype) matches only items EA binds to that profile, which keeps two languages that share a short name apart. Do not strip a prefix that is part of the stereotype's own name: EA's built-in ArchiMate MDG stores `ArchiMate_Assignment`, so `Assignment` matches nothing. Check `rule_stats` and `rules_examined_nothing` in the result (see the `ea-validation` skill) to catch a name that selected nothing.

In an endpoint list, an entry written `<technology>::<name>` means that technology's element; a bare name matches the stereotype column whichever technology it came from.

| Technology | What `t_object.Stereotype` holds | Selector to write (bare) | Qualified form |
|---|---|---|---|
| EA built-in ArchiMate (1, 2 and 3.1) | `ArchiMate_Assignment` | `ArchiMate_Assignment` | technology id or profile name, then `::ArchiMate_Assignment` |
| EA built-in BPMN2.0 | `BusinessProcess` | `BusinessProcess` | technology id or profile name, then `::BusinessProcess` |
| A custom technology with id `WBA` (Westbrook Bank, an illustration) | `WBABusinessApplication` | `WBABusinessApplication` | `WBA::WBABusinessApplication` |

The first two rows were measured on EA 17.1 build 1716, in the MDG declaration and in stored model
data. So for an ArchiMate ruleset the selector reads:

```yaml
    selector:
      type: connector
      connector_stereotypes: [ArchiMate_Assignment]   # NOT `Assignment`, which matches 0
```

*Measure it, do not infer it.* Run `summarize_stereotype_usage`, or read
`SELECT DISTINCT Stereotype FROM t_object`, against a model actually built with the
technology. Do not take the name from the notation's specification, and do not take it
from the MDG's `metatype` attribute -- `metatype` is the concept name without the prefix,
which is precisely the trap. `rulesets/archimate-3/archimate-3_rules.yaml` carries the
worked measurement in its header, including what the unprefixed form did when it shipped.

*Sanity-check the run.* Zero violations and zero matched elements are the same output.
Confirm a ruleset matched more than zero elements before reporting a model as clean: zero violations is only a pass if `rules_examined_nothing` is empty.

## Writing relationship-table rules

Use this when the language's standard publishes an allowed-relationship table (ArchiMate's
relationship tables, BPMN's connection rules, and so on). An endpoint rule checks the source
and the target separately, so it passes a connector whose two ends are each allowed somewhere
but not together. A relationship-table rule checks the pair.

The table goes in a top-level `tables:` section; one rule then checks every connector:

```yaml
tables:
  archimate-3.1-relationships:
    source: "ArchiMate 3.1 Appendix B, relationship tables"   # required: cite where the table comes from
    connectors:                                               # one letter per connector stereotype
      a: ArchiMate_Access
      r: ArchiMate_Realization
      v: ArchiMate_Serving
    cells:                                                    # source -> target -> allowed letters
      ArchiMate_BusinessProcess:
        ArchiMate_BusinessService: fortv
        ArchiMate_BusinessObject: ao

rules:
  - id: ARCHIMATE-REL-003
    severity: error
    selector:
      type: connector
      connector_stereotypes: any_of_table   # every stereotype the table's `connectors` names
    condition:
      type: relationship_table
      table: archimate-3.1-relationships
      skip_endpoints: [ArchiMate_Junction, ArchiMate_Grouping]   # judged by other rules
      unknown_endpoint: ignore              # an end the table does not name: ignore | warn | error
```

- **Generate the table, do not type it.** Build `cells` from the language's data (for the
  library languages, `relationships.allowed` in the language file), so the ruleset and the
  standard cannot drift. Cite the source; a table without `source` is refused.
- **A known pair with no cell allows nothing.** If both ends appear somewhere in the table but
  `cells[source][target]` is missing, every connector between them is a violation.
- **Prefixes are dropped in tables.** Unlike selector names, table names may carry the
  technology prefix (`ArchiMate3::ArchiMate_Serving`); it is removed before matching, because
  EA stores the short name. An element bound to another technology with the same short name
  matches too.
- **An end with no stereotype uses the table's `""` row.** An end that carries no stereotype
  and has no `type:` row is looked up under `""`.
- **Quote what YAML would read as a boolean.** Quote cells, sources and targets that YAML would
  read as booleans: `"no"`, `"yes"`, `"on"`, `"off"`. An unquoted one is refused with
  `invalid_table`. When generating YAML, quote every string.
- **Pick `unknown_endpoint` deliberately.** `ignore` suits a model that mixes languages; `warn`
  or `error` suit a model that should hold only this language.
- **Prove it fires.** Seed one connector the table refuses and confirm the rule reports it,
  naming the pair and what the table allows there.

The connector selector also accepts `connector_stereotypes: [A, B]` (a list) for any connector
condition.

## Selecting by EA type

A stereotype selector cannot see an element that carries no stereotype, and EA models UML
that way: a class, a use case or a port is told apart by EA's own type
(`t_object.Object_Type`), not by a stereotype. A rule can select by EA type, beside or
instead of stereotypes; given both, an item must match both.

```yaml
    selector:
      type: element
      types: {any_of: [UseCase]}            # t_object.Object_Type
    selector:
      type: connector
      connector_types: [Generalization]     # t_connector.Connector_Type
```

Anywhere a rule names an element at a connector's end, a table row or column, or a
container, write an EA type as `type:<Object_Type>`. The prefix keeps a type apart from a
stereotype of the same name.

```yaml
    condition:
      type: connector_endpoint_stereotype
      source_must_be_one_of: ["type:Actor", "type:UseCase"]
      target_must_be_one_of: ["type:UseCase"]
```

In a relationship table, an end uses its stereotype's row when the table has one, otherwise
its `type:` row. `connector_count` takes `connector_type` beside `connector_stereotype`.

- **Measure the type names.** Read `SELECT DISTINCT Object_Type FROM t_object` (or
  `Connector_Type FROM t_connector`) on a model built in EA. EA's names are its own
  (`StateNode`, `ActionPin`, `Sequence`), not always the standard's metaclass names.
- **Prefer stereotypes where they exist.** Many technologies put one stereotype on several
  EA types; select by type only for what has no stereotype, or to narrow a stereotype to one
  of its EA types.

## Writing where-it-sits rules

EA records where every element sits. An element's **container** is the element it is
attached to, if any (a port's owner, or an element nested under another in the Browser),
otherwise its package. A package's container is the package above it. So each element has
one chain of containers, read outward.

`contained_in` checks that chain. `path` has one step per level, innermost first; a step
names the container by stereotype or `type:` (`stereotype_one_of`), by name (`name_one_of`),
or both, and must match all it names. A qualified stereotype (`WBA::...` or the profile name) matches a package bound to that technology; a bare name matches any.

```yaml
  - id: ZF-CELL-002
    selector:
      type: element
      stereotypes: {any_of: [BusinessEntity]}
    condition:
      type: contained_in
      path:
        - {stereotype_one_of: [ZFCell], name_one_of: [Semantic Data Model]}   # the cell
        - {name_one_of: [Owner]}                                              # the row it is in
```

`contains_count` bounds an element's **direct** children of a kind. A package element's
children are what its package holds; any other element's children are the elements attached
to it.

```yaml
    condition:
      type: contains_count
      child: {stereotype_one_of: [TopEvent]}
      min: 1
      max: 1
```

- **Use names only where the standard has nothing else.** Some frameworks identify a
  container only by its name (a framework row or column); where a stereotype exists, use it.
- **A missing container fails.** If the chain ends before the path does, the element is
  reported, with where it actually sits.

## Writing connector count rules

```yaml
    condition:
      type: connector_count
      connector_stereotype: Aggregation   # the edge label to count
      direction: incoming                 # incoming | outgoing: use only these two
      min: 2                              # at least 2
      # max: 5                            # optional upper bound
```

Any other `direction` (including `both`) is refused with `invalid_rule_shape`: write one rule per direction. Omitted means outgoing.
`direction: incoming` = connectors pointing INTO this element (element is the target).
`direction: outgoing` = connectors pointing OUT of this element (element is the source).
Use `connector_type: Generalization` instead of, or beside, `connector_stereotype` to count by
EA connector type. With neither, the rule counts every connector. `min` and `max` are
non-negative whole numbers with `min` not above `max`.

## The extended grammar

Everything above keeps its meaning. A ruleset written before these keys existed runs the same way and
gives the same violations. The keys below add to it. Use them when a standard's rule is about an
element's tags, its multiplicity, its type, its ancestors, what it owns, or what it must not be, and
the older conditions cannot say it. A ruleset that uses any of them needs a server that has them: set
`meta.min_server_version` as described in the `ea-validation` skill, so an older server refuses the
ruleset instead of reading the new keys as errors in the middle of a run.

Westbrook Bank names below (`WBA`, `WBA::WBABusinessApplication`) are an illustration. Use your own
technology's names, read from your model.

An unknown key anywhere in these blocks is `invalid_rule_shape`, with the text `<where> has unknown fields [...]; allowed: [...]`.

### The match block

A match block describes one element. Wherever a rule needs "an element that looks like this", it takes
a match block: an element selector's `where`, a connector selector's `source` and `target`,
`connector_ends.source` and `.target`, `contained_in.path` steps, `contains_count.child`, `related`'s
`where` and `each` (when the step yields elements), `typed_by`, `specializes` and `not`. It is a
mapping with at least one key, and every key present must hold.

| Key | Value | Holds when |
|---|---|---|
| `stereotype_one_of` | non-empty list of names (a stereotype, a qualified name, or `type:<Object_Type>`) | the element's stereotype or EA type is in the list |
| `any_stereotype_one_of` | non-empty list of stereotype names (bare or qualified; a `type:` entry is refused, put it in `stereotype_one_of`) | any stereotype applied to the element, the first or a later one (read from the cross-reference rows), is in the list |
| `name_one_of` | non-empty list of names | the element's name is in the list |
| `kind_one_of` | list of kind names (see below) | the element is that kind of thing |
| `tags` | list of `{name, value_in \| value_not_in \| non_empty}` or `{name, min, max, integer}` | every tag clause holds |
| `properties` | list of `{name, value_in \| value_not_in \| non_empty}` over Status, Priority, Difficulty, Phase, Version, Author, Complexity (Priority and Difficulty are a Requirement's; blank on other types) | every property clause holds |
| `typed_by` | a match block, or `{}` for "typed by anything" | the element's type (classifier) matches the block |
| `specializes` | a match block | some ancestor through Generalization matches the block (any depth, loop-safe) |
| `multiplicity` | `{one_of: [...], lower_min: n, upper_max: n}`, at least one | the element's multiplicity fits |
| `not` | a match block | the element does not match that block |

```yaml
selector:
  type: element
  stereotypes: {any_of: [WBA::WBABusinessApplication]}
  where:
    tags: [{name: lifecycle, value_in: [Current, Strategic]}]
```

**Tags.** Give exactly one of `value_in`, `value_not_in`, `non_empty` per clause. A tag's values are all its
rows with blanks ignored. `value_in` holds when any value is in the list. `value_not_in` holds when no value
is in the list, so an element with no value holds. `non_empty: true` needs a value; `false` needs none.
Quote a value YAML would read as a number, yes/no or null.

**Numbers on tags.** A clause may instead give `min` and `max` (inclusive numbers) and `integer: true`.
It holds when the tag has a value and every value passes; a value that is not a number fails, and a blank
value is ignored, so an element with no value does not hold. The same three keys work on a tag entry of
`tagged_value_required` and `tagged_value_constraint` (a value that is not a number is reported as "is not a
number"; a blank or missing value is skipped there, so add `must_be_non_empty` to the entry to require one)
and on a `tagged_value_filter` clause (use them or `value_in`, not both).

```yaml
# Every Westbrook business application carries a whole-number priority from 1 to 10.
selector: {type: element, stereotypes: {any_of: [WBA::WBABusinessApplication]}}
condition:
  type: tagged_value_required
  tags: [{name: priority, min: 1, max: 10, integer: true, must_be_non_empty: true}]
```

**Second stereotypes.** EA keeps the first stereotype in the element's own row and the rest in a
cross-reference table. `stereotype_one_of` reads the first; `any_stereotype_one_of` reads all of them.

```yaml
# Business applications that are also a system of record, whichever stereotype comes first.
selector:
  type: element
  stereotypes: {any_of: [WBA::WBABusinessApplication]}
  where: {any_stereotype_one_of: ['WBA::WBASystemOfRecord']}
```

**Properties.** `properties` reads EA's own element columns, such as the status of a requirement. Any other
name is refused with `invalid_rule_shape`, which lists the allowed ones.

```yaml
# An approved Westbrook requirement must have an owner.
selector:
  type: element
  types: {any_of: [Requirement]}
  where: {properties: [{name: Status, value_in: [Approved]}]}
condition: {type: tagged_value_required, tags: [{name: owner, must_be_non_empty: true}]}
```

**Multiplicity.** `one_of` takes quoted forms such as `"1"`, `"0..1"`, `"1..*"`, `"*"` (meaning `0..*`).
`1` equals `1..1`. `lower_min` and `upper_max` are whole numbers of at least 0. An element with no
multiplicity fails every multiplicity test.

**Kinds.** `kind_one_of` names things EA stores as one element type with a number or a property. Each entry is
one of the measured names, `ntype:<number>` (the raw `t_object.NType`), `action:<kind>` (an Action whose kind
is that text, such as `action:CallBehavior`, case sensitive), `pin:input` or `pin:output`.

| Measured name | What EA stores |
|---|---|
| `InitialPseudostate`, `FinalState`, `ShallowHistory`, `Junction`, `Choice`, `Terminate`, `EntryPoint`, `ExitPoint`, `DeepHistory` | StateNode, NType 3, 4, 5, 10, 11, 12, 13, 14, 15 |
| `InitialNode`, `ActivityFinalNode`, `FlowFinalNode` | StateNode, NType 100, 101, 102 |
| `SendEvent` | Event, NType 0 |
| `FragmentAlt`, `FragmentOpt`, `FragmentBreak`, `FragmentPar`, `FragmentLoop`, `FragmentCritical`, `FragmentNeg`, `FragmentAssert`, `FragmentStrict`, `FragmentSeq`, `FragmentIgnore`, `FragmentConsider` | InteractionFragment, NType 0 to 11 in that order |

Not measured: Event numbers 2 to 9 (only 0, a send, is named); StateNode 6 (a junction in a state machine,
a JoinNode in an activity, so write `ntype:6`) and 0, 1, 2, 7, 8, 9 and 103; a fork or join in a state
machine. Write those as `ntype:<number>` and check the number against a model built in EA. An entry
that is none of these is refused: `kind_one_of entry 'X' is not a kind this server can name`.

```yaml
where: {kind_one_of: [InitialPseudostate]}        # a state machine's initial state
where: {kind_one_of: ["pin:output"]}              # an output pin
```

### Selectors

- Element: the existing keys, plus `where: <match block>`.
- Connector: the existing keys, plus `source: <match block>` and `target: <match block>`. They filter before the
  rule runs, so `rule_stats.examined` counts only connectors that pass.
- Diagram: `{type: diagram, diagram_types: [names]}`. A name is EA's `Diagram_Type` or `<technology>::<name>`
  for an MDG diagram. Scope and `meta.exclude_packages` apply by the diagram's package.

```yaml
selector:
  type: connector
  connector_stereotypes: [WBA::Uses, WBA::Flows]
  source: {tags: [{name: lifecycle, value_in: [Current, Strategic]}]}
```

### `connector_ends`: the two ends of a connector

A connector selector only. Keys: `source` and `target` (match blocks), `source_end` and `target_end`
(`{multiplicity: {...}, aggregation_one_of: [none | shared | composite]}`, at least one inside). Give at
least one of the four. `source_end` reads the source side's cardinality and aggregation, `target_end` the
target side's. An association can carry the diamond on either end, so write both when the whole matters.

This is the Westbrook lifecycle rule (WBA-LFY-001) in YAML. A connector from a Current or Strategic application
to a Deprecated or Retired one is a finding:

```yaml
- id: WBA-LFY-001
  severity: error
  selector:
    type: connector
    connector_stereotypes: [WBA::Uses, WBA::Flows]
    source: {tags: [{name: lifecycle, value_in: [Current, Strategic]}]}
  condition:
    type: connector_ends
    target: {tags: [{name: lifecycle, value_not_in: [Deprecated, Retired]}]}
```

A cardinality example, for a composition that must end at exactly one whole:

```yaml
condition:
  type: connector_ends
  source_end: {multiplicity: {one_of: ["1"]}, aggregation_one_of: [composite]}
```

### `related`: what an element is linked to

Keys: `via` (required, a mapping with exactly one step), `where`, `min`, `max`, `each`. Give at least one of
`min`, `max`, `each`. `min` and `max` are whole numbers of at least 0, `min` not above `max`. `where` limits
what is counted. `each` is a match block (or feature block) that every counted item must satisfy; an item that
does not is its own finding.

| `via` (element selector) | Counts | Options |
|---|---|---|
| `connector` | elements at the other end of connectors | `connector_stereotypes`, `connector_types`, `direction: incoming \| outgoing` (default outgoing; `both` is refused) |
| `container` | the element or package it sits in | none: write `container: {}` |
| `children` | its direct children | none |
| `classifier` | the element that types it | none |
| `general` | its direct parents through Generalization | none |
| `attributes` | its attributes | none |
| `operations` | its operations | none |
| `parameters` | the parameters of all its operations | none |
| `diagrams` | the diagrams it appears in | none |
| `tag_reference` | the elements its tag points at | `tag: <name>` |

| `via` (diagram selector) | Counts | Options |
|---|---|---|
| `shows` | the elements on the diagram | none |

| `via` (connector selector) | Counts | Options |
|---|---|---|
| `linked_connectors` | connectors tied to this one | `relation: realizes \| realized_by \| attached_to` |

`connector` returns elements, deduped, not connectors. A step with no options is written with `{}`.

```yaml
# Every business application is used by at least one other application.
condition:
  type: related
  via: {connector: {connector_stereotypes: [WBA::Uses], direction: incoming}}
  where: {stereotype_one_of: [WBA::WBABusinessApplication]}
  min: 1
```

**Features.** `via: attributes`, `operations` and `parameters` take a feature block in `where` and `each`:

- attributes: `stereotype_one_of`, `name_one_of`, `type_one_of`, `typed_by`, `visibility_one_of`, `multiplicity`, `not`
- operations: the same without `multiplicity`
- parameters: `name_one_of`, `type_one_of`, `typed_by`, `not`
- diagrams (`via: diagrams`): `name_one_of`, `diagram_types`, `not`
- connectors (`via: linked_connectors`): `stereotype_one_of` (a stereotype or `type:<Connector_Type>`), `source`, `target`, `not`

```yaml
# A table has at most two key columns, and every column has a type.
condition:
  type: related
  via: {attributes: {}}
  where: {stereotype_one_of: [column]}
  max: 2
```

A feature finding carries `feature`.

`tag_reference` resolves the comma-separated values of the tag against element GUIDs. A value that matches
no element is its own finding (`tag 'principal' holds 'X', which names no element`). It yields elements only.
`realizes` and `realized_by` read EA's realization rows. `attached_to` follows an end that is a proxy connector
element to the connector it stands for.

**Typing.** `typed_by` and `via: classifier` read the type EA stores. For a Part or Port that is the type GUID
(`PDATA1`) matched to an element, falling back to the classifier. Pins and objects use the classifier;
attributes and parameters use their own type. Not measured: which Part field EA's property window fills
("Property Type" in the UI), so the fallback exists; a Part typed through a property-window write.

### `any_of`, `all_of`, `not`, `forbidden`

```yaml
condition:
  type: any_of                  # all_of takes the same shape
  conditions:
    - {type: contains_count, child: {stereotype_one_of: [WBA::WBAComponent]}, min: 1}
    - {type: related, via: {connector: {connector_stereotypes: [WBA::Uses]}}, min: 1}
```

- `any_of` fails with one finding, `none of the alternatives holds: (1) <msg>; (2) <msg>`.
- `all_of` reports every child's findings separately.
- `not` takes `condition: <one condition>`; the finding is `<description> holds, and this rule says it must not`.
- `forbidden` takes no keys. Every selected item is a finding: `is not allowed here: the rule forbids <selector>`. Pair it with `where` to forbid one shape:

```yaml
- id: WBA-FRB-001
  severity: error
  selector:
    type: element
    stereotypes: {any_of: [WBA::WBABusinessApplication]}
    where: {tags: [{name: lifecycle, value_in: [Retired]}]}
  condition: {type: forbidden}      # a retired application must not remain in the live packages
```

Inside `any_of`, `all_of` and `not` only per-item checks are allowed. `chain`, `unique`, `forbidden`,
`relationship_table` and `tagged_value_type_shipped` are refused there (`a <type> condition cannot sit inside
any_of, all_of or not`); give them a rule of their own. Errors in a nested condition name the path
`condition.conditions[i]`.

### `chain`: how deep, and whether it loops

An element selector only. `via` is `connector`, `general` or `classifier`. Give `max_depth` (whole number of at least 1,
the most links a chain may have), `no_cycles: true`, or both.

```yaml
- id: WBA-CHN-001
  severity: warning
  selector:
    type: element
    stereotypes: {any_of: [WBA::WBACapability]}
  condition:
    type: chain
    via: {connector: {connector_stereotypes: [WBA::ParentOf], direction: incoming}}
    max_depth: 3
    no_cycles: true
```

Findings: `chain of ParentOf (incoming) is 4 steps deep, max 3: 'A' > 'B' > ...` and
`chain of ParentOf (incoming) loops: 'A' > 'B' > 'A'`. A loop is reported once, on its first selected member.
Depth ignores a link that closes a loop.

### `unique`

`key: name` or `key: "tag:<name>"` (required), `scope: model | package | container` (default `model`). It
applies to element and diagram selectors; a diagram selector takes `name` only. Every member of a clash is a
finding: `tag 'id' 'REQ-001' is shared with 'Req two' (#2) (scope model)`.

```yaml
condition: {type: unique, key: "tag:requirementId", scope: package}
```

### Tables: connector types in the legend

A letter in a table's `connectors` can map to an EA connector type: `a: "type:Dependency"`. A connector uses
its stereotype's letter when its stereotype is in the legend, otherwise its type's. `type:` with no type after it is `invalid_table`.

### Ruleset-level keys

```yaml
meta:
  exclude_packages: [Archive, "{3F2A...}"]   # package names or GUIDs; their contents are left out
  owner_tag: businessOwner                    # the tag on a package's element that names its owner
exceptions:                                   # or a file named <ruleset>.exceptions.yaml beside the ruleset
  - rule_id: WBA-LFY-001
    element_guid: "{8C1D...}"
    reason: Retirement plan approved, runs to March
    recorded_by: <Reviewer A>
    expires: 2027-03-31
```

- `exclude_packages` is a non-empty list of text. A connector is still checked unless both ends are in excluded packages. `owner_tag` is text. A wrong shape is `invalid_ruleset_meta`.
- An exception needs all five fields: `rule_id`, `element_guid`, `reason`, `recorded_by`, `expires` (a date,
  `YYYY-MM-DD`). One without an expiry is refused. Exceptions go in the ruleset under `exceptions:` or in a file
  beside it named `<ruleset>.exceptions.yaml` (a mapping with `exceptions:`, or a bare list).
  Errors are `invalid_exception`.
- What these do to a run, and how to read the result, is in the `ea-validation` skill.

Every finding carries the element's GUID and package id. The ruleset's id, for run history, is `meta.id`, else `meta.language`, else the file name, else `inline`.

### What was measured, and what was not

Measured against a model built in EA 17.1 (build 1716): the kind names in the table above. Everything else in this section was
proved against the engine's test fixtures and read from how EA stores the data, not run on a customer model. Not measured:
reference tags longer than the stored value column; the type of each SysML tag (a single reference or a
list), so any tag can be named and none is assumed; EA writing the realization rows itself on build 1716, and
whether UPDM's own stereotypes use the same row; SysML item-flow realization; a real UAF diagram type;
multiplicity beyond one sample model; run time at enterprise scale (reads are bulk per step, but
`contained_in`, `contains_count`, `children` and `container` still read per item). A rule that depends on
one of these is a hypothesis until it has run against your own model and shown a finding.

## Section comments

Use ASCII section headers to visually group rules:

```yaml
  # ═══════════════════════════════════════════════════════════════════════════
  # SECTION 1 — RELATIONSHIP ENDPOINT VALIDITY (REL)
  #
  # One or two lines explaining what this section covers and which spec
  # sections these rules come from.
  # ═══════════════════════════════════════════════════════════════════════════

  # ── Assignment ──────────────────────────────────────────────────────────────

  - id: WBA-REL-001
    ...
```

---

## See Also

- `ea-ruleset-author/SKILL.md` — the workflow this grammar supports
- `rulesets/archimate-3/archimate-3_rules.yaml`: the canonical reference implementation
