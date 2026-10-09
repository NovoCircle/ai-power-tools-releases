# Verification — checking a diagram you generated

Generating a diagram is half the job. This file is the other half: what to check, what the check
can and cannot see, and how to stop.

The loop is **compose → place → style → route → verify → lint → correct**, and it is bounded. Three
correction passes, then you report what is left. A loop that runs until it is satisfied either
terminates or lies about having finished.

---

## 1. The stale-render trap — read this before anything else

**EA caches a diagram's render.** If the underlying rows changed since EA last drew it — a direct
SQL write, a placement made from a different process or a different session — asking for the image
can return the previous one. It looks plausible. It is not the diagram you just built.

A check that skips the reload **certifies a diagram it never saw.**

`verify_diagram` reloads unconditionally and has no flag to skip it, deliberately: the one thing a
verification step must not offer is a faster mode that invalidates the verification. Use it rather
than `get_diagram_png` or `get_diagram_svg` when the point is to *check* something.

Those two are the right calls when you already trust the state and just want the picture, and both
take `refresh=True` when you do not.

---

## 2. What verification actually reads

`verify_diagram(diagram_id=..., include_svg=True)` returns the placed geometry EA holds after the
reload: per-object rects, sizes and z-order; per-link routing, color, width and label state; the
canvas extents; and, on request, the rendered SVG.

Two properties of that payload matter more than the field list:

**It is EA's own rendering.** `get_diagram_svg` and `get_diagram_png` both call EA's
`Project.PutDiagramImageToFile`. The SVG is not a reimplementation of EA's drawing — it *is* EA
drawing. That is why the SVG is authoritative for color and for paint order.

**A color readback proves nothing; a render does.** EA stores whatever integer you wrote and hands
it back on request, whether or not it draws with it. Some shapes refuse a fill outright — the write
succeeds, the property reads back correctly, and EA paints the element in its own colors, because
the shape script owns the fill. `set color → read color` asserts your own input and passes against
an implementation that stores it and never draws it.

So: **check color by looking at the render.** In the SVG, `fill="#RRGGBB"` and `stroke="#RRGGBB"`
are readable with a regex. No image decoding required.

---

## 3. The linter

`tools/lint.py`. It consumes a `verify_diagram` result and nothing else — no repository calls of its
own — so it runs anywhere you can carry the payload.

```python
import lint

report = lint.lint_diagram(verified, profile=..., roles=..., rows=..., columns=...,
                           stacks=..., rings=..., expected_route=...)
if not report.clean:
    for finding in report.errors:
        print(finding.rule, finding.subjects, "->", finding.correction)
```

### It is language-neutral by construction

Every rule reads geometry and presentation. Nothing reads the metamodel, and no notation name
appears anywhere in the module — a test enforces that over identifiers *and* string constants,
including docstrings. One linter therefore serves every modeling language, including one nobody has
written a binding for, because "these boxes overlap" is not a metamodel question.

The consequence you have to live with: **the linter cannot know what two elements have in common.**
That is why `roles`, `rows`, `columns`, `stacks` and `rings` are yours to supply.

### The groupings are yours to supply, and omitting them is not free

- `roles` maps a role name to the objects playing it. Uniform sizing is checked *within* a role,
  never across roles — two elements can share a container and legitimately differ in size.
- `rows` is a list of rows, each a list of objects. Spacing is checked per row, along **x**.
- `columns` is the same thing turned ninety degrees: a list of columns, each a list of objects,
  spacing checked along **y**. It is a separate argument rather than an axis on `rows` precisely so
  that a caller who already passes `rows` does not have to restructure to declare a column — pass
  both and both are judged, by the same rule, under the same id. Until `columns` existed the y axis
  had no rule at all: a column passed as a row has every x gap equal to the same negative number,
  so the spread was zero and uneven vertical spacing reported clean. The server's own distribute
  operation shipped with exactly that defect, and it now does both axes because they are orthogonal.
- `stacks` is a list of `(axis, containers)` pairs. `axis` is `"vertical"` (read top to bottom, so
  the containers should share a **width** and a **left edge**) or `"horizontal"` (read left to
  right, so they should share a **height** and a **top edge**). You state the axis as well as the
  members: coordinates cannot tell a tall narrow vertical stack from a horizontal one. Rules
  `ragged-stack` and `staggered-stack`.
- `rings` is a list of `(hub, items)` pairs, or of `(hub, items, sweep)` triples with the sweep in
  degrees. A radial tree is several rings, one per hub, and is passed as several. Rule
  `uneven-spokes` from the pair; `uneven-ring-angles` needs the sweep as well, and see below for
  why it cannot be inferred.

Omit them and those rules **do not run**. They do not guess. Guessing which elements share a role
from their coordinates would invent the metamodel the module refuses to have, and it would do it
silently, which is worse than not checking.

A stack or ring you do not declare is not judged, and a diagram that merely *looks* stacked or
ringed gets no finding.

A wrapped row is **two rows**. Pass it as two. The rule will not compensate, because compensating
would blind it to the single mis-spaced element it exists to catch.

### How to tell "did not run" from "ran and found nothing"

Two signals, and you need both, because a clean report that never asked the question is the failure
mode this whole file exists to prevent.

**An absent metric key.** A rule that never got its grouping records nothing:
`worst_stack_extent_spread`, `worst_stack_alignment_spread`, `worst_spoke_spread` and
`worst_ring_angle_spread` are simply not in `report.metrics`.

**`report.not_run`.** This is for a grouping you **did** declare and the rule could not judge — an
axis outside `STACK_AXES`, a ring with no sweep, or groups that are all too small to compare
anything within (a role of one, a row of two, a stack of one). Each of those looks exactly like a
clean result in the findings, so each rule says it out loud.

A grouping you did **not** supply says nothing on `not_run`, deliberately: an entry per unused
grouping would put four lines on every ordinary diagram, and a list that is noisy on correct output
is a list nobody reads — after which it cannot do its one job. An **empty** group is treated the
same way and is not a declaration at all, which is what keeps a banded diagram drawn with
`draw_band_labels=False` quiet: it has no container elements, its caller still hands over a stack,
and that is deliberate, documented behavior rather than something to complain about.

**Three rules record a count with no meaning on its own,** and each now carries a denominator beside
it, the way `crossings` carries `crossings_measured_over`:

| rule | the ambiguous count | the denominator that makes it readable |
|---|---|---|
| `uniform-sizing` | `roles_with_inconsistent_sizing` | `roles_measured` — roles holding two or more elements |
| `pitch` | `worst_pitch_spread` | `pitch_groups_measured` — rows *and* columns holding three or more, summed |
| `missing-title` | nothing at all | `title_convention_stated` — false when no drawn-title convention was stated, so the rule never ran |

All five of those metric keys are always present. `roles_with_inconsistent_sizing: 0` is the same zero whether you
passed clean roles or passed none, and a vacuous zero has already been quoted as a result here.

### Severity

One rule is deliberately narrower than its name suggests. `missing-connector-labels` fires only on
**inconsistent** labeling — some connectors named and others not. Uniformly unlabeled connectors are
a convention in several notations, not an error, and a rule that reported every one of them would
report correct diagrams as broken.

- **error** — the diagram is wrong. Overlapping elements, a row or column with no whitespace,
  elements in one role at different sizes. `report.clean` is false.
- **warning** — look at it. Often correct in context: out-of-canvas placement, an unset route, an
  unexplained set of fills, a ragged stack, a staggered stack, uneven spokes, a bunched ring. Does
  not block.
- **info** — a measurement, not a judgment.

`report.clean` means **no errors**, not "no findings". A bar nobody can clear is a bar nobody uses,
and a linter that rejects every legitimate view gets switched off — after which it protects nothing.

### Four rules about shape rather than about elements

Every rule above is per-element or per-pair. These four are about a *group's* geometry, and each
exists because a diagram passed everything else and looked wrong.

- **`ragged-stack`** (warning). A band sized to its own contents is narrower when it holds fewer
  items, so bands of three, three and two leave a ragged edge. Only the cross-axis extent is
  compared, against `SIZE_TOLERANCE`. Bands of different *heights* in a vertical stack are normal
  and are not reported. A deliberately tapering stack is a legitimate composition: do not declare it
  a stack.
- **`staggered-stack`** (warning). The other half of the same picture, and for a while the recorded
  blind spot: containers of *identical* size at different offsets, so the edge the eye follows down
  the stack zigzags. The leading edge is the left edge of a vertical stack and the top edge of a
  horizontal one, judged against `SIZE_TOLERANCE` — alignment is the strictest claim here, boxes
  either line up or they do not, so it takes the tightest tolerance already in the file. Reported
  separately from `ragged-stack` because the two have different corrections: one says resize, the
  other says align.
- **`uneven-spokes`** (warning). Centering each item on a circle does not put its *edge* on it. A
  wide flat item reaches toward the hub by half its height at the top and bottom and by half its
  width at the sides, so it stands off from the hub at the top and bottom and crowds it at the
  sides. The rule measures the spoke as drawn — center to center, less the stretch inside the hub
  and inside the item — and flags a spread above `PITCH_TOLERANCE`. Place items by their near edge
  and it is clean.
- **`uneven-ring-angles`** (warning). A ring squeezed into a third of its circumference, with every
  spoke the same length and nothing overlapping. What gives it away is the step from the last item
  back to the first: the items' own steps can be perfectly even at 100 degrees apiece while the way
  back is 160. The spread of the steps is judged against `ANGLE_TOLERANCE`.

  **This rule needs the ring's `sweep` and does not run without it.** Three items bunched into 200
  degrees and three items fanned evenly across 200 degrees *are the same geometry*; the only
  difference is how far round the ring was meant to go, and only you know that. A rule that assumed
  a full circle would report every deliberate fan, and a fan is what a partial sweep is for. Pass
  `(hub, items, sweep)` and it is judged; pass `(hub, items)` and it lands on `not_run`. Only
  whether the ring closes is read off the number — 360 or more closes it — because the spread of the
  observed steps is what is judged, so the linter holds no copy of the engine's angular arithmetic
  to drift away from.

All four are warnings because an uneven stack or ring is a defect of appearance and never of
correctness. Three of them reuse an existing tolerance rather than a new one: no real stack or ring
has been measured to calibrate a separate number, and the claim — "these are the same size" and
"these are evenly spaced" — is the one the existing constants already make.

`ANGLE_TOLERANCE = 4` is the one new constant, and it is in **degrees**, which is why it could not
reuse `PITCH_TOLERANCE` in layout units. It is calibrated, not picked. Over 6300 ring layouts the
composition engine actually produces — counts 2 to 15, eight sweeps, four start angles, three radii,
five item shapes — the worst spread of the angular steps is **0.78°**, which is the cost of placing a
center on whole units. A `SIZE_TOLERANCE`-sized nudge of 4 units, at the tightest center-to-center
distance any of those layouts produces (132 units), is **1.74°**, so two neighbors nudged opposite
ways move one step by **3.47°**. The smallest measured defect is a spread of 60°. So the boundary
sits anywhere in (3.5, 60) and 4 is taken from the noise end deliberately: a floor's job is to stay
quiet on correct output.

### A row or column with no whitespace, and why deliberate abutment is safe

`pitch` judges the **spread** of the spacing, and the spread is blind to a row that has no spacing at
all: eight equal boxes butted edge to edge have eight gaps of zero, and the spread of eight zeros is
zero. `check_no_overlaps` does not catch it either — touching is exempt there **by design**, because
a band and its contents legitimately share an edge. So a row with no whitespace anywhere in it used
to score completely clean. That is the third time the touching exemption has hidden a spacing defect
here, so the rule now carries a **floor on the gap itself**, an error, on both axes and whether or
not the elements are uniformly sized.

**Bands, lanes and pools abut on purpose, and this does not report them.** What keeps the floor off
them is the *declaration*, not the geometry and not the element type:

- A group you pass as a **row** or a **column** is a statement that its members are laid out with
  spacing between them, so zero spacing in one is a defect.
- Containers that abut deliberately reach the linter as a **`stacks`** grouping instead, and **no
  rule here measures the gaps between a stack's members.**

The same two boxes are therefore a defect as a row and correct as a stack, and only you know which
they are. One consequence worth knowing: a column you pass as a `rows` group now comes back as "no
whitespace" rather than as clean, because its members' x extents sit on top of each other. That is
the mis-declaration being reported rather than a new defect — pass it as `columns` and you get the
uneven-spacing finding you were after.

---

## 3a. The drawn box is not always the stored rect

Measured on EA 17.1, and it changes how much the geometry rules can be trusted:

**EA grows the rendered element to fit a name it cannot break.** It wraps on spaces only, so a name
with spaces wraps to fit. A name without them is never broken at any length — instead the drawn box
gets wider. A 30-character unbreakable name in a 100-wide element renders **128px** wide; a
49-character one renders **188px**. EA does not truncate, does not add an ellipsis, and does not
shrink the font.

`verify_diagram` keeps reporting the stored width of 100 throughout.

So a diagram can draw an element half again as wide as its geometry says, and **every rule that
reads the stored rects — overlap, pitch, canvas, uniform sizing — is blind to it.** Two elements
with a comfortable gap in the geometry can sit on top of each other on the canvas.

`render-exceeds-rect` is the rule for this, and it is an **error**: the diagram does not match its
own geometry, so nothing downstream can be trusted about it. It is measured by comparing the SVG's
own `<rect>` against the element's stored width, which is why it needs `include_svg=True`.

The related rule, `label-cramped`, catches the subtler case: a name that DOES fit, with less than
`LABEL_MARGIN` px to spare, so it reads as touching the border. That is what the first generated
capability map did, on a diagram that scored clean on every other metric.

`label-clipped` is kept for shapes that genuinely clip rather than grow. On ordinary elements it
will not fire, and that is the correct behavior rather than a gap.

### These rules refuse to guess, and that costs coverage on purpose

They only judge a box whose text is **exactly one known element's name**, and whose width could
plausibly be that element's outline. Both guards exist because of what happened without them:

- EA draws MDG-stereotyped elements with a **shape script**, which emits paths rather than a
  `<rect>`. On such a diagram the only rects are the drawn containers, so every element's text fell
  to the band enclosing it and the "label" became five element names and two connector labels run
  together — then reported as a spectacular overflow of a box it never belonged to.
- A shape script also emits several rects per element, and judging a name against an icon box
  reported a 37px overflow against a rectangle the name was never drawn inside.

So on a shape-scripted notation these rules mostly stay silent, and `labels_unmatched` on the report
says how much went unjudged. A quality warning that fires wrongly across a whole notation is how a
linter gets switched off, and a missed cramped label costs far less than that.

#### Then measured against live EA, which moved two of these from belief to fact

A bound MDG's shape-scripted elements were rendered by EA 17.1 for the first time: six elements on
one view — three shape-scripted, two plain `Class`, and a named container — with one shape-scripted
element and one plain element deliberately given the **same** 46-character unbreakable name.

**`labels_measured` counts BOXES, not elements, and `not_run` stayed silent.** The three
shape-scripted elements emitted no `<rect>` at all, so none of them was label-checked; the report
still read `labels_measured: 4` and `not_run: []`, because the container and the two plain elements
supplied boxes of their own. The `not_run` line for this case only appears when *nothing* was
measured, so a mixed diagram — one plain element beside a notation the rule cannot see — reports a
positive count and says nothing about the half it skipped. **Read `labels_measured` as "boxes
judged", never as "elements checked", and compare it against the element count yourself.** The claim
elsewhere in this file that a shape-scripted notation reports itself on `not_run` holds only when
every element on the view is shape-scripted.

**A name two elements share used to name the wrong element.** In the same run the plain `Class` grew
its drawn box from 100px to 216px — a real `render-exceeds-rect` error — and the error was raised
against the *shape-scripted* element, which had emitted no box and could not have overflowed.
Renaming one of the two moved the finding onto the right element, which is how the shared name was
established as the cause: the name-to-element index kept the first element carrying a name and
dropped the rest, and "first placed" is not a tie-break, it is a coin toss. A duplicated name is now
counted as **unmatched**, restoring what this rule's contract already said — *exactly one* known
element's name. The residual cost is stated rather than hidden: **an element that shares its name
with another on the same view is not label-checked.**

Neither of these was reachable hermetically. The first needs EA's own renderer to decline to emit a
rect; the second needs EA to grow a box.

---

## 4. Profiles: why suppression is correctness, not convenience

A presentation profile says how much detail a view shows. An executive view that deliberately hides
connector labels must not then be told its connector labels are missing.

Pass the profile as a plain mapping. From a binding's profile:

```python
p = binding.profile("executive")
profile = {**p.display_settings(), "collapses_parallel": p.collapses_parallel}
report = lint.lint_diagram(verified, profile=profile)
```

`lint.PROFILE_KEYS` lists what is understood; anything else in the mapping is ignored rather than
rejected, so a profile vocabulary can grow without breaking the linter. `lint.SUPPRESSED_BY` is the
whole of profile-awareness — one table, readable and testable, rather than a branch inside a rule.

**A profile can never suppress a structural defect.** Overlapping elements are wrong under every
profile. Presentation settings switch off rules about *what is shown*, never rules about *where
things are*. There is a test per profile key asserting exactly that.

Suppressed rule ids come back on `report.suppressed`. A suppression must be visible, or a clean
report overstates what was checked.

---

## 5. The correction loop, and how to stop

```python
previous = None
for attempt in range(lint.MAX_CORRECTION_PASSES):
    verified = verify_diagram(diagram_id=..., include_svg=True)
    report = lint.lint_diagram(verified, profile=profile, roles=roles, rows=rows,
                               columns=columns, stacks=stacks, rings=rings)
    if report.clean:
        break
    if lint.is_stalled(previous, report):
        break          # this pass changed nothing; another will not help
    apply_corrections(report.errors)
    previous = report
```

Two stopping conditions, because there are two ways to fail:

- **The budget runs out.** Say so. "Three passes, these four errors remain" is a useful report;
  "done" is not.
- **A pass changes nothing.** `is_stalled` compares report signatures, ignoring message wording so
  that a coordinate in a message does not look like a new finding. Stop at the first stall rather
  than burning the remaining budget on passes that each fix nothing.

Either way, **report honestly what is left.** The loop's value comes from being trusted, and one
"done" over a diagram with four overlaps costs more trust than twenty honest partial reports.

---

## 6. What the linter cannot see

Kept here on purpose. A clean report means *no defect this linter knows how to measure* — it is not
a claim that the diagram reads well, and the list of what it misses is the difference between those
two statements.

### The inventory is the denominator

The list below is written by hand. The **defect-class inventory** is its derived counterpart, and
it is what a clean score needs in order to mean anything. It lives with the server's benchmark
suite, in the `ea-mcp-server` repository, as `tests/benchmark/defect_corpus.py`, and prints itself:

```
PYTHONPATH=. python -m tests.benchmark.defect_corpus
```

Each entry is one defect class, the perturbation that produces it from a **real captured
`verify_diagram` payload**, the rule that should fire, and whether it actually does. Its companion
test reads the rule ids from the linter's own registry, so a rule added here with no corpus entry
turns that suite red rather than quietly widening the gap between what the linter checks and what
the inventory claims.

**As of 2026-09-30 it records 22 defect classes: 21 detected, across 18 rules, and one that is
perturbed, linted, and provably fires nothing** (a name colliding with the stereotype icon drawn
inside its own box — see the known limit at the end of this section). So **a clean score is not
proof of a good diagram**: it excludes those 21, says nothing about that one, and says nothing at
all about the eight classes listed below, which no rule reaches. The report also names the six
causes a rule puts on `not_run`, and the five shapes the captured payloads do not contain, each of
which bounds what the corpus can claim without a fresh capture.

Read it before quoting a score to anybody. And it decays: it is a claim about this linter as of a
date, so re-run it rather than repeating the figures above.

- **Whether the grammar was the right choice.** A capability model laid out as swimlanes will lint
  clean. It is still the wrong diagram.
- **Whether the content belongs on one diagram at all.** Forty elements can be spaced perfectly.
- **Whether a name means anything.** "Component 7" and "Payment Authorization" are the same to every
  rule here.
- **Whether a container's grouping is honest.** A group called "Other" holding a third of the
  content lints clean and is a confession.
- **Whether the declared grouping is the real one.** The stack and ring rules judge the stacks and
  rings you pass, and cannot tell that you left one out or put a box in the wrong ring. A ring with
  no `sweep` is not judged for its angles at all, and says so on `not_run`.
- **How much of its sweep a ring should fill.** `uneven-ring-angles` judges evenness only. A fan
  occupying a quarter of the sweep it declared, evenly, is clean — how wide a fan should open is a
  composition choice, not a defect.
- **Whether the layout matches the reader's mental order.** Foundations at the top is a choice the
  linter cannot second-guess.
- **A collision caused by a grown box, unless the render was supplied.** Without `include_svg=True`
  the geometry rules read stored rects and cannot know the drawing is wider — see §3a. The report
  lists this on `not_run` rather than staying quiet about it.
- **Two connectors drawn on top of each other.** Measured live on EA 17.1: two `OrthogonalSquare`
  connectors between the corners of a square shared a collinear horizontal segment, which reads worse
  than a crossing and is not one. `crossings` counted the center-to-center approximation instead and
  reported **1** where the drawn paths proper-cross **0** times. The count is honest about being
  approximate and is still the right metric for comparing two versions of one diagram, but under
  orthogonal routing it is neither an upper nor a lower bound on what the reader sees, and no rule
  sees the overlap at all.
- **Color set as the element's DEFAULT appearance rather than on the placement.** `unexplained-color`
  counts `distinct_fills`, and `fill` is decoded from the placement's own style string only. Measured
  live on EA 17.1: the same three colors reported `distinct_fills: 3` when set per placement and
  `distinct_fills: 0` when set as the element default — while EA drew all three either way, and the
  render carried `fill:#FF0000`, `fill:#00FF00` and `fill:#0000FF` in both cases. So a diagram
  colored the way EA's own *Default Appearance* dialog colors one is **invisible** to this rule, and
  its zero is the vacuous kind. This is the likeliest reason a generated view reports no fills at all
  when it plainly has some: check the render, or set the color on the placement.

When a rule *can* be built for something on this list, it should be. Until then, the honest report
is "clean, and here is what clean does not cover" — which is why this section exists in a file the
skill points at rather than in a comment nobody reads.

### A known limit, not a gap to close: a name colliding with a stereotype icon

An element's name running into the icon drawn inside its own box, so the two overprint. There is no
rule for it, and unlike the items above **this one is not reachable by adding one.** The mechanism,
because a limit without its mechanism gets rediscovered as a bug:

1. **`stereotype` is inert input.** No rule reads the field. It arrives in the payload and nothing
   branches on it — which is the language-neutrality property working as intended, not an oversight.
2. **The icon is not in the geometry.** It is drawn by a shape script, and an element drawn by a
   shape script emits **paths rather than a `<rect>`**. There is nothing in either the stored rects
   or the SVG rects to measure the name against.
3. **The one rule that reads the render refuses to judge those diagrams.** On a shape-scripted
   notation the only `<rect>`s are the drawn containers, so no box's text is exactly one element's
   name and `labels_unmatched` rises. `check_labels_fit` reports itself on `not_run` only when
   **nothing** on the view was measured — measured live, a container plus two plain elements is
   enough to keep that line away while every shape-scripted element goes unjudged. See §3a. When a shape
   script *does* emit small rects — an icon box, a compartment divider — they are under `_MIN_BOX`
   (20px) and discarded as decoration, which is exactly the size an icon is.

Closing it needs a live EA and attribution of a shape script's output, and the linter's standing rule
is to **refuse to judge what it cannot attribute**: three classes of false positive got through 63
green hermetic tests by guessing, and were caught only by live diagrams. A quality warning that fires
wrongly across a whole notation is how a linter gets switched off, and a missed icon collision costs
far less than that.

So: **render it and look.** That is the check for this one, and there is no substitute.

---

## 7. Look at it

The rules above were all added because something shipped that they would have caught. Several were
added because a diagram **scored clean and looked wrong** — ragged container widths, a name running
into its own icon, a band stopping short of its neighbors.

Render it and look. `verify_diagram(include_image=True)` returns the picture. The linter is the
floor, not the ceiling.
