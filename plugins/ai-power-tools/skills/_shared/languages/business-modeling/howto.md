# Modeling a business in Sparx EA (the OMG business modeling extensions)

How Sparx EA represents the language described in the business modeling language skill, measured on EA 17.1 build 1716 (2026-10-21). The language is the **UML Profile for Business Modeling** of the OMG UML 1.3, 1.4 and 1.5 specifications. **It is part of the UML 1.x specifications and has no newer version**: it was dropped from UML 2.0, so there is no later release to follow. EA's own Business Modeling stereotypes are Sparx's, not the OMG's, and they go beyond it. Every fact here was read from what EA creates and lists (`ea.yaml` records the source of each fact). Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own actors, workers and entities. Nothing here assumes you have any particular model.

## 1. What EA gives you

- **No Business Modeling profile of its own.** EA's samples call the technology `EAExtended:BusinessModeling`, a Core Extensions file that cannot be read. Its stereotypes are ten rows of the **EAUML** profile of Core Extensions (Resources > MDG Technologies > System Technologies > Core Extensions > UML Profiles > EAUML): `business actor`, `business use case`, `business use-case realization`, `internal worker`, `business boundary`, `business entity`, `worker`, `case worker`, `business worker`, `business control`.
- **Create them with the qualified type `EAUML::<name>`**, spaces kept (`EAUML::business actor`). EA stores the bare name in the Stereotype field (`business actor`) and the qualified form in a cross-reference record. `EAExtended::`, `Extended::` and `BusinessModeling::` are not stereotype prefixes: they are refused.
- **One diagram type**, created as `Extended::Business Modeling` (stored with the base type Logical and the marker `MDGDgm=Extended::Business Modeling;`).
- **Toolbox and quick links.** Measured on EA 17.1 build 1716, 2026-11-04: EA names the diagram type "Business Modeling Diagram", and its toolbox has one page, "Business Modeling", with ten items (Business Actor, Business Use Case, Business Use Case Realization, Business Boundary, Business Control, Business Entity, Business Worker, Worker, Internal Worker, Case Worker), the same ten as the stereotypes. From a Business Use Case the quick links offer no business-modeling link, only "Requirement" and the common list. One source was tried.

## 2. The EA diagram type for each standard diagram type

The OMG chapter defines **no diagram type**. It describes only how the package and class kinds are labeled. A use case model and an object model are ordinary UML models, drawn here on EA's one diagram type:

| Standard view | EA diagram type | Holds |
|---|---|---|
| Use case model (the business from outside) | `Extended::Business Modeling` | actors, use cases, realizations, plain associations |
| Object model (the business from inside) | `Extended::Business Modeling` | workers, case workers, internal workers, entities, communicate and subscribe |

EA's two business patterns ("Basic Business Use Case Model", "Basic Use Case Realization") draw all four of their diagrams on this type.

## 3. Concepts: what to create

| Language concept | What to create in EA | Stored as | Notes |
|---|---|---|---|
| Actor (plain UML actor) | an Actor, with `EAUML::business actor` or with no stereotype | `business actor`, or none | The OMG profile defines no business actor; it uses the plain actor. Both are valid; the allowed-pairs rule reads either. |
| Use case (plain UML use case) | a UseCase, with `EAUML::business use case` or none | `business use case`, or none | As above. |
| Use case realization | a Collaboration with `EAUML::business use-case realization` | `business use-case realization` | A Realisation connector runs from it to the use case. The OMG name `use case realization` is refused; this is EA's name for it. |
| Worker | an **Object** with `EAUML::worker` | `worker` | EA also lists `business worker`, a separate stereotype that this guide treats as the same kind. |
| Case worker | an Object with `EAUML::case worker` | `case worker` | Draw a Generalization to a worker. |
| Internal worker | an Object with `EAUML::internal worker` | `internal worker` | The OMG name, no business prefix. |
| Entity | an Object with `EAUML::business entity` or `EAUML::entity` | `business entity`, `entity` | Two stereotypes, one OMG kind (section 6). |
| Use case model, use case system, use case package, object model, object system, organization unit, work unit | a Package, with the OMG keyword **typed** as its Stereotype | `useCaseModel`, `useCaseSystem`, `useCasePackage`, `objectModel`, `objectSystem`, `organizationUnit`, `workUnit` | EA has no stereotype for any of them. See section 5. |
| `business boundary`, `business control` | an Object with `EAUML::business boundary` or `EAUML::business control` | as named | **EA extras.** No OMG source. |

None of the stereotypes carries a tagged value. Workers and entities are Objects, not Classes: EA **refuses** these stereotypes on a Class, an Interface, an Artifact and an Actor.

Specialization: a case worker and an internal worker specialize a worker. Draw a Generalization from the case worker (or internal worker) to the worker. EA accepted a Generalization between two Objects with no message.

## 4. Relationships

| Relationship | EA connector | Stereotype | Direction |
|---|---|---|---|
| communicate | Association | the keyword `communicate`, **typed** | from the From element to the To element, as drawn |
| subscribe | Association | the keyword `subscribe`, typed | from the subscriber to the publisher |
| actor takes part in a use case | Association | none | EA stores the direction as Unspecified |
| realization of a use case | Realisation | none | from the realization to the use case |
| specialization | Generalization | none | from the specialization to the generalization |

`communicate` and `subscribe` are association keywords in the OMG profile and **not stereotypes in any EA profile** (the catalog tried both and got nothing stored). EA stores the keyword if you type it as the connector's Stereotype. The pairs they may join are the ones BIZMOD-LNK-001 allows (the language's `relationships_allowed` table); a pair outside it is a warning.

## 5. What EA does that the standard does not

- **Business-prefixed forms of the plain UML elements** (`business actor`, `business use case`) and a business form of the realization collaboration. The standard has only the plain actor and use case.
- **`business boundary` and `business control`**, with `boundary`, `control` and `entity` sitting beside them in the same EAUML list. None is in the OMG business modeling chapter.
- **Workers and entities as Objects.** The standard calls them classes.
- **No stereotype for the package kinds** (use case model, use case system, use case package, object model, object system, organization unit, work unit) **or for communicate and subscribe.** The way to mark them in EA is to type the OMG keyword, in camel case as the profile writes it, into the Stereotype field of the package or the association. EA stores it exactly as typed and keeps no profile behind it, so it is a convention of the guide, not something EA enforces or autocompletes. The ruleset keys on those spellings; a model that does not type them has nothing for the rules about object models, work units and communicate to select.
- **Containment is by package.** A work unit is a package that holds its entities directly; an object model is a package that holds its object system directly.

## 6. Traps found

1. **The prefix.** The technology is Core Extensions (`EAExtended`) but the stereotype prefix is `EAUML`. `EAExtended::business actor` is refused with an error.
2. **Spaces and hyphen.** The names keep their spaces, and the realization name is hyphenated (`business use-case realization`). Matching ignores case (`EAUML::Entity` stores `entity`), but the stored name is always the lower case one; select with that.
3. **Class is refused.** Creating a worker or entity as a Class with the stereotype set leaves it with no stereotype. Create with the qualified type, which makes an Object.
4. **`business entity` and `entity` are different stored strings.** EA does not treat one as the other. A rule or a query that names only `business entity` misses the elements typed `entity`, and the reverse. The same holds for `business control` and `control`, and `business boundary` and `boundary`.
5. **`StereotypeEx` for the keywords stores nothing.** `Connector.StereotypeEx = "EAUML::communicate"` is accepted without a message and leaves the Stereotype empty. Set `Stereotype = "communicate"` (typed text) instead.
6. **Typed `communicate` can bind to TOGAF.** With TOGAF loaded, EA matched the typed `communicate` to TOGAF's `Communicate` in the cross-reference while `t_connector.Stereotype` kept the typed spelling. If a modeler picks `Communicate` from a list, the stored spelling is capitalized and the ruleset does not select it.
7. **Diagram type typos fail silently.** `Extended::` followed by a name EA does not know, `EAExtended::Business Modeling` and every other prefix create a plain Class diagram with no error. Check `MDGDgm=` after creating one.
8. **Use case realization is a Collaboration, not a UseCase.** The Realisation connector goes from the collaboration to the use case.

## 7. What the ruleset checks

Three rules (`rulesets/business-modeling/business-modeling_rules.yaml`): communicate and subscribe join only the pairs BIZMOD-LNK-001 allows (the language's `relationships_allowed` table) (warning); an object model holds an object system (error); a work unit holds an entity (warning).

3 of 3 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

**To get these checks, type the OMG keywords as stereotypes.** EA's business modeling toolbox has no item for these
five kinds, so nothing in EA marks them for you. Type the keyword, exactly as shown, into the Stereotype field:

| What you are modeling | Where | Type this |
|---|---|---|
| An association that is a communicate link | the association's Stereotype | `communicate` |
| An association that is a subscribe link | the association's Stereotype | `subscribe` |
| The package that is an object model | the package's Stereotype | `objectModel` |
| The package at the top of an object model | the package's Stereotype | `objectSystem` |
| A package that is a work unit | the package's Stereotype | `workUnit` |

A model that does not type them is not checked by these three rules, and the validation reports nothing for them, which
looks the same as a model that passes. Type the keywords in lower camel case, as above: a capitalized `Communicate` is
not selected.

**If TOGAF is loaded in the same model:** TOGAF has its own `Communicate` stereotype. EA may match a typed
`communicate` to it in the stereotype cross-reference, and EA's stereotype list offers TOGAF's capitalized
`Communicate`. Type `communicate` yourself rather than picking it from the list, so the stored name stays lower case
and the communicate check selects it (trap 6 in section 6).

Everything else the chapter says is a definition (an entity is passive; a case worker deals with outside actors) or needs a property EA stores where the rule grammar cannot read it. The language skill's other rules have no ruleset rule.
