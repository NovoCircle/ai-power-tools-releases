# Compositional Grammars — Choosing and Judging a Diagram Layout

Detail supporting [`../SKILL.md`](../SKILL.md). This file is about judgment: which shape of
diagram suits which content, and what separates a composed diagram a reader trusts from one they
squint at. It is deliberately not API documentation — the arithmetic and the parameter names live
in [`../tools/compose.py`](../tools/compose.py), whose docstrings are the reference for those.

Read the coordinate convention below before anything else. It is the one piece of mechanical
knowledge in this file, and it is the single easiest thing to get backwards.

---

## 1. EA's coordinate system

Sparx EA does not use screen coordinates. Verified against EA 17.1:

| Edge | Sign | Relationship |
|---|---|---|
| `left`, `right` | positive, increasing rightward | `right > left` |
| `top`, `bottom` | **negative**, increasing upward | **`top > bottom` numerically** |

Therefore:

```
width  = right - left
height = top - bottom          <-- not bottom - top
```

A real element as EA placed it: `left=50, top=-50, right=190, bottom=-110`. That box is 140 wide
and 60 tall.

Three consequences that trip people up:

- **Moving an element down the diagram makes `top` and `bottom` more negative.** A band stack
  descends by subtracting.
- **The visually topmost rect is the one with the largest `top`.** So the bounding box of a set of
  rects takes the *maximum* of the tops and the *minimum* of the bottoms.
- **An intersection test written for screen coordinates reports the wrong answer**, and it does so
  silently — two boxes that genuinely overlap come back as disjoint. Anything that checks for
  collisions has to be written for this axis, and tested against a known-overlapping pair.

Everything downstream inherits an error here: the layout looks plausible in the numbers, and then
elements sit on top of each other in the diagram. Pin the convention with a test before building
on it.

---

## 2. What a grammar is, and why the split matters

A compositional grammar is a rule for turning *content with a known shape* into *geometry*. It is
not a layout algorithm in the graph-drawing sense — nothing here minimizes edge crossings or
relaxes a force model. Each grammar assumes the content already has a structure (an ordered set of
bands, a set of parallel sequences) and places boxes accordingly, by arithmetic alone.

That restraint is the point. A grammar is deterministic and inspectable: given the same content and
the same sizing you get the same diagram, every time, and you can reason about why a box is where
it is. EA's own automatic layouts are the right tool when the content has no such structure — a
dense dependency graph, for instance — and that case is a named choice here, `graph` (§8), not a
failure to pick a grammar. Reach for a composed grammar when the content *does* have structure and
you want the diagram to show it. One more value, `ea-semantic` (§9), records the diagram types whose
own definition dictates the arrangement, so that computing coordinates for them would be wrong.

The capability splits three ways, and each corner holds a different kind of knowledge:

| Corner | Holds | Lives in |
|---|---|---|
| Prose | Judgment — which grammar suits this content, what good looks like, when to refuse | `SKILL.md`, this file |
| Code | Arithmetic — deterministic, unit-testable, no repository access at all | `tools/compose.py` |
| Data | Language specifics — sizing, spacing, routing per modeling language | the bindings |

The practical test of the split: **`compose.py` contains no modeling-language names.** No profile,
no technology id, no stereotype. A band of boxes is the same arithmetic whether the boxes are
drawn as capabilities, application components or process steps. If a change to the engine needs a
branch on which language is in play, the specifics belong in a binding instead, and the engine
should be taking one more parameter.

---

## 3. Status — eight grammars, three placements

The vocabulary has **eight** values. Six are layouts this library computes coordinates for; the
other two are the cases where it computes none. What separates them is *who places the geometry*,
because that decides what may be done with a diagram type that names the grammar.

| Grammar | Who places the geometry | Status |
|---|---|---|
| Layered bands | Our arithmetic | **Implemented** — `compose_layered_bands` |
| Lanes | Our arithmetic | **Implemented** — `compose_lanes` |
| Nested grid | Our arithmetic | **Implemented** — `compose_nested_grid` |
| Radial | Our arithmetic | **Implemented** — `compose_radial` |
| Two-column cycle | Our arithmetic | **Implemented** — `compose_two_column_cycle` |
| Computed geometry | Our arithmetic, not yet written | **Not built.** What remains under the name: the treemap |
| Graph | EA's own layout, which we tidy afterward | **Producible today**, with no composer behind it |
| EA-semantic | The diagram type itself | **Not producible.** Recorded so the gap is visible as data |

**How the list grew.** The analysis first resolved the corpus into **four** grammars. Measuring the
rows grouped under "computed geometry" before building it showed they do not share an arithmetic:
placing items on a circle, packing rectangles so their *areas* encode a number, and drawing a
waveform against a time axis are three unrelated pieces of code. The polar one was split out and
built. The waveform was not left behind as unfinished work of the same kind; it was moved to a
different value altogether, and §7 records why.

Two values were then added for a different reason. Most diagram types are graphs or trees, and the
composed grammars have nothing to say about them, yet a binding must name a grammar. So whole
families of diagram type went unrecorded for a schema reason rather than a real one, and an
omitted diagram type is indistinguishable from an oversight. `graph` and `ea-semantic` exist so
that every diagram type can be recorded honestly: one as "EA places it, and that is fine", the
other as "classified, and not producible yet".

**Then a sixth layout.** `two-column-cycle` was the last row of the corpus audit still waiting on
engine code — everything else unproducible was waiting on artwork or on a decision. It is its own
grammar rather than a radial variant because its arithmetic is a split and a pitch rather than a
bearing, and because its boxes are deliberately different heights, which no other composed layout
allows. §6b.

**Composed and producible are different questions.** Whether the engine has a composer for a
grammar is one fact. Whether a diagram of that type can be produced at all today is another, and
the two only coincide for the composed grammars. `graph` is producible and has no composer;
`computed-geometry` has a composer pending and is neither; `ea-semantic` is neither and has nothing
pending. Do not answer one question with the other's answer.

Do not tell a user computed geometry is available, and do not improvise a call to it. If content
plainly wants it, either compose it from the implemented grammars and say what you approximated, or
hand the geometry over explicitly and say you did it by hand. Do not tell a user an `ea-semantic`
type can be produced either, and do not quietly lay it out as a graph (§9).

---

## 4. Layered bands

Horizontal bands stacked top to bottom, each band holding items laid out left to right.

### What it suits

Content where the vertical axis carries a *meaning* — a layering, a tiering, an order of
abstraction — and the horizontal axis carries only membership.

- Reference models and layered architectures: channels above applications above data above
  infrastructure.
- Capability maps, one band per level of the capability hierarchy.
- Technology stacks.
- Maturity or tier breakdowns, where each band is one tier.

The test: can you name what moving an item from one band to another would mean? If the answer is
"nothing, the bands are just rows I needed", this is the wrong grammar and the content is probably
a flat set.

### What makes it read well

- **The layer order is the reader's mental order.** Consumers at the top, foundations at the
  bottom, or the reverse — but one of the two, consistently, and matching whatever convention the
  audience already uses.
- **Uniform item size within a band.** This is a rule, not an accident of the implementation. A row
  of boxes at four different widths reads as four different kinds of thing even when it is one kind,
  and the reader spends attention decoding the variation instead of the content. Vary size
  *between* bands when the bands hold genuinely different kinds of thing; never within one.
- **One width for every band, so the stack has a straight right edge.** A band is a full-width strip
  standing for a layer that spans the diagram, so a band of two items drawn narrower than the band of
  three above it reads as a mistake in the drawing rather than as a fact about the content. The engine
  gives every band the widest band's width and leaves the slack empty inside the sparse ones. A
  `min_band_width` above what the contents demand is a floor under the width the whole stack ends up
  with; it widens the stack and never narrows it, so it cannot leave one band narrower than another.
  This is **the opposite of the nested grid's rule** and the difference is deliberate — see §6, and
  do not tidy the two into agreement: a band is a strip whose raggedness reads as a drawing error,
  while a nested-grid container is sized by its contents because its size *is* the data.
- **A `min_band_width` NARROWER than the contents is a conflict to raise with the user, not to
  settle.** It used to be outvoted in silence: the stack came back at the width the contents needed
  and nothing said the explicit figure had been ignored. Both answers are legitimate drawings —
  extend the bands to fit, or hold the width and let the items run past the right edge — so
  `compose_layered_bands` reports the clash in `result["conflicts"]` and takes the user's answer as
  `on_misfit="widen"` or `on_misfit="overlap"`. Widening is what happens when nobody answers, because
  it is the only one of the two that keeps every item inside its band. **Ask; do not take the
  default as agreement.** This is the same mechanism, the same record and the same two answers as a
  name too long for its box — see [`bindings.md`](bindings.md) §5.7.1.
- **Band heights that follow their contents.** A band with two items should not be as tall as a band
  with twelve. Fixed band heights leave holes that read as missing content. Height is where this
  grammar carries its variation; width is not, which is why the two are treated differently.
- **Wrapping rather than shrinking.** When a band holds more items than fit, run them onto a second
  row at the same size. Shrinking boxes to fit one row destroys the uniform-size rule and makes the
  crowded band look less important than the sparse one.
- **A visible label strip per band.** The band's own rect, with room for its name, is what tells the
  reader the vertical axis means something.

### What makes it read badly

- **Too many bands.** Past about seven the layering stops being a structure and becomes a list.
  Group the bands or split the diagram.
- **One enormous band.** A band with forty items wrapped over five rows is a grid that has been
  mislabeled as a layer. Either the band should be several bands, or the content wants a nested
  grid.
- **Empty bands with no explanation.** An empty band is legitimate — it says "this layer exists and
  is deliberately unpopulated" — but only if the label makes that claim on purpose. The engine keeps
  an empty band's label row rather than collapsing it silently, so the emptiness is visible and the
  author has to mean it.
- **Reading anything into how much of a band is filled.** Bands share a width, so a sparse band has
  empty space on its right that means nothing beyond "this layer has fewer things in it than the
  busiest one". If the horizontal extent is supposed to carry a measure, this is the wrong grammar.
  (`align` still chooses where a band's row sits inside the width it is given — flush left by default,
  centered on request. It no longer moves the bands themselves, because they already share both
  edges.)
- **Bands used to carry two dimensions at once.** If the horizontal position within a band also
  means something (time, priority), say so in the diagram, or use a grammar where it is explicit.
  A reader will not guess.

---

## 5. Lanes

Parallel tracks, each holding a sequence of items that flows along the track. Swimlanes.

### What it suits

Content with two axes where one is *sequence* and the other is *responsibility*.

- Process flows, one lane per role, actor, system or organizational unit.
- Value streams, one lane per stage owner.
- Handoff-heavy workflows, where the interesting content is who passes what to whom.
- Release or migration sequences, one lane per workstream.

The test: is there a step order, and does the identity of who performs each step matter? Both have
to be true. Only the order matters, and a single flow is clearer. Only the ownership matters, and
layered bands or a grid is clearer.

### What makes it read well

- **Items at the same sequence index line up on the flow axis.** This is the most important
  property of the grammar and the reason it is worth implementing rather than eyeballing. A handoff
  from one lane to the next should read as a step *across*; if the target step sits half a box
  ahead, the reader has to work out whether that offset means something. It does not, and they
  should never have to ask. The engine allocates one slot per sequence index, sized to the longest
  item at that index in any lane, and centers each item in its slot. A caller can verify it: every
  item comes back carrying the slot it was placed in.
- **Few lanes.** Three to six is comfortable. Beyond that the eye loses the horizontal track and
  the diagram becomes a scatter of boxes.
- **Lane thickness that follows the largest item in it.** A lane with one big item should be thick;
  its neighbors should not be padded to match.
- **Lanes that abut.** Swimlanes are a partition of one space, not a set of separate diagrams.
  Touching lane bands say that; gaps between them say the lanes are unrelated.
- **A label area inside the lane band**, at the leading edge — down the left of a horizontal lane,
  across the top of a vertical one. Labels floating outside the band drift when the diagram is
  edited.
- **An orientation chosen for the content, not out of habit.** Horizontal lanes suit long
  sequences and short lane names. Vertical lanes suit many lanes, or lane names long enough that a
  left-hand label column would eat the canvas.

### What makes it read badly

- **A lane that is nearly empty.** One item in a lane of twelve slots is eleven slots of white
  space the reader keeps scanning for content. Either the lane belongs on the diagram as a whole
  and its emptiness is the message — say so — or that participant is not part of this flow.
- **Ragged lane lengths pretending to be alignment.** If lane A has eight steps and lane B has two,
  the grammar will still align B's two, but the diagram is claiming a parallelism that is not there.
- **A sequence index used for two different things.** If index 3 means "third step" in one lane and
  "third thing this team owns" in another, the alignment is actively lying. Lanes must share one
  sequence.
- **Lanes as a stand-in for layering.** A swimlane diagram with no flow along the lanes is layered
  bands with the wrong label. Use bands.
- **Crossings that are not drawn.** Lanes make handoffs legible only if the connectors between
  lanes are actually placed. A correct lane layout with no connectors is a seating plan.

---

## 6. Nested grid

Containers within containers, each container laid out as a grid of its children: a domain holding
subdomains holding applications.

`compose_nested_grid(nodes, spec=None)`. The input is a recursive tree rather than a flat list — a
node carrying `items` is a container and needs a `name`; a node without `items` is a leaf and needs
an `id`:

```python
compose_nested_grid([
    {"name": "Retail", "items": [
        {"name": "Onboarding", "items": [{"id": 101}, {"id": 102}]},
        {"id": 103}]},
    {"name": "Payments", "items": [{"id": 104}]},
])
```

Leaves and containers may sit side by side at any level, and a leaf at the top level comes back with
`container_id: None`.

### What it suits

Content where **containment is the whole structure** and there is no sequence: two or three levels of
grouping, and usually no connectors at all.

- Domain and subdomain maps; capability maps where the levels are genuine decomposition.
- Portfolio views grouped by owner; application taxonomies.
- Information models grouped by subject area.
- Organization structures, where the nesting *is* the reporting line.

The test: would an arrow between two of these boxes add anything? If the answer is yes, the content
is a graph and this is the wrong grammar. A nesting that also needs arrows to be read is not a
nesting.

### What makes it read well

- **Nesting stops at two or three levels.** Past three a reader can no longer tell which box owns
  which, and the outermost container becomes a frame rather than a statement. The engine **refuses**
  a fourth level rather than warning about it — `max_grid_depth` defaults to 3 and a caller who
  genuinely wants more raises it deliberately.
- **Containers sized by their contents.** A group holding twenty things should be visibly bigger than
  one holding two. Sizing containers alike is the fastest way to make a portfolio view lie about
  where the weight is. A container is therefore **not** stretched to fill its grid cell, and a row of
  containers can end at different depths — the ragged edge is the price and it is worth paying.

  **This is the opposite of the layered-bands rule (§4), on purpose. Do not reconcile them.** There,
  every band takes a common width because a band is a full-width strip and raggedness reads as a
  drawing error. Here, size *is* the information: snapping containers to uniform cells drew a
  four-child grouping at exactly the same size as a two-child one, which is tidier and wrong about
  the thing the diagram exists to show. The rule differs because what the rectangle *means* differs.
- **Grids close to square, not one long row.** A grouping rendered as a single row reads as a list
  and the grouping disappears. The engine defaults to `ceil(sqrt(n))` columns; `grid_columns`
  overrides it per composition or per container when the content has a real column meaning.
- **Uniform cell size within a level.** Item size is stated by the *parent*, so sibling leaves
  cannot disagree — varying sizes among siblings is what most makes a generated diagram look
  machine-made. Levels may differ from each other; an override does not cascade to grandchildren.
- **Each container's label legible at the zoom the reader will actually use.** The title strip is an
  extra inset at the top of the container, above the padding, so a name never sits on its children.
- **Real whitespace between cells.** A grid packed edge to edge reads as one block. Note that a
  no-overlap check cannot see this: touching rects do not overlap, by design.

### What makes it read badly

- **Four or more levels deep.** See above; this is the one the grammar refuses outright.
- **Containers sized alike.** A container with two children looking as significant as one with
  twenty is a measurement error presented as a picture.
- **Arbitrary grouping.** A grid of "Other" is a confession, not a category. If a third of the
  content lands in it, the grouping is wrong.
- **An empty container with no explanation.** Legitimate — it says "this grouping exists and is
  deliberately unpopulated" — but only if that is meant. The engine keeps an empty container's label
  and one cell of space rather than collapsing it, so the emptiness is visible and the author has to
  own it.
- **Connectors added to "clarify" the nesting.** They contradict it. If the relationships matter more
  than the grouping, use a graph layout.

### Note on the EA mechanism

Nesting in EA is not only geometric. A box drawn inside another box is not the same as an element
genuinely owned by that container, and the two can disagree. **Get the model relationship right
first**; the geometry is the easy half. `container_id` on every item and `parent_id` on every
container are returned precisely so the ownership can be built from the same structure the geometry
came from, rather than inferred back out of the rectangles.

---

## 6a. Radial

A hub and its spokes: items distributed on a ring around a center, optionally with a further ring
hanging off each one.

`compose_radial(nodes, spec=None, hub=None)`. The hub is an **item**, not a container — it is one
of the things on the diagram rather than something enclosing them — and a node carrying `items`
gets its own outer ring, which is what turns a hub-and-spoke into a radial tree.

**Sizing comes from the spec, for every ring.** `item_width`, `item_height` and `radius` are stated
once and apply to the whole composition. There is **no per-node sizing in this grammar**, and a
sizing key on a node or on the hub is **refused** with an error naming it — not accepted and
ignored, which is what it used to be. Per-ring sizing does exist in the engine: `compose_radial_tree`
resolves those same three keys per node, and it also gives a branch angular room in proportion to
what that branch carries instead of handing every branch the same wedge, which is what makes
per-ring sizing worth having. Reach for that grammar when the rings must differ.

### What it suits

Content with **one center and peers around it**, where the peers have no order among themselves
that the reader needs. Capability wheels, service catalogs around an organization, a mind map, a
stakeholder map, a cycle of four or five stages.

The test: is there genuinely a center? A radial layout claims one. If every item is a peer and
nothing sits at the middle, the ring is decoration and a grid says the same thing more plainly.

### What makes it read well

- **Equal spokes, which the engine now guarantees and the caller used to have to engineer.** The
  engine places each item so the *drawn* spoke — the gap between the hub's border and the item's
  border, along the line between them — is the same length all the way round, whatever shape the
  boxes are. `radius` means that gap. Item centers therefore do **not** all sit at one distance from
  the hub, and should not: the item at the side has to sit further out than the one at the top by
  exactly the amount the two boxes reach further along that bearing.

  What this replaced, and what it was wrong about: this file used to tell you to prefer **square-ish
  items**, on the reasoning that a wide flat box "reaches closer to the center at the top and bottom
  of the ring than at the diagonals". That had the direction backwards. A box centered on the ring
  reaches back toward the hub by half its *height* at the top and bottom and by half its *width* at
  the sides, so a wide flat box **crowds the hub at the sides and stands off at the top and bottom** —
  the opposite of what was written. Measured on a real ring of eight 140x60 boxes around a 140x60
  hub at a radius of 220, the spokes came out 160 at the top and bottom, about 136 on the diagonals
  and 80 at the sides.

  The advice was also incomplete, in a way worth knowing even now. Square items were never enough:
  a square is not a circle, and its border is 41% further from its center through a corner than
  along an axis. With a square hub and square items on a ring of eight, that spread the spokes by
  about 41% of the box's side — 41 units for 100x100 boxes, and more for bigger ones. Only a circle
  would have removed it, and EA draws boxes. Item shape is now the engine's problem rather than
  yours: the drawn gap comes out at the requested radius at every position, to within a unit of
  rounding.
- **Few enough to see the circle.** Past about a dozen the ring reads as a crowd. The engine widens
  the radius rather than letting items collide, and that widening is **bounded**. It has to be:
  fitting *n* boxes into a fixed sweep needs a radius that grows about in proportion to *n* and
  inversely to the sweep, so a narrow fan asked to hold enough items widens without limit. The
  engine stops at `max_radius` — default **900**, the same number `wrap_width` uses for the widest a
  composition's content may get — and **refuses** past it, naming the count, the box size, the arc,
  the radius that would have been needed, and the four ways out: fewer items on the ring, a wider
  sweep, smaller items, or `max_radius` raised deliberately.

  Measured, at 90x88 items over a 60-degree fan: 238 units of radius at three items, 654 at six, and
  a refusal from eight upward — where the unbounded engine returned 932 at eight, 2046 at sixteen and
  3161 at twenty-four — the last of those a composition measuring 2873 x 1687 units, most of it the
  empty middle of a 60-degree fan. An **inner** ring runs further still, because its arc is a
  fraction of the outer step: twelve spokes of three branches over a 180-degree sweep settled ring
  one at 576 and demanded 1178 on every inner ring, a figure the result dict never reported. A very large circle was the old outcome and it was called the honest
  failure; a refusal that says which input to change is the honest outcome, and it is a failure the
  caller can act on.
- **A hub that earns its place.** The center position is the most emphatic on the diagram.
- **One ring, or two at most.** The engine refuses a third by default.

### What makes it read badly

- **No real center.** See above; this is the common misuse.
- **A ring used to imply sequence.** A reader follows a cycle clockwise whether or not one is meant.
  If the order is arbitrary, say so, or use a grid.
- **Long labels.** A wide label forces a wide box. That no longer makes the spokes uneven, but it
  still costs you twice: the ring has to grow to keep wide boxes from colliding — far enough, on a
  partial arc, to be refused outright — and the items' outer
  corners stick out by different amounts even though their inner edges line up, so the ring's outer
  silhouette is the uneven thing instead. Shorter labels still read better; they are no longer
  load-bearing.
- **Arcs you cannot draw.** Reference radial diagrams commonly use curved connectors. The connector
  vocabulary here has Direct, Auto, Custom, Tree, Lateral, Orthogonal and Bezier — **no arc**. A
  generated equivalent is structurally right and visually not identical; say so rather than
  reporting it as reproduced.

---

## 6b. Two-column cycle

A cycle drawn as two columns: the flow runs down one and back up the other, closing the loop across
the top.

`compose_two_column_cycle(items, spec=None)`. `items` is the cycle **in order**, first item at the
top left. There are no containers — a cycle is a ring of peers and nothing encloses them — so an
item's `container_id` is always `None`.

This is the one composed grammar whose boxes are deliberately **different heights**, and that is the
whole reason it is a grammar of its own rather than a parameter on the radial one.

### What it suits

A closed sequence of a handful of steps or states where **each step carries content of its own** —
entry, do and exit behavior, a couple of lines of code, a short description — and where the reader
needs to see that the sequence returns to its start.

A state machine drawn as a cycle is the case it was built for: pedestrian crossing, order
lifecycle, an approval loop, a shift rotation. Anything where the answer to "and then?" for the last
item is "the first one".

The test: is it genuinely closed, and does the order matter? If the items are unordered peers around
a center, that is §6a and a ring says it better. If the order matters and it does not close, that is
a lane (§5) or a plain graph (§8) — a cycle layout drawn on a non-cycle is a promise the content
does not keep, and a reader will hunt for the missing closing step.

### What makes it read well

- **Content in the boxes.** The layout exists to make room for it. A cycle of five empty boxes is a
  ring with corners; use §6a.
- **A count you can see round.** Four to eight. Above about twelve the columns are taller than a
  screen and the closing step stops being a step.
- **Ordered content, ordered items.** The composer places by list position and nothing else. Hand it
  the cycle in the order it is read.
- **Connectors you add yourself.** The arrangement is what makes the loop legible; nothing in the
  composer draws it. Route the steps down each column, the fold across the bottom and the closing
  step back to the first item.

### What it guarantees, given variable heights

This is the part worth reading before using it, because "two columns" is the easy half and the
heights are where a layout that assumes uniform boxes drifts out of alignment.

- **One width for every item.** Both columns have a straight left and a straight right edge, so the
  cycle has a rectangular outline. Width carries nothing here — a compartment wraps — so varying it
  would be variation a reader has to decode for no gain. Same argument as §4's shared band width,
  applied to the other axis.
- **One row pitch for the whole composition**, the tallest item plus the vertical gap. Not per row:
  a pitch that followed each row's own tallest member would make the spacing uneven, and the §10
  spacing check judges a column of unequal boxes on its **center-to-center** pitch, so it would say
  so.
- **Aligned centers, not aligned tops.** Each item is centered in its row's slot. That is what keeps
  the pitch even, and what makes the fold and the closing step come out horizontal: row *r* in the
  left column and row *r* in the right share a center line, to within a unit of integer rounding.
  Aligning tops instead leaves the center pitch varying by half the difference between successive
  heights — tens of units on this grammar's content.
- **The row pitch is a floor, not a promise.** The tallest box comes from the content, so a pitch too
  small for it is widened rather than refused, and the pitch actually used comes back on the result —
  the same contract as the radial radius. The **column** pitch is not treated that way: a column
  pitch narrower than the item width is the caller contradicting their own spec, and it is refused.
- **Not one size.** Two boxes of different heights are different sizes. Do not hand the whole cycle
  to the uniform-sizing check in §10 as a single role: it compares heights as well as widths and will
  report the content as a defect. Declare a role per height. The shared width is the uniformity this
  grammar promises, and it is the part worth checking.

### Where the odd count puts the gap

With an odd number of items one cell is empty, and which one is a decision rather than an accident.
The first `ceil(n / 2)` items run down the left column and the rest run up the right, **anchored at
the bottom row** — so the fold at the bottom is a horizontal hop at every count, the empty cell is
the **top of the return column**, and the step that closes the loop is the diagonal one.

One of the two turns has to be diagonal at an odd count. Anchoring the return column at the top
instead gives a horizontal closing step and a diagonal fold. The fold is an ordinary step in the
sequence and wants to read as "and now across"; the closing step is already understood as "and back
to the beginning" and survives being drawn at an angle. So the diagonal is spent on the edge whose
meaning the reader already has.

### What makes it read badly

- **A sequence that does not close.** The commonest misuse, and the one the layout cannot rescue: the
  shape says "cycle" whether or not the content does.
- **Uniform empty boxes.** Nothing is wrong with the output; it is just a worse ring. Use §6a.
- **One box very much taller than the rest.** The pitch is set by the tallest, so a single 400-unit
  box spaces every other row 400 apart and the cycle becomes mostly whitespace. Split the long
  content into a note, or accept the spacing — do not fix it by shortening the pitch, which is what
  the floor exists to prevent.
- **Too many items.** Twelve is the point at which the columns stop being readable together. Split
  the cycle or summarize a run of steps into one.
- **Reading the two columns as two groups.** They are one sequence folded, not a left-hand set and a
  right-hand set. If a reader could plausibly take them as two categories, label the fold or use
  lanes.

---

## 7. Computed geometry — *not built*

Positions derived from data rather than from structure: a two-axis placement where both coordinates
come from element properties. A risk/value bubble chart, a technology radar, a time-phased roadmap.

**What is left under this name is the treemap**, where area encodes a quantity. It was once two
things, and the other is not here any more: the radial arrangement was split out and built, and the
timing diagram was moved to `ea-semantic` (§9).

**Why the timing diagram does not stay here.** A timing diagram draws a waveform per participant
against a shared time axis. The measurement is what settled it: the horizontal axis *is* time, and
every timeline spans the canvas to carry it, so no two timelines are ever horizontal neighbors —
the horizontal gap between neighbors has no samples at all, because it is not a quantity that diagram
type has. The type dictates the arrangement; coordinates are the wrong output for it, which is the
definition of `ea-semantic`, not of a composed grammar we have yet to write.

The move matters for a reason beyond tidiness. A diagram type recorded under a composed grammar that
is not built starts reporting itself composable **the day that composer ships**. Left here, the
timing diagram would have been reported as composable the moment a treemap composer arrived, and
something would then have composed a waveform as a treemap. Recording it under a grammar that will
never have a composer is what keeps that from happening. The same applies to any future type: do not
park a diagram type under `computed-geometry` to get it into a file.

A time-phased roadmap is a different case. There the arrangement is ours to choose and the dates are
the data we position by; in a timing diagram the type itself has already fixed the arrangement.

**Would suit:** portfolio assessments with two scored dimensions, radars with a ring per horizon,
roadmaps where horizontal position is a date, and the treemap.

**Would read well when:** both axes are labeled and their units stated; the scale is honest — a
linear axis for a linear measure, and no silent rescaling to fill the canvas; overlapping points
are resolved by a stated rule rather than left stacked; the source of every score is recorded
somewhere the reader can find.

**Would read badly when:** an axis is unlabeled — which turns a measurement into decoration; the
scores are invented to justify a position the author had already chosen; collision avoidance moves
a point far enough that its position no longer matches its data. A computed diagram claims
precision, so its geometry has to earn it. If the data is not good enough to defend, one of the
other grammars is the honest choice.

---

## 8. Graph — *EA places it*

A graph or a tree. **We compute no coordinates: EA's own layout places the elements and we tidy
afterward.** This grammar is fully **producible**, and it has no composer because it needs none.

### What it suits

Content whose relationships *are* the structure, and where nothing about the content says where a
box has to sit.

- Dependency and interaction networks: components and what each depends on, services and their
  consumers, systems and the flows between them.
- Structural models: things and the associations between them, parts and how they connect.
- Hierarchies and taxonomies drawn as trees, and decision structures that branch.
- Flows that have no owners: steps and branches with no responsibility axis.
- Most other diagram types. Each composed grammar assumes a particular shape — strata, owners,
  containment, a center — and most diagram types have none of them. This is their honest home,
  not a consolation prize.

Two tests, and both should pass:

1. **Would a general-purpose layout produce something a reviewer would accept?** If yes, this is the
   grammar. Do not downgrade the type to `ea-semantic` merely because the result was not *composed*;
   not-composed and not-producible are different facts.
2. **Is there a structure a composed grammar would show?** Strata you can name, owners of steps,
   genuine containment, a real center. If there is, that grammar serves the content better and this
   one is the wrong choice. A graph of a layered architecture is a layered architecture with the
   layers thrown away.

### What we still contribute

Everything except the coordinates. A `graph` binding carries the measured element sizes, the spacing
(which the layout call reads as layer and column spacing, so the figures are not wasted on a grammar
that computes nothing), the default and trunk routing, the title convention, and which visual channels
the type already claims and which are free. That is the difference between a diagram that reads as
the right kind of diagram and one that merely contains the right elements.

### What makes it read well

- **Sizes from the type, uniform by role.** EA's layout decides where boxes go, not how big they
  are, so the same "same role, same size" rule as every other grammar applies and the tidy step is
  where it is enforced.
- **Spacing stated, not left at the layout's default.** The gaps come from the binding, so a diagram
  of a given type looks like the others of its type.
- **One routing style throughout**, the binding's default, with the trunk route only for the
  relationship types the diagram habitually draws as a shared trunk. A mixture of routing styles on
  one diagram reads as several diagrams pasted together.
- **A title per the type's convention** — drawn on the canvas or supplied by EA's frame, never both
  and never neither.
- **The geometry checks run after the layout call.** EA placed the boxes, so the no-overlap,
  positive-size and fits-the-canvas checks in §10 are things to verify, not things the engine
  guarantees.

### What makes it read badly

- **Reaching for it because no other grammar came to mind**, when the content does have strata,
  owners, containment or a center. See the second test above.
- **Reading meaning into position.** The layout places boxes by connectivity, so where a box sits
  says nothing. If horizontal or vertical position is supposed to carry a value, this is the wrong
  grammar, and the diagram must not imply otherwise.
- **Hand-nudging boxes after the layout** until connectors cross that did not before. Tidy the sizes
  and routing; leave the placement.
- **A graph too dense for any layout to untangle.** Split it, or filter it, before drawing it.

### What it refuses

It refuses to stand in for a composed grammar to make a coverage figure look better, and it refuses
diagram types whose arrangement the type itself dictates. A message exchange laid out as a free
graph has all its elements and is no longer a message exchange; that belongs in §9, not here.

---

## 9. EA-semantic — *not producible, recorded*

The diagram **type** dictates the arrangement, and coordinates are the **wrong output**. Placing
boxes on these is not tidying; it is fighting the editor, which derives the arrangement from the
content.

**This value is not producible**, and it is recorded rather than omitted precisely so that an omitted
diagram type stops being indistinguishable from an oversight. "Classified, not producible yet" is a
fact someone can plan against. A missing entry says nothing.

### How it differs from computed geometry

The two are easy to confuse, and confusing them is the expensive mistake, so plainly:

- **`ea-semantic`** means *coordinates are the wrong output.* The arrangement belongs to the type.
  Nothing is pending, because no coordinates we could write would be right.
- **`computed-geometry`** means *the arithmetic exists but we have not written it.* Coordinates are
  the right output, and one day a composer will produce them.

A waveform drawn against a time axis is the instructive case. It looks like arithmetic we have not
written, and it was first filed that way; but the axis is dictated by the type, so it is `ea-semantic`
(§7 has the reasoning).

### What it suits

Diagram types whose quality is order, not geometry.

- **Message exchanges**: participants each with a lifeline running down the page, and messages
  between them ordered from top to bottom. The order across and down the page is derived from the
  message sequence. Measured, the horizontal spacing is an even pitch no author produces by hand,
  which is the signature of an editor doing the placing, and a lifeline's height is set by how many
  messages it carries, so no element size is stable enough to state.
- **Timing diagrams**: a waveform per participant against a shared time axis, where each timeline
  spans the canvas and no two are horizontal neighbors.

The test: **does the type itself say where things go, so that any coordinates we wrote would only
restate its rule, and get it wrong as soon as the content changed?** And is the quality of the diagram
something other than geometry — the order of the messages, the shape of the waveform?

Measure before you classify. A type that *sounds* sequential is not necessarily `ea-semantic`: if
authors place its elements at freely chosen positions, in many different sizes, with gap
populations that look like an ordinary graph's rather than an even pitch, EA is not imposing the
arrangement and the type is `graph`. Resemblance to a sequence is not the test; whether EA dictates
the placement is.

### What it refuses

- **Composing it.** There is no composer and none is pending. A caller must not write coordinates
  for one of these types.
- **Being laid out as a graph** to make the diagram appear. Do not promote an `ea-semantic` type to
  `graph` because it would raise the coverage figure; the elements would be present and the diagram
  would no longer be of that kind. Say the type is recorded but not producible, and stop.
- **Being judged by geometry.** The overlap and sizing checks in §10 say nothing about whether a
  message order is right, so passing them proves nothing here.

---

## 10. Reviewing any composed diagram

Whatever the grammar, these hold. For the composed grammars the first three are guaranteed
arithmetically by the engine; for a `graph`, EA placed the boxes, so they are checks to run after
the layout call rather than guarantees. The rest are judgment and need a human, or an author acting
like one.

1. **No two items overlap**, and no two containers overlap. Items sitting inside their own container
   is expected and is not an overlap — check items against items and containers against containers,
   never the two sets mixed.
2. **Every rect has positive width and height**, and obeys the sign convention in §1.
3. **The composition fits the canvas.** Check the returned bounding box against the space available
   before placing anything.
4. **Uniform sizing within a role.** Same band, same size. Same lane, same size. A box that is
   bigger for no stated reason will be read as more important. *For no stated reason* is the whole
   rule: a two-column cycle's boxes differ in height because they hold different amounts of
   content, and a nested-grid container is sized by its contents, so in both cases the role is
   narrower than "everything on the diagram" — see §6b and §6.
5. **The axes mean something, and the diagram says what.** If the vertical axis is a layering, the
   band labels carry it. If the horizontal axis is a sequence, something on the diagram says so.
6. **A reader who was not in the room can name the structure.** If they cannot say why the boxes are
   arranged this way, the grammar was the wrong one or the content was not ready.

### Worked shape

An example composition over the Westbrook Bank reference model: three bands, centered, with
`Channels` holding three items at the default 140x60 and `Business Applications` holding two at
200x60. The top band's rect starts at `left=20, top=-20`; its items sit at `top=-48`, below the
label strip; the second band's rect starts at `top=-150`, below the first band's `bottom=-120` plus
the band gap. The `Data Platform` band is empty and keeps a label row 40 tall, so the layer is
visible and unpopulated rather than absent. The whole thing reports a bounding box 484 wide and 300
tall, which is what you compare against the canvas.
