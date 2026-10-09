# Language Bindings — Diagram Conventions as Data

Detail supporting [`../SKILL.md`](../SKILL.md). This file is the normative schema for a binding:
every key, whether it is required, and what it is validated against. Which grammar suits which
content is judgment and lives in [`grammars.md`](grammars.md); the arithmetic lives in
[`../tools/compose.py`](../tools/compose.py).

---

## 1. What a binding is

Every modeling language has its own diagram types, its own sizing and spacing, its own title
convention, its own routing habits, and its own catalog of standard views. If those live in code,
every new notation is an engineering task and the library never covers more than the few that were
hard-coded. So they live in data instead — one YAML binding per technology — and adding a notation is
a data change rather than an engineering task.

The dependency runs one way only. `compose.py` contains no technology name and does not import the
loader: a binding is data that *feeds* the engine. A single `if technology == …` in the engine would
quietly undo the whole design.

**The bindings are a tree, not a flat set of peers.** EA is a UML tool, so one binding holds EA's base
notation and every MDG binding declares `extends` to it and records in `base` which of its diagram
types each of its own is drawn on. What that buys is the slots a binding does *not* state: they resolve
to the value measured for the diagram type it is actually drawn on instead of to an engine default.
§5.6 is the whole of it.

## 2. Where bindings live, and how one is found

Bindings sit in `bindings/`, one file per technology. **Ask `available_bindings()` which ones ship**
rather than trusting a list in a document: this line read "two ship" for some time after the third
one landed, and a stale inventory here is the one that sends a reader looking for a file that is not
there — or worse, writing a second binding for a technology that already has one.

The filename is a slug of the technology id — lowercased, with anything outside letters, digits, `.`,
`_` and `-` flattened to `-`, so `BPMN2.0` becomes `bpmn2.0.yaml`. The **declared `technology` is
authoritative**: when no slug matches, the loader reads each file's declared id, so a file named
anything at all still binds the technology it says it does.

Bindings are parsed with `yaml.safe_load`, always. That is why a binding cannot carry executable
content — `!!python/object` is refused by the parser rather than by a check someone could forget to
run. PyYAML is required, and is loaded the way `validate_model` loads it: if it is missing, the error
says so and names the install.

```
pip install pyyaml
```

## 3. The closed vocabularies

Four vocabularies are fixed. A value outside them is refused on load.

**Grammars** — eight, in three placements. The placement is who computes the coordinates, and it
decides what a consumer may do with a diagram type that names the grammar.

| Grammar | Placement | Geometry is ours | Producible today |
|---|---|---|---|
| `layered-bands` | composed by us | yes | yes — `compose_layered_bands` |
| `lanes` | composed by us | yes | yes — `compose_lanes` |
| `nested-grid` | composed by us | yes | yes — `compose_nested_grid` |
| `radial` | composed by us | yes | yes — `compose_radial` |
| `two-column-cycle` | composed by us | yes | yes — `compose_two_column_cycle` |
| `computed-geometry` | composed by us | yes | **no** — no composer yet |
| `graph` | EA's layout places it | **no** | **yes** — via `layout_diagram`, then tidy |
| `ea-semantic` | the diagram type dictates it | **no** | **no** — later design work |

Six are compositional layouts this library computes coordinates for. `computed-geometry` is one of
them and has no code behind it yet: **the treemap is all that remains under that name** after `radial`
was split out and built, and the timing diagram was moved to `ea-semantic` — see §5.5.1 and
`grammars.md` §7.

The other two are the cases where we place nothing, and they are not layouts:

- **`graph`** — a graph or a tree. We compute no coordinates; EA's own layout engine does, and we tidy
  afterwards. The binding still carries everything else of value, and `spacing` is not wasted on it:
  the layout call reads the same gaps as layer and column spacing. A `graph` diagram type is fully
  **producible**, and the reference corpus audit already counts diagrams achieved this way.
- **`ea-semantic`** — the diagram *type* fixes the arrangement, so coordinates are the **wrong
  output**. The clear case is lifelines with messages ordered down the page, where the horizontal
  pitch is an even machine step no author produces by hand. Quality there is order, not geometry.
  Nothing here produces or judges one, so it is **not** producible. It is recorded anyway — see §5.5.
  **It does not mean "behavioral"**: a state machine's states and a collaboration's participants sit
  where a modeler put them and are `graph`. See §5.5.1, which is where that mistake was made and
  corrected.

> **Two questions, two answers, never one boolean.** `grammar_is_implemented` means *the engine has a
> `compose_<grammar>` function for this* and nothing else — consumers sweep that set to pick a
> composer, so an entry with no composer in it would crash them. *Can we produce this at all* is
> `grammar_is_producible`. For the composed grammars the two coincide; for `graph` they differ,
> which is the whole reason there are two.

**Channels** — the ten visual channels a diagram can carry a variable in: `fill`, `border`,
`border_width`, `line_color`, `line_style`, `font_color`, `opacity`, `icon`, `size`, `position`.

**Title conventions** — two: `drawn`, meaning the diagram carries a drawn title element on the
canvas, and `frame-header`, meaning EA's own diagram frame supplies it and drawing one would double
up.

**Routes** — the ten EA accepts, from a connector's Line Style submenu: `Direct`, `AutoRouting`,
`CustomLine`, `TreeVertical`, `TreeHorizontal`, `LateralVertical`, `LateralHorizontal`,
`OrthogonalSquare`, `OrthogonalRounded`, `Bezier`. Comparison ignores case and punctuation; the
string is stored as written. The server is the source of truth for these names — the loader's copy
exists so a typo is caught on load instead of at write time.

## 4. The schema

Every validation error names the offending key by its path into the document —
`diagram_types.Application.channels.fill`, `viewpoints.ApplicationCooperation.diagram_type` — so an
author can find it without guessing. Unknown keys are refused rather than ignored, and the common
mistakes are told what they probably meant.

### 4.1 Top level

| Key | Required | Validated against |
|---|---|---|
| `technology` | yes | Non-empty string, and must not contain `::`. This is the part *before* the `::` in an `MDGDgm=<Tech>::<DiagramType>` value, and it has to match EA verbatim. |
| `display_name` | no | Non-empty string. Defaults to `technology`. |
| `extends` | no | Technology id of another binding in the same directory — **the notation this one is built on**. Cannot be this binding's own id; cycles are refused by name. Every shipped MDG binding names the base notation here; see §5.6. |
| `stereotype_prefix` | no | String, `""` included. See §5.3 — `""` is a statement, not an omission. |
| `notes` | no | Non-empty string. |
| `diagram_types` | yes | Mapping, at least one entry. |
| `viewpoints` | no | Mapping. Absent is a legitimate answer for a notation that publishes no catalog. |
| `presentation_profiles` | no | Mapping. |

### 4.2 `diagram_types.<name>`

The key is the diagram type name as EA spells it, verbatim — BPMN's is `Business Process`, with a
space.

| Key | Required | Validated against |
|---|---|---|
| `base` | no | Non-empty string. The EA base diagram type this MDG diagram type is built on, which is what a caller passes to `create_diagram` to create one — `Logical` for `ArchiMate3::Application`, `Analysis` for `BPMN2.0::Business Process`. **Consumed twice**: it picks the parent diagram type this one inherits its unstated sizes and gaps from (§5.6), and it is the resolver's weakest match when a diagram names no MDG diagram type of its own. State it on every diagram type — a missing `base` costs the substrate. |
| `grammar` | yes | One of the eight grammars (§3). Mandatory, which is why `graph` and `ea-semantic` exist — see §5.5. |
| `title` | yes | `drawn` or `frame-header`. |
| `sizing` | yes | §4.3. |
| `spacing` | no | §4.4. Per key, an omitted gap now means **the value measured for the base diagram type this one is drawn on**, and the engine's own default only when there is no substrate to ask. See §5.6. |
| `routing` | yes | §4.5. |
| `channels` | yes | §4.6. |
| `notes` | no | Non-empty string. |

### 4.3 `sizing`

A mapping of notation concept name to `{w, h}`, both positive whole numbers. `default` is required —
every diagram type needs a fallback box size, and per-concept entries are refinements of it. `width`
and `height` are refused with a pointer to `w` and `h`.

Keys are concept names as the notation's own specification writes them (`ApplicationComponent`), not
what EA stores. See §5.3.

> **Per-concept sizes are yours to apply.** `spec()` carries `sizing.default` and nothing else, and
> the engine sizes items uniformly within a band or a lane. A `Junction: {w: 20, h: 20}` entry does
> not take effect on its own — read it with `size_for` and act on it, or you will place 100x70
> junctions. See §7.

### 4.4 `spacing`

Any subset of `compose.DEFAULT_SPEC`'s keys — `item_gap_x`, `item_gap_y`, `item_gap_flow`,
`lane_gap`, `band_gap`, `wrap_width`, `align` and the rest — spelled the way the engine spells them.
Values are copied into the spec verbatim. See §5.1.

> **Each grammar reads its own keys, and nothing checks which ones you set.** `spacing` is validated
> against the whole of `DEFAULT_SPEC` without regard to the diagram type's `grammar`, so a `lanes`
> binding may carry band-only keys and a `layered-bands` binding may carry lane-only keys. Keys the
> composer for that grammar never reads are inert, not refused, and nothing reports them.
>
> | Read by | Spec keys |
> |---|---|
> | both composers | `origin_left`, `origin_top`, `item_width`, `item_height`, `label_height` |
> | `layered-bands` only | `item_gap_x`, `item_gap_y`, `h_pitch`, `row_pitch`, `wrap_width`, `align`, `band_pad_x`, `band_pad_y`, `band_gap`, `band_pitch`, `min_band_width` |
> | `lanes` only | `item_gap_flow`, `flow_pitch`, `lane_pad`, `lane_gap`, `min_lane_thickness`, `label_width` |
>
> The label key depends on orientation in `lanes`: a horizontal lane reserves `label_width` down its
> left, a vertical lane reserves `label_height` across its top. A band always uses `label_height`.
>
> **`compose_lanes` never reads `item_gap_x` or `item_gap_y`.** All three BPMN diagram types are
> `grammar: lanes` and all three set both, so in `bpmn2.0.yaml` those two are recorded measurements
> rather than layout input — kept for a future nested-grid or bands rendering, and labeled as such at
> the point they are set.

### 4.5 `routing`

| Key | Required | Validated against |
|---|---|---|
| `default` | yes | A route name. Leaving it unstated means every connector falls back to whatever EA last did, which is not a convention. |
| `trunk_for` | no | List of relationship type names this notation habitually draws as a shared trunk. |
| `trunk_route` | no | A route name. Defaults to `OrthogonalSquare` when `trunk_for` is present. |
| `notes` | no | Free text. |

### 4.6 `channels`

| Key | Required | Validated against |
|---|---|---|
| `fill` | yes | A string saying what the notation uses fill for, or `~`. |
| `claimed` | no | Mapping of channel name to a string saying what it already means. `fill` is not allowed here — it is declared by `fill`. |
| `free` | no | List of channel names, no duplicates, none of them already spoken for. |
| `notes` | no | Free text. |

See §5.2. This is the block the rest of the schema exists to protect.

### 4.7 `viewpoints.<name>`

A standard view the notation itself defines — ArchiMate's viewpoints, TOGAF's deliverables, UAF's
views. Holding the catalog as data is what lets view selection stay generic instead of growing a
branch per notation.

| Key | Required | Validated against |
|---|---|---|
| `diagram_type` | yes | Must be a diagram type this binding declares. |
| `intent` | no | List of phrases a request might match. |
| `admits` | no | List of concept names, no duplicates. Concept names, not stored stereotypes. |
| `grammar` | no | One of the eight. Overrides the diagram type's grammar for this viewpoint. |
| `notes` | no | Free text. |

### 4.8 `presentation_profiles.<name>`

How much detail a view shows, orthogonal to its diagram type. The same content can be duplicated
into a second diagram under a different profile, giving a live detail view *and* a live executive
view of one model rather than a screenshot of one of them.

A profile says what it **shows**; EA is told what to hide. The loader owns that inversion, so
`hide_connector_labels` in a binding is refused with a pointer to `connector_labels`.

| Key | Value |
|---|---|
| `description` | Non-empty string. |
| `connector_labels`, `connector_stereotypes`, `element_stereotypes`, `notes` | `true` or `false`. |
| `compartments` | `all`, `none`, or a list of compartment names. |
| `collapse_parallel` | `true` or `false` — collapse parallel connectors between a pair onto one line. |
| `direction_only` | `true` or `false`. Refused unless `collapse_parallel` is also set: it means nothing on its own and reads as if it does something. |

Every key is optional. A profile that says nothing about stereotypes leaves them alone rather than
asserting a default it never chose.

---

## 5. What the schema is strict about, and why

### 5.1 `spacing` uses the engine's own key names

`compose.py` distinguishes a **gap**, the space between two boxes, from a **pitch**, which runs
leading edge to leading edge and therefore includes the box it steps over. It raises when a pitch is
smaller than the item it has to step over.

> A binding author writing `pitch: 40` beside a 100-wide item has written a layout the engine
> refuses, and would not find out until generation time.

So `spacing` is validated against `compose.DEFAULT_SPEC` itself. A binding can only name a key the
engine really has, spelled the way the engine spells it, which makes the translation into a spec the
identity — the two cannot drift apart. `pitch:` is refused with the keys the author probably meant,
`item_gap_x` and `item_gap_y`, and so are `h`, `v`, `gap_x` and `gap_y`.

Values are not range-checked here. `compose.py` owns those rules, and duplicating them would give two
answers that can disagree. What is checked is the key, because an unknown key is the failure the
engine cannot see.

### 5.2 `channels` is mandatory, and so is `fill`

Each notation **already claims** some visual channels. A second variable has to go somewhere else,
and a binding that lets an agent recolor ArchiMate fills has broken the notation while looking like a
feature.

`fill` is required even when the answer is "nothing" — write `~`. Leaving the key out is not a
neutral default; it is a binding that has not said whether the most tempting channel on the diagram
is available.

A channel cannot be both claimed and free. Listing one in both places is refused, because it tells a
consumer it is safe to overwrite something the notation needs. The one exception falls out of that
rule rather than around it: when `fill` is `~`, fill is not spoken for, so it may appear in `free`.

Fill is sometimes worse than claimed — it is unavailable. Measured on EA 17.1 build 1716,
`ArchiMate_Node` and `ArchiMate_Grouping` ignore a per-diagram fill outright: the write succeeds, the
property reads back, and EA draws the element in its own colors, because the stereotype's shape
script paints it. Seven of nine sampled concepts honor it. Nine concepts is a sample rather than a
sweep, which is why this is a note in the binding and not data a consumer can query yet. In practice,
reach for `Device` or `SystemSoftware` over `Node` when a technology layer needs color coding.

### 5.3 `stereotype_prefix` — concept names in, stored stereotypes out

`admits` and `sizing` keys use concept names the way the notation's own specification writes them:
`ApplicationComponent`. What EA stores in `t_object.Stereotype` is the prefixed form,
`ArchiMate_ApplicationComponent`.

The prefix is data because it is not guessable. It was measured on EA 17.1 build 1716's built-in
ArchiMate3 MDG, which prefixes with `ArchiMate_`; BPMN2.0 uses no prefix, and an install carrying a
differently built MDG can differ again. `stereotype_for` applies the prefix and `concept_for` removes
it, so the conversion happens in one place.

### 5.4 `title` is explicit per diagram type

Neither convention can be the silent default: a diagram with two titles and a diagram with none are
equally likely mistakes. It is recorded per diagram type because the split tracks notation — measured
across the reference corpus, 13 of 13 ArchiMate diagrams draw a title and 10 of 11 BPMN diagrams rely
on EA's diagram frame.

> The corpus catalog spells the second convention `frame-only`. The schema spells it
> `frame-header`. They are the same convention.

### 5.5 A binding may name a grammar that cannot be composed

`computed-geometry` is a valid value with no code behind it. That is deliberate: recording an
implemented grammar for a diagram type that is genuinely something else would be a lie stored as
data, and the lie would be believed precisely because it composes.

`nested-grid` was in this position until it was implemented, which is what the arrangement is for:
ArchiMate's Organization and Capability viewpoints had been recorded as the nested grids they are,
so the day the grammar shipped they became composable without a single binding changing.

`DiagramTypeBinding.grammar_is_implemented` is how a consumer finds out before it composes rather
than after. `False` is a real answer, not an error — check it, say so, and act on
`grammar_is_producible` instead of composing the wrong shape.

**This is not a license to park a diagram type under an unbuilt grammar.** `archimate3.yaml` records
`Motivation` as `layered-bands` even though a motivation view reads as a tree, and that is honest,
because the levels of intent really are drawn as registers — one band per level — which is what keeps
siblings aligned; the binding's own `notes` say so. What would be dishonest is recording
`computed-geometry` for a diagram type with no computed geometry, just to get it into a file: the day
the treemap composer ships, that type starts reporting itself composable and something will compose
it.

### 5.5.1 Choosing between `graph` and `ea-semantic`

Both mean *we place nothing*. They differ on whether the result is any good, and therefore on whether
the diagram type counts as producible.

Ask the two questions in this order.

1. **Would a general-purpose layout produce an acceptable diagram of this type?** If yes — because the
   content is a graph or a tree and nothing about the diagram type says where a node must sit — the
   grammar is **`graph`**. Hand it to EA's layout, then tidy: apply the binding's sizes, set the
   routing it states, and add or omit a title per its convention. Class, component, deployment,
   package, object, use case, internal block, parametric and plain activity diagrams are all this
   case.
2. **Does the diagram type itself dictate the arrangement, so that coordinates are the wrong output?**
   Then the grammar is **`ea-semantic`**. A sequence diagram's quality is lifeline order and message
   sequence, and the measurement shows the editor doing the placing: an even horizontal pitch no
   author produces by hand, and no element size stable enough to state, because a lifeline's height is
   set by how many messages it carries. Placing boxes on that is not "tidying", it is fighting the
   editor. Sequence and timing diagrams are this case.

> **MEASURE BEFORE YOU CLASSIFY.** This section named four types under `ea-semantic` — sequence, state
> machine, communication and interaction overview — and three of them were wrong. The intuition behind
> the mistake was *behavioral means the type owns the arrangement*, and it does not. Measured on the
> example model, 43 plain state machine diagrams place 62 states at freely chosen positions in 20
> distinct sizes, with gap populations (n=132 horizontal, n=107 vertical, the densest single diagram
> supplying 8% and 10% of them) that look like a class diagram's rather than an even pitch — so EA imposes
> nothing and the type is **`graph`**, which is how the shipped base-notation binding classifies it.
> Communication and interaction overview are ordinary graphs on the same evidence; the sequence in a
> communication diagram lives in the message *numbering*, not in coordinates. A type that *sounds*
> sequential is not `ea-semantic` unless EA is doing the placing, and the way to find out is to
> measure the positions and the sizes.

**A timing diagram is `ea-semantic`, not `computed-geometry`** — the reverse of what this section
used to say. Its x axis looks like arithmetic nobody has written, which is how it was first filed; but
the axis is dictated by the type. Every timeline spans the canvas to carry the shared time axis, so
no two timelines are ever horizontal neighbors and the horizontal gap has no samples at all, because
it is not a quantity the type has. The decisive argument is the parking hazard in §5.5: under an
unbuilt *composed* grammar, a timing diagram would start reporting itself composable the day the
treemap composer shipped. The shipped binding classifies it `ea-semantic`, `grammars.md` §7 and §9
carry the full reasoning, and **the treemap is now all that remains under `computed-geometry`**.

The distinction the pair turns on is still worth holding: `ea-semantic` means *coordinates are the
wrong output*, `computed-geometry` means *the coordinates are right and we have not written the
arithmetic*.

Test 1 first, and mean it. If EA's layout genuinely produces something a reviewer would accept, the
type is `graph` and producible — do not downgrade it to `ea-semantic` because the result is not
*composed*. Equally, do not promote an `ea-semantic` type to `graph` because it would raise the
coverage figure: a sequence diagram laid out as a free graph is not a sequence diagram.

**Record the type either way.** The reason these values exist at all is that `grammar` is mandatory,
so before them the only ways to bind such a type were to record a composed layout it does not have or
to leave it out — and an omitted diagram type is indistinguishable from an oversight. Recording it as
`ea-semantic` says "classified, not producible yet", which is a fact someone can plan against. A
missing entry says nothing.

**A `graph` binding is worth authoring.** It carries the measured element sizes, the spacing the layout
call consumes, the default and trunk routes, the title convention, and the claimed and free visual
channels — everything except the coordinates. That is the difference between a diagram that reads as
the notation and one that merely contains the right elements.

### 5.6 The base notation is the root, and inheritance fills only what a binding does not state

EA is a UML tool. Every MDG technology is a **stereotype layer applied to UML**, not a peer notation
beside it, and the data says so: each MDG diagram type records in `base` the EA base diagram type it is
drawn on, and every base the shipped MDG bindings name is a plain-UML diagram type. An ArchiMate view
*is* a Class diagram (`Logical`) with a technology tag; a BPMN process *is* an `Analysis` diagram; a
SysML requirement diagram *is* a `Custom` canvas. So one binding is the root of the tree and every
other one declares `extends` to it.

**Two keys, two facts, neither derivable from the other.** `extends` says which binding is the parent;
`base` says which of the parent's diagram types each of this binding's own diagram types is drawn on.
They are not one relationship stated twice: a single binding's diagram types can sit on *different*
bases (one shipped binding sits on two), so there is no single value `base` could derive; and `base`
names a diagram type rather than a technology, so deriving the parent from it needs a search of the
directory whose answer changes with which files happen to be present — which is the silent-wrong-answer
failure this whole module is built against. The duplication is made safe by a **test that derives the
parent from `base` and asserts it matches the declared `extends` for every shipped binding**, which
also catches the real hazard of a hand-written key: an author who forgets it.

**What is inherited: `sizing` per concept and `spacing` per key, and nothing else.**

| Slot | Inherited? | Why |
|---|---|---|
| `sizing` | per concept | A concept the child sizes keeps the child's size, `sizing.default` included — a stereotyped element is the size its own MDG draws it. Concepts the child says nothing about take the substrate's measured size. |
| `spacing` | per key | The slot this exists for. A gap a child leaves unstated used to reach the engine's own default; it now reaches the value measured for the diagram type the child is actually drawn on. |
| `grammar`, `title`, `routing`, `channels` | no | Each is mandatory or a statement in its own right. Letting a parent's `graph` win over a child's `layered-bands` or `lanes` would flatten the structure an MDG exists to add — ArchiMate's viewpoints genuinely impose bands on a base that is otherwise a graph. |
| `notes` | no | Prose about one binding is not prose about another. |
| `stereotype_prefix` | when the key is **absent** | See below. |
| `viewpoints`, `presentation_profiles` | one level, child entries winning | Neither is a claim about what EA declares, so a technology publishing none of its own is better off with its parent's than with nothing. |

**A child does not acquire its parent's diagram type catalog.** This is a change from an earlier merge
that added the parent's diagram types to the child's, and that merge is wrong in two silent ways once
the parent is the base notation. A technology's diagram types are declared by its MDG and are checked
against the MDG data, so handing an MDG binding a diagram type named `Logical` invents one EA never
declared and makes `mdg_diagram_type` build a qualified key no diagram can carry. Worse,
`resolve_diagram` matches a diagram's `Diagram_Type` against bound diagram type **names**, so every
binding drawn on a base would claim that base's own name and a plain diagram of it would come back
ambiguous across all of them. The parent's diagram types are the **substrate**, not entries in the
child's catalog.

**A child refining its own technology still works.** When a child diagram type states no `base`, the
substrate is the parent's diagram type of the **same name** — which is exactly the house-binding case:
the same diagram type, refined, inheriting whatever it does not restate.

**A `base` the parent does not bind is not an error.** A base notation may decline a diagram type for
want of a figure it can support, so a child drawn on one has nothing to inherit and keeps its own
values. `DiagramTypeBinding.inherits` is `False` there and `substrate` is `""`, so the condition is
visible rather than silent. What is *not* acceptable is shipping it: a test asserts every base every
shipped binding states is bound by the root, which is the check that would have caught two of the four
shipped technologies declaring a parent and inheriting nothing from it.

**The `stereotype_prefix` trap, which is live.** A child that **omits** the key inherits the parent's,
and the base notation's is a measured `""` — 93.6% of the elements on plain diagrams carry no
stereotype at all. That is right for a family drawn in plain UML and **wrong** for one whose MDG
stereotypes its elements, so a derived family with a real prefix must state it. The loader
distinguishes an absent key from a declared `""`, which is what makes the second form a statement
rather than an absence: `not data.get("stereotype_prefix")` cannot tell them apart, and a child that
declared `""` under a prefixed parent would silently acquire the prefix and send every stereotype
lookup after a name nothing stores. Every shipped binding states its own.

### 5.7 A measured box size does not know the content's names

`sizing.default` is measured off real diagrams of the notation, so it is the right box for a typical
name. It knows nothing about the names in front of it, and a customer's element names come from their
model and are whatever they are.

**EA does not clip a name it cannot fit — it grows the drawn box and leaves the stored geometry
alone.** Measured live on EA 17.1: a 36-character name with no space in it was drawn 169px wide
against a stored width of 60. Nothing announces it. Every other check — overlap, pitch, containment —
reads the stored rect, so from that point on they are all reading a rect EA does not paint.

Pass the item names to `spec()` and the width is fitted before it reaches the engine:

```python
fitted = dt.spec({"align": "center"}, names=[e["name"] for e in elements])
if fitted.widened:
    print(fitted.note)   # "item_width widened from 100 to 214 so every box fits its name: ..."
```

- **What must fit is the longest space-free run**, not the whole name. EA wraps on **spaces only** and
  never inside a word, so a multi-word name breaks itself and only its longest word has to fit.
- **The widening lands on `item_width`**, which is the value every grammar falls back to, so peers
  keep one width and a text-fit fix cannot become an `inconsistent-sizing` finding. A per-band or
  per-node `item_width` in the layout input still wins, and is not fitted — `spec()` never sees it.
- **Item names, not group names.** A band's or lane's title is drawn across a strip sized by the band.
- **It reports.** `spec()` returns a `SpecFit`, which *is* the spec dict and also carries
  `conflicts`, `widened`, `requested_width`, `driver` and `note`. A measured convention that was not
  the figure used has to be visible, not inferred.
- **And where the two cannot both be honored, it asks rather than deciding** — see §5.7.1.
- **Without `names` nothing is measured** and the width is the convention's, exactly as before.
- **What it does not promise.** EA's wrap is greedy, so a *multi-word* name can still read as cramped
  at a width that leaves it fitting one line with 5px each side. Guaranteeing clearance there means
  sizing the box to the whole name — a 58-character title would demand a 335-wide box — which
  overrides the notation's measured convention for content that renders perfectly well today. The
  live sweep found no findings at all from multi-word names and every one from unbreakable ones.
  `label-cramped` stays the backstop, and it measures rather than predicts.

#### 5.7.1 Widening the box is not the only answer, so the conflict is surfaced

This section used to end "there is no flag to disable the fitting: supplying the names is the
request." That was right about the intent and wrong about whose call the conflict is. **Extending
the box and keeping the width while the text overlaps the border are both legitimate drawings of the
same content**, and which one a diagram wants depends on the diagram. So the misfit is reported and
the **user** decides.

```python
spec = dt.spec({"item_width": 60}, names=[e["name"] for e in elements])
for conflict in spec.unanswered_conflicts:
    ask_the_user(conflict["question"])
spec = dt.spec({"item_width": 60}, names=[e["name"] for e in elements],
               on_misfit="overlap")        # their answer, relayed
```

| | Value |
|---|---|
| `on_misfit=None` (omitted) | nobody has answered; the default is applied and the conflict says so |
| `on_misfit="widen"` | the user chose the wider box |
| `on_misfit="overlap"` | the user chose to keep the width asked for |

- **Widening remains the default**, for the reason it was unconditional before: EA grows a box it
  cannot fit whatever the stored rect says, so it is the only answer under which the stored geometry
  is the geometry EA paints. What changed is that it is no longer silent.
- **`on_misfit` is an answer, not a setting.** A misspelled value is refused as a `BindingError`
  rather than falling through to the default, because "the user chose wrong" and "nobody answered"
  are opposite states.
- **`overlap` is not a return to the old behavior.** The width is the same one the old code produced
  and the conflict is still reported — the difference between the two is a choice on the record
  versus a default nobody saw. Under `overlap`, `widened` is `False` while `conflicts` is not empty:
  nothing moved, and something was still decided.
- **Each conflict is a `compose.FitConflict`** — a plain dict, so it crosses a tool boundary as
  JSON with nothing to import. Fields: `conflict`, `where`, `driver`, `driver_kind`,
  `requested_width`, `required_width`, `options` (each with its `width` and `effect`), `applied`,
  `width_applied`, `answered`, `question`, `note`, `detail`.
- **One mechanism, two sites.** `compose_layered_bands` reports the same record, in
  `result["conflicts"]`, when an explicit `min_band_width` is narrower than the bands' contents. Same
  two answers, same `on_misfit` argument. A caller handles both with one branch.

---

## 6. The loader API

`tools/bindings.py`. Anything invalid raises `BindingError`, whose message names the path into the
document.

| Call | Returns |
|---|---|
| `find_binding(technology, directory=None)` | The `Binding` for a technology id, or `None` if there is not one. Defaults to the skill's own `bindings/`. |
| `load_binding(path)` | Load, validate and resolve one file, following `extends`. |
| `load_binding_text(text, source)` | Validate and load from YAML text. No directory, so no `extends` resolution. |
| `available_bindings(directory=None)` | `{technology id: filename}` for every valid binding on hand. An invalid file is omitted rather than raising, so one bad file does not make the whole catalog unreadable; load it directly to see why. **A duplicate technology id is the exception and raises `DuplicateTechnology`** naming the id and every file that claims it — omitting one of two files that claim an id is not omitting it, it is picking a winner, and the readers of the directory used to pick different ones. |
| `declared_technologies(directory=None)` | `{technology id: filenames that declare it}` for every file that parses, validated or not. Identity only: the one view of the directory every reader agrees on. |
| `binding_conflicts(directory=None)` | The subset of the above with more than one file per id. Never raises, so an audit or a health check can report a shadowed id instead of failing on it. Empty for a clean directory. |
| `unvalidated_glyphs(name)` | The distinct characters of `name` that `HEADER_ADVANCE_PX` was never calibrated on — it was measured over printable ASCII in one font. The guard on that constant: a width predicted for a name carrying any of these is an extrapolation, and `spec(names=...)` reports it as `SpecFit.extrapolated`. |
| `implemented_grammars()` | The grammars the engine has a `compose_<grammar>` for, **read from `compose.py` on every call**. Never a written-down set: a hand-kept flag pinned to the engine by a test is two copies of one fact, and that shape once let a measurement tool report a remembered reach figure for a grammar that had already shipped. |
| `producible_grammars()` | `implemented_grammars()` plus the grammars EA's layout places — the answer to "can we produce this at all". |

Module constants: `GRAMMARS` (the vocabulary, a frozenset), `GRAMMAR_PLACEMENT` (grammar → who places
it, the one table the rest is derived from), `COMPOSED_GRAMMARS`, `EA_PLACED_GRAMMARS`, and
`IMPLEMENTED_GRAMMARS`, which is `implemented_grammars()` as at import — the same meaning and, for the
composed grammars that were already built, the same value it has always had, so a reach figure
derived from it does not move when the vocabulary grows. Code that changes the engine after import
must call the function.

On `Binding`:

| Member | Does |
|---|---|
| `diagram_type(name)` | One `DiagramTypeBinding`. Raises, naming what is declared. |
| `viewpoint(name)` | One `Viewpoint`. Raises, naming what is declared. |
| `profile(name)` | One `PresentationProfile`. Raises, naming what is declared. |
| `stereotype_for(concept)` | `ApplicationComponent` to `ArchiMate_ApplicationComponent`. |
| `concept_for(stereotype)` | The inverse. A stereotype without the prefix comes back unchanged — models contain elements stereotyped from other technologies, or from none, and a lookup helper is the wrong place to have an opinion about that. |
| `diagram_type_for_mdgdgm(value)` | Resolve an `MDGDgm=<Tech>::<DiagramType>` value, or `None` when it names another technology, so a caller can try the next binding. Only about half of real diagrams carry `MDGDgm` at all; the rest identify themselves through `Diagram_Type`, so resolution needs a second path. |
| `viewpoints_admitting(concepts)` | Viewpoints that admit **every** concept given, narrowest first — the one admitting the fewest concepts overall leads, ties broken by name. Ranking is on admissibility only; intent matching belongs to the caller. |

On `DiagramTypeBinding`:

| Member | Does |
|---|---|
| `spec(overrides=None, names=())` | Build a `compose.py` spec: `sizing.default` becomes `item_width` and `item_height`, and `spacing` is copied across verbatim — the **resolved** spacing, so an inherited gap reaches the engine. Caller overrides win, and an override naming a key the engine does not have is refused here, where the message can mention the binding. **Pass `names`** — the item names — and `item_width` is widened until the longest word in the widest of them clears the border. See §5.7. |
| `width_to_fit(name)` | Module function. The narrowest box width at which that one name reads as fitting: its longest space-free run at the measured advance, plus `lint.LABEL_MARGIN` of clearance each side. A full-width glyph is charged two character cells, which is a floor derived from Unicode East Asian Width and the measured maximum advance, not a second estimate; any other character outside printable ASCII is charged the calibrated advance and reported by `unvalidated_glyphs`. |
| `sizing` / `spacing` | Attributes. **Resolved**: what this diagram type states, over the measured values of the base diagram type it is drawn on. This is the pair a consumer wants. |
| `own_sizing` / `own_spacing` | Attributes. What this binding's own document stated, which is a different question and the one a provenance test asks — a figure is only this technology's measurement if this technology stated it. |
| `inherited_sizing()` / `inherited_spacing()` | What came from the substrate rather than from this file: the resolved mapping minus the stated one. |
| `substrate` | Attribute. The `<Tech>::<DiagramType>` the rest came from, or `""`. |
| `inherits` | Property. Whether a substrate was found at all. `False` for the root of the tree, and for a diagram type whose `base` the parent leaves unbound — where unstated slots fall back to the engine, as they did everywhere before §5.6. |
| `size_for(concept="")` | Box size for a concept, falling back to `default`. Takes the concept name, not the stored stereotype. |
| `claimed_channels()` | Channel to what the notation already uses it for, `fill` included. |
| `free_channels()` | Channels a second variable may legitimately use. |
| `channel_is_free(channel)` | Ask about one. |
| `default_route()` | The diagram type's default route. |
| `route_for(relationship)` | The route for a relationship type: `trunk_route` for anything in `trunk_for`, otherwise the default. |
| `draws_its_own_title` | Property. `True` when `title` is `drawn`. |
| `grammar_is_implemented` | Property. Whether the engine has a composer for this grammar. See §5.5. **Not** the same question as producibility. |
| `grammar_is_producible` | Property. Whether a diagram of this type can be produced at all today, by either route — a composed grammar that is built, or one EA's layout places. |
| `geometry_is_composed` | Property. Whether the coordinates are ours to compute. `False` means they come from EA. |
| `grammar_placement` | Property. Who places the geometry, as one of the three values in `GRAMMAR_PLACEMENT`. |
| `mdg_diagram_type` | Property. The `<Tech>::<DiagramType>` string, to compare against a diagram's own `MDGDgm`. |

On `Viewpoint`: `admits_concept(concept)`, plus `diagram_type`, `intent` and `admits` as read-only
attributes, and `effective_grammar`, `grammar_is_implemented`, `grammar_is_producible` and
`geometry_is_composed` — the last three returning `None` when the viewpoint states no grammar of its
own. `None` is not `False`: "this viewpoint has no opinion, ask its diagram type" is a different
answer from "we know we cannot", and returning `False` for both would make every ordinary viewpoint
look unsupported.

On `PresentationProfile`: `display_settings()`, which returns `set_diagram_display` keyword arguments
(see §8), and `collapses_parallel`, a property saying whether to collapse parallel connectors between
a pair onto one line. Collapsing hides relationships, so a profile that sets it needs an annotation
on the diagram saying what was summarized.

## 7. Worked example

Composing an application view over the Westbrook Bank reference model.

```python
from bindings import find_binding
from compose import compose_layered_bands

binding = find_binding("ArchiMate3")
if binding is None:
    ...        # nothing bound for this technology: say so, fall back to a plain graph layout

dt = binding.diagram_type("Application")
if not dt.grammar_is_producible:
    ...        # recorded, and nothing here can produce one yet: say so and stop
if not dt.geometry_is_composed:
    ...        # EA places this one. Create the elements, call layout_diagram with the
               # spacing from dt.spec(), then tidy: dt.size_for(), dt.route_for() and
               # the title convention. Do NOT compute coordinates.

result = compose_layered_bands(       # reached only when the geometry is ours
    [
        {"name": "Channels", "items": [{"id": 13477}, {"id": 13478}]},
        {"name": "Business Applications", "items": [{"id": 13479}]},
    ],
    dt.spec({"align": "center"}, names=["Channel Portal", "Mobile Channel",
                                       "PaymentsInitiationService"]),
)
```

`names` is the item names, in any order. It widens `item_width` when a name will not fit the
notation's measured box, and the returned spec says so - §5.7.

The two checks are in that order on purpose. `grammar_is_producible` is the one that says whether to
go on at all; `geometry_is_composed` is the one that picks the route. Reading
`grammar_is_implemented` alone conflates them and drops every diagram type EA would have laid out
perfectly well.

Then place with `ea_diagram("add_elements_to_diagram_bulk")`, passing the returned
`left`/`top`/`right`/`bottom` inside each `element_ids` entry (a dict with `element_id`) and `layout="none"`, and route connectors with
`dt.default_route()` or `dt.route_for("Realization")`.

Three things the binding answers that the spec does not carry:

- `binding.stereotype_for("ApplicationComponent")` gives the stereotype to query or write.
- `dt.size_for("Junction")` gives a concept its own box size. The spec carries only the default, and
  the engine sizes items uniformly within a band or a lane, so a concept needing its own size needs a
  band of its own, a lane override, or that size applied when you place it.
- `dt.draws_its_own_title` says whether to add a title element or leave it to EA's frame.

## 8. Two limitations

**`find_binding` returns `None` for an unbound technology, and that is normal.** Most repositories
use several technologies nobody has bound. A caller should say so and fall back to a plain graph
layout rather than composing against the wrong binding — which is also why the declared `technology`
is checked rather than the filename trusted.

> **The fall-back-to-a-graph advice has one exception, and it is not optional.** `SKILL.md` says to
> fall back to a plain graph layout when no grammar fits. That holds when no grammar fits **and the
> diagram type is not `ea-semantic`**. An `ea-semantic` type must never be laid out as a free graph —
> that is the entire point of the category. Hand a sequence diagram to a graph layout and you get the
> participants placed and the message order ignored, which is worse than not generating it, because it
> looks like a sequence diagram and is not one. Where the type is `ea-semantic`, say it is recorded and
> not producible, and stop. See §5.5.1 and `grammars.md` §9.

**`PresentationProfile.display_settings()` emits only settings verified to change what EA renders.**
There are seven: `hide_connector_labels`, `hide_element_stereotypes`, `hide_connector_stereotypes`,
`hide_attribute_types`, `hide_operation_return_types`, `hide_operation_brackets` and
`show_element_notes`. Each was established by rendering the diagram and reading the markup, against
content the setting could actually suppress — not by writing the value and reading it back, which EA
would echo either way.

**`compartments: none` does not remove a compartment.** EA's `SuppressedCompartments` was measured
through six value shapes against a class with populated attribute and operation compartments and
changed nothing every time, so there is no verified way to take a compartment off a diagram. What is
available is reducing its detail to names: `balance` rather than `balance: Decimal`, `getBalance`
rather than `getBalance(): Decimal`. So `none` and any explicit compartment list both mean "the least
detail EA will give us", and `all` means full detail. That is a smaller promise than the profile
vocabulary suggests, and it is stated rather than papered over — a profile must never promise a
suppression that silently does nothing.

**`notes` is the one setting whose polarity does not flip.** Everywhere else a profile says what it
shows and EA is told what to hide. Element notes are hidden by EA *by default*, so `notes: true`
becomes `show_element_notes: True` rather than a `hide_` flag set False. Tidying that for consistency
turns notes off in the detail view and on in the executive one, which is exactly backwards.
