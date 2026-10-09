# Building the profile tree from a census

Phase 1 of `ea-mdg-model-build` assumes you are duplicating a profile tree that already
exists. This covers the other case: a first version of a technology, generated from the
stereotype usage a repository already contains.

Route here from `ea-mdg-assess` §2a, which is where path B is chosen and recorded.

---

Two cases, and they start differently.

**A later version of a technology that already has one** — duplicate the existing tree. That is
the rest of this phase.

**A first version, generated from what the repository already contains** — there is nothing to
duplicate, so build the tree and populate it from a census. Route here from `ea-mdg-assess` §2a,
which is where path B is chosen and recorded.

1. **Census first, profile-aware.** `_shared/tools/ea_census.py`. Not `summarize_stereotype_usage`:
   it reads `t_object.Stereotype`, a bare name that does not identify the language, so it cannot
   tell a governed element from an ad hoc one carrying the same name. The census gives you
   `(stereotype, metaclass)` pairs, tag names with populated-value coverage, and inferred enum
   domains — which is exactly the content of the profile you are about to create.

2. **Create the four packages** with `ea_model(operation="create_package", ...)`, sequentially —
   EA's package tree is not thread-safe and parallel creates produce intermittent COM errors.

3. **Stereotype the three child packages, and get this right**: the child package's stereotype is
   what routes its content into a section of the built MDG.

   | Child package stereotype | Lands in |
   |---|---|
   | `«profile»` | `<UMLProfiles>` |
   | `«toolbox profile»` | `<UIToolboxes>` |
   | `«diagram profile»` | `<DiagramProfile>` |

   ⚠ **Stereotyping all three `«profile»` piles everything into `<UMLProfiles>`** and the toolbox
   and diagram sections come out empty. Measured. Our own MDG book says EA accepts either and
   repeats the error in its own dev model — it does not.

4. **Name the technology package for the id you want.** The technology id is the package name
   truncated to 12 characters, so `WBA Technology` yields `WBA Technolo`. A census-derived name
   will often be too long.

5. **Create one `«metaclass»` element per distinct metaclass the census observed**, then one
   `«stereotype»` element per `(stereotype, metaclass)` pair, then an **Extension** connector from
   each stereotype to its metaclass. Phase 2 covers the mechanics; the Extension is the part that
   decides whether the stereotype exports at all.

6. **Carry the census's tag names onto the stereotypes as attributes.** Phase 3 covers the
   reference-data half.

**Verify by round-trip, not by inspection.** Build the technology, install it, and re-census the
repository through the new technology. The generated MDG should describe the content it was
derived from. Anything the re-census reports as undeclared is something the generation dropped.

