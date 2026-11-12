# Modeling the Business Motivation Model (BMM) 1.3 in Sparx EA

How Sparx EA's built-in Business Motivation Model technology represents the language described in the BMM language skill, measured on EA 17.1 build 1716 (2026-10-20). The technology is a system technology whose definition is encrypted, so every fact here was read from what EA creates and lists, not from the definition file; `ea.yaml` records the source of each fact. Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own enterprise. Nothing here assumes you have any particular model.

**Version.** This guide describes BMM 1.3 (OMG formal/15-05-19, April 2015). OMG's page for the standard lists 1.3 as the latest version (1.2, 1.1 and 1.0 are earlier), so no newer version exists. Which version EA's technology follows was not measured.

## 1. What EA gives you

- **Technology:** Business Motivation Model (technology id `BMM`, profile `BMM`), under Resources > MDG Technologies > System Technologies.
- **One diagram type:** `BMM::BMM Diagram`. The standard defines no diagram types, so there is nothing to map: every view of a motivation model is this one canvas. Opening it switches the Toolbox to the BMM pages.
- **Seven toolbox pages:** BMM - Ends, BMM - Means, BMM - Influencers, BMM - Assessments, BMM - Categories, BMM - Asset and Liability, BMM - Relationships. The element pages hold the same concepts as section 2 under their display names; the Relationships page lists the connector stereotypes by display name (Acts As, Affects Achievement Of, and so on).
- **Model templates:** a BMM Categories template (the Annex G category instances: the four SWOT assessment categories, the general influencer categories, four desired result categories) and two worked BMM examples.
- **Sixty-six stereotypes:** 29 for elements and 37 for connectors. Every one is a concept or a relationship of the standard; EA adds none of its own.

## 2. Concepts: what to create

Create an element with the stereotype in the second column. Stored names are the bare names (`Goal`), not `BMM::Goal`; the qualified form exists in the stereotype cross-reference and is what you pass when creating by script (`BMM::Goal`).

| Standard concept | EA stereotype | EA metaclass | Tagged values |
|---|---|---|---|
| Vision | `Vision` | Requirement | none |
| End | `End` | Requirement | none |
| Desired Result | `DesiredResult` | Requirement | none |
| Goal | `Goal` | Requirement | none |
| Objective | `Objective` | Requirement | none |
| Desired Result Category | `DesiredResultCategory` | Class | none |
| Means | `Means` | Requirement | none |
| Mission | `Mission` | Requirement | none |
| Course of Action | `CourseOfAction` | Requirement | none |
| Strategy | `Strategy` | Requirement | none |
| Tactic | `Tactic` | Requirement | none |
| Directive | `Directive` | Requirement | none |
| Business Policy | `BusinessPolicy` | Requirement | none |
| Business Rule | `BusinessRule` | Requirement | `EnforcementLevel` (free text) |
| Influencer | `Influencer` | Requirement | none |
| Internal Influencer | none | none | Use an Influencer placed in an InfluencerCategory instance named Internal (Annex G.3 allows either mechanism). |
| External Influencer | none | none | Use an Influencer placed in an InfluencerCategory instance named External (Annex G.3 allows either mechanism). |
| Regulation | `Regulation` | Requirement | none |
| Influencer Category | `InfluencerCategory` | Class | none |
| Influencing Organization | `InfluencingOrganization` | Requirement | none |
| Organization Category | `OrganizationCategory` | Class | none |
| Assessment | `Assessment` | Requirement | none |
| Assessment Category | `AssessmentCategory` | Class | none |
| Potential Impact | `PotentialImpact` | Requirement | none |
| Risk | none | none | Use PotentialImpact; EA does not separate a risk from a reward. |
| Potential Reward | none | none | Use PotentialImpact; EA does not separate a risk from a reward. |
| Organization Unit | `OrganizationUnit` | Requirement | none |
| Business Process | `BusinessProcess` | Requirement | none |
| Asset | `Asset` | Artifact | none |
| Fixed Asset | `FixedAsset` | Artifact | none |
| Resource | `Resource` | Artifact | none |
| Offering | `Offering` | Artifact | none |
| Liability | `Liability` | Artifact | none |

Reading the table:

- **Four standard concepts have no stereotype:** Internal Influencer, External Influencer, Risk and Potential Reward. EA refused `BMM::InternalInfluencer`, `BMM::ExternalInfluencer`, `BMM::Risk` and `BMM::PotentialReward` as an unknown type. Class an influencer as internal or external with an Influencer Category instance named Internal or External (the standard's Annex G allows this and EA's BMM Categories template creates both), and model a risk or a reward as a Potential Impact whose name or description says which.
- **Metaclass splits three ways:** the four category stereotypes are `Class`; Asset, Fixed Asset, Liability, Offering and Resource are `Artifact`; everything else is `Requirement`.
- **The one tagged value is `EnforcementLevel`, on Business Rule only.** It is free text with no list of values and no default. See section 5.

## 3. Relationships: what to connect

Every BMM connector is a UML Dependency drawn from source to target, stereotyped with the name below, and carries no tagged values. Read each as a sentence from source to target ("Goal Amplifies Vision"). The pairs are the standard's relationships as the language file lists them, applied to each concept's specializations (a relationship on Directive applies to Business Policy and Business Rule). Whether EA's own quick linker offers the same pairs was read for three pairs only.

| EA connector stereotype | Source to target pairs the standard defines |
|---|---|
| `ActsAs` | Organization Unit to Influencing Organization; Directive to Regulation |
| `AffectsAchievementOf` | Assessment to End |
| `AffectsEmploymentOf` | Assessment to Means |
| `Amplifies` | Goal to Vision |
| `Categorizes` | Assessment Category to Assessment; Assessment Category to Assessment Category; Influencer Category to Influencer; Influencer Category to Influencer Category; Organization Category to Influencing Organization; Organization Category to Organization Category; Desired Result Category to Desired Result |
| `ChannelsEffortsTowards` | Course of Action to Desired Result |
| `Claims` | Liability to Resource |
| `Defines` | Organization Unit to End; Course of Action to Offering |
| `Delivers` | Business Process to Offering |
| `Deploys` | Course of Action to Asset |
| `Determines` | Strategy to Organization Unit |
| `Discharges` | Course of Action to Liability |
| `EffectsEnforcementLevelOf` | Tactic to Business Rule |
| `Enables` | Course of Action to Course of Action |
| `Establishes` | Organization Unit to Means |
| `Governs` | Directive to Course of Action; Business Policy to Business Process |
| `GovernsUseOf` | Directive to Asset |
| `Guides` | Business Rule to Business Process |
| `Identifies` | Assessment to Potential Impact |
| `Implements` | Tactic to Strategy |
| `Includes` | Course of Action to Course of Action; Desired Result to Desired Result; Desired Result Category to Desired Result Category; Business Policy to Business Policy |
| `IsAComponentOfThePlanFor` | Strategy to Mission |
| `IsFormulatedBasedOn` | Course of Action to Directive |
| `IsJudgmentOf` | Assessment to Influencer |
| `IsResponsibleFor` | Organization Unit to Business Process; Organization Unit to Asset; Organization Unit to Liability |
| `IsSourceOf` | Influencing Organization to Influencer |
| `Makes` | Organization Unit to Assessment |
| `MakesOperative` | Mission to Vision |
| `Manages` | Business Process to Asset |
| `Provides` | Fixed Asset to Resource |
| `ProvidesImpetusFor` | Assessment to Directive; Potential Impact to Directive |
| `Quantifies` | Objective to Goal |
| `Realizes` | Business Process to Course of Action |
| `Recognizes` | Organization Unit to Influencer |
| `Requires` | Offering to Resource |
| `SupportsAchievementOf` | Directive to Desired Result |
| `Uses` | Assessment to Assessment; Offering to Fixed Asset |

Reading the table:

- **The 37 names match the standard.** EA's connector names are the verb phrases of the standard's relationship names (Amplifies, Quantifies, Channels Efforts Towards, and so on). Several names carry more than one fact type: Categorizes (seven), Includes (four), Governs, Defines, Uses, Acts As, Is Responsible For and Provides Impetus For (two or three each), so the pair decides which fact it is.
- **One relationship has no connector.** "Business Policy is the basis for Business Rule" (the standard's relationship 38) has no stereotype of that name in EA's list. How Sparx expects that link to be drawn was not harvested; do not guess a stereotype for it. EA's own sample models do not draw it.
- **Direction follows the standard's active reading.** EA's three BMM sample models use it for the eight connector stereotypes they contain (Goal to Vision for Amplifies, Tactic to Strategy for Implements, Objective to Goal for Quantifies, and so on). It is assumed, not measured, for the other 29.

## 4. Which diagram

The standard has no diagram types, so the choice is not between types but between contents. Use `BMM::BMM Diagram` for every view. A view that follows the model's own chain (an Influencer, the Assessment that judges it, the Potential Impact, the Directive it motivates, the Course of Action that directive governs, the Desired Result it channels effort toward) is easy to read, but this is a suggestion: EA's technology states no layout or grouping convention and none was harvested.

## 5. What EA does that the standard does not

- **Enforcement level has a home in EA.** The standard names six enforcement levels (strictly enforced, deferred enforcement, pre-authorized override, post-justified override, override with explanation, guideline) but gives them no attribute. EA gives Business Rule a free-text `EnforcementLevel` tag. EA does not check the text against the six names. The standard says a Tactic sets the level: connect the Tactic to the rule with `EffectsEnforcementLevelOf`.
- **Categories are Class elements.** The standard's category concepts are plain classes in EA, which is also where the Annex G instances (Strength, Weakness, Opportunity, Threat; Competitor, Customer, and the rest) live.
- **Placeholders are real stereotypes.** The standard marks Organization Unit, Business Process, Asset, Fixed Asset, Resource, Offering and Liability as defined elsewhere; EA gives each its own stereotype (Asset and its kin on `Artifact`), so a BMM model can hold stand-ins for items maintained in other models.
- **The toolbox groups concepts its own way.** Organization Unit, Regulation and Business Process sit on the BMM - Influencers page, although the standard treats Organization Unit and Business Process as placeholders defined elsewhere and does not call a Business Process an influencer.

## 6. What the standard has that EA does not

- No stereotype for Internal Influencer, External Influencer, Risk or Potential Reward (section 2), nor for the standard's superclass Motivation Element (EA refused that type too).
- No connector for relationship 38 (section 3).
- No check, when you build by script, of which pairs a connector may join, of a cardinality (a Goal that amplifies two Visions), or of like-kind inclusion (a Goal that includes an Objective). Section 7 gives the evidence. Acyclic hierarchies were not tested.

## 7. Traps found

1. **EA does not stop a wrong pair.** The probe created all 37 connector stereotypes between the same Goal and Vision through the API; EA accepted every one. In the UI the quick linker offers only a subset of stereotypes for a pair, but nothing validates the result afterward. The ruleset exists for this.
2. **The quick linker is looser than the standard in one place found.** Between an Objective and a Goal it offers Includes (and its reverse reading) as well as Quantifies. The standard allows a Desired Result to include only Desired Results of its own kind and joins a Goal and an Objective only by Quantifies (rule BMM-HIER-001). A model built from the quick linker alone can break that rule.
3. **Stored names are shared with another technology.** `BusinessProcess` and `Resource` are also stored stereotype names in EA's BPMN 2.0 technology. A validation rule that selects by stored name alone cannot tell them apart; only the cross-reference (`FQName`) does. A rule that also names the EA type (`types`, since the engine of 2026-10-21) can here, because BMM stores them as a Requirement and an Artifact and BPMN 2.0 as an Activity and a Class; the BMM ruleset does not do so yet. Keep BMM and BPMN content in separate packages if you validate by stored name alone.
4. **Creating by script needs the qualified type.** Create with `BMM::Goal`, which binds the technology's stereotype. A qualified name EA does not know is refused with `Invalid type` (measured for the four concepts in section 2 that have no stereotype, and for Motivation Element). What an unqualified name does was not measured.
5. **The `EnforcementLevel` tag is created with the element, but late.** Adding the tag by name straight after creating a Business Rule left two rows (one empty, one with your text); setting the existing tag on the element after its first update left one. The ruleset reads the first row, so read the element's tags before writing them.
6. **Display properties differ by stereotype.** Twenty stereotypes hide the metaclass icon and 26 hide UML links; Fixed Asset, Offering and Resource do neither. This affects how elements draw, not what they mean.
7. **The toolbox pages and the Resources list agree.** All seven pages were read (the Relationships page has 37 items, matching the 37 connector stereotypes), checked on screen on EA 17.1 build 1716, 2026-11-04. From a Goal, the quick links offered Objective (includes, is included by, is quantified by), Strategy (has efforts towards channeled by) and Assessment (has achievement affected by), in the standard's phrases rather than the stereotype names; one source was tried.

## 8. Checking a model

The BMM ruleset (`rulesets/bmm-1/bmm-1_rules.yaml`, 13 rules) checks the relationship table, the stated cardinalities, like-kind inclusion, that an enforcement level has a Tactic behind it, and that Courses of Action are governed and Influencers categorized. It does not check wording (an Objective being measurable, a Mission having three parts, an Influencer being neutral), acyclic hierarchies, or the relationship between Assessments, Ends and Means across three elements; those need a person. The ruleset's header says how many of the language's 39 rules it covers and why the other 25 are left to a person.

3 of 13 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

An Influencer is classed as internal or external either by a subclass or by its Influencer Category, and `BMM13-REL-006` accepts both.
