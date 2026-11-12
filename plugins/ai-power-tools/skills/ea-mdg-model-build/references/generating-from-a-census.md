# Building the profile tree from a census

Phase 1 of `ea-mdg-model-build` assumes you are duplicating a profile tree that already
exists. This covers the other case: a first version of a technology, generated from the
stereotype usage a repository already contains.

Route here from `ea-mdg-assess` §2a, which is where path B is chosen and recorded.

---

There is nothing to duplicate on a first version, so build the tree and populate it from a census,
in the steps below. (A later version of a technology that already has a tree is duplicated instead;
that is Phase 1 of `ea-mdg-model-build`.)

1. **Census first, profile-aware.** Run `_shared/tools/ea_census.py` over the rows listed in
   `ea-mdg-assess` §2a, read once each, not over SQL calls you write per stereotype. It resolves
   which technology each stereotype is bound to and gives you `(stereotype, metaclass)` pairs, tag
   names with populated-value coverage, and inferred enum domains, which is exactly the content of the
   profile you are about to create. `summarize_stereotype_usage` is profile-aware from server 3.6.0
   (`resolved_items`, `split_stereotypes`) and suits a quick count, but it returns stereotype counts
   only, so it cannot stand in for this census; before 3.6.0 it reads the bare
   `t_object.Stereotype` name, which does not identify the language.

2. **Create the four packages** with `ea_model(operation="create_package", ...)`, sequentially —
   EA's package tree is not thread-safe and parallel creates produce intermittent COM errors.

3. **Stereotype the child packages (one `«profile»`, one `«diagram profile»`, one `«toolbox profile»` per toolbox), and get this right**: the child package's stereotype is
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

