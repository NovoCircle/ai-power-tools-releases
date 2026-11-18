---
name: prol-modeling-languages
description: Load, update, configure and retire an MDG Technology as a Prolaborate modeling language, and keep its profiles (element forms, tag visibility, chart View dropdowns) in step with the MDG installed in Enterprise Architect. Use after an MDG release that is published through Prolaborate, when element pages or designer charts show wrong or missing tags, or when asked which modeling language a Prolaborate repository uses. Every change needs the person's go, names the identity acting, records the old profile first and is read back. This is the only configuration change a Prolaborate skill makes; all other administration stops.
---

# Prolaborate modeling languages

*Written from one live walkthrough on one Sparx-hosted tenant (EA cloud repositories), driven as a Super
Admin on Prolaborate 5.6.1.40, and from a second run on one client engagement. Each fact marked "seen
once" below was measured once, on one tenant, as a Super Admin. A Super Admin short-circuits
Prolaborate's authorization checks, so nothing verified this way shows what a restricted user sees or can
do.*

Prolaborate keeps its **own copy** of each modeling language (an uploaded MDG XML) and its **own
profiles**. It does not follow the MDG installed in EA. Every MDG release that changes stereotypes or tags
needs a Prolaborate step, or element pages, sub-reports and designer charts keep showing the old language.

Run `prol-start-here` first (tenant, identity, repository). Read
[`../_shared/references/prolaborate-session.md`](../_shared/references/prolaborate-session.md) before
driving anything.

Westbrook Bank is the example used here: technology id `WBA`, stereotype `WBA::WBABusinessApplication`.
Read each Westbrook value as an illustration and substitute your own technology and stereotypes. Nothing
here assumes the repository holds a Westbrook model.

---

## 0. The boundary

Modeling languages and profiles change repository configuration that affects **every user of the
repository**. The rules for any change in this skill:

1. **A go for each change.** Before the change, tell the person what will change, in which repository, and
   who is affected, and wait for an explicit yes. A go covers exactly what was shown. A change that was not
   shown needs a new go. Telling users beforehand is the person's job: say so.
2. **State the acting identity.** Name the signed-in person and role (from the token claims) before the
   change. Everything is attributed to them.
3. **Record the old profile first** (§1.6). If it cannot be recorded, do not change anything.
4. **Read it back.** After every change, read the result through the API and compare it with what was
   agreed. Do not trust the absence of an error: Prolaborate returns a success with a failure in the body
   on several calls.
5. **Never delete a language** without a separate, explicit go. Retire it instead (§4).

**Everything else in administration stops.** Users, groups, access permissions, sections, integrated
applications, the license and other repository settings are not changed by this skill. A request for one
of those is answered "no skill does that" and stops. `prol-admin` reads them.

---

## 1. Assess (read-only)

1. Open the repository: Prolaborate home, then the web portal (it opens in a **new tab**), then
   Repositories, then the repository. Modeling languages are configured **per repository**.
2. Hamburger menu (left end of the top bar), then **Repository Configuration**, then **Modeling
   Languages**. If it isn't visible, type "modeling languages" in the menu's search box.
3. Record the list (set rows per page to 50): Name, Type (Built-In or Custom), Version, Profiles, Status.
   Note which custom language is Active.
4. Read the new MDG file's technology id: `<Documentation id="...">` in the XML (or `ea_mdg
   parse_mdg_xml`). Compare it with the language currently loaded.
5. Decide the path:

| New file's id vs loaded language | Path |
|---|---|
| Same id (a new version of the same technology) | **Update in place** (§2a). Keeps the entry, its profiles and links. **Does not add new tags to existing forms** (§2a) |
| Different id | **Add new** (§2b), then retire the old entry (§4). Prolaborate refuses an in-place update across ids |

6. **Record the old profile before changing anything.** Read it through the API (below): every
   stereotype's form, its groups, each tag's label, Show state and write access. Keep it in the
   conversation as the restore reference and the template for the new profile, and offer to save it to a
   file the person names, since it is the rollback path. Also keep the old MDG XML on disk.
7. **Take a database backup before any change** (or have the instance's owner take one). The recorded
   profile and the old MDG file do not restore everything: an in-place update and a form's first save
   change hidden fields that the interface cannot put back (§2a, §3b, §6). The backup is the only exact
   way back. Don't start without it unless the person says, after being told this, to go ahead without.

## 2a. Update in place (same technology id)

Needs the go of §0. State which language entry will change and what it will lose if the new file removes
tags.

1. Pencil on the language's row. On 5.6.1.5 the pencil opens **Edit Modeling Language** directly, with no
   menu step (seen once). On other versions a menu may come first.
2. **Name**: include the new version. **Description**: say what it replaced (the history is otherwise
   lost). An update that keeps the **same version number** is accepted (seen once, 5.6.1.5), so a
   re-upload of the same version is possible.
3. **Choose from existing MDGs or upload your own (in XML format)**: select **Choose File** and pick the
   new MDG.
4. Status Active, then **Update**. Back on the list, confirm the Version column and that the profile
   count is unchanged.
5. **An in-place update does not add new tags to existing forms.** Seen once: the update kept each
   profile and its form setup, dropped tags the new MDG removed, and left tags the new MDG added in the
   Form Designer's Technology Properties panel, not on the form. So an update that adds a tag is not
   finished until the forms are checked:
   1. List the MDG's tags per stereotype from the new XML.
   2. Read each stereotype's form back through `POST /api/mdg/stereptype/GetAll` (§3) and compare its tag
      labels with that list. **Count only groups where `isUnassigned` is false.** A tag the update added
      is listed by the API in the stereotype's **Unassigned Group** with Show (`isEnabled`) true (seen
      once, 5.6.1.5). A comparison that reads every group, or that takes Show as "on the form", reports
      the new tag as present when it is not on the form.
   3. For each tag missing from a form, the person **drags it in from the Technology Properties panel**
      in the Form Designer, then saves. An automated drag failed when tried, so do not script it. Or
      rebuild the form from a fresh profile (§2b), which shows every MDG tag; whether a fresh profile can
      be generated for the same technology id has not been measured, so do not promise it.
   4. Read the form back again. Compare it with the recorded old profile (groups and Show states kept)
      and with the MDG's tag list (new tags present).
6. **Expected noise in the comparison.** An in-place update also changes hidden profile fields on forms it
   had no reason to touch (seen once, 5.6.1.5, an uncurated default profile, Super Admin). None of them
   shows in the Form Designer. Ignore these when you diff against the recorded old profile, and say
   they were ignored:
   - the Basic Attributes group's `isAssigned`, true to false, on every form;
   - `elementType` on the technology tag rows of element stereotypes, null to "Element";
   - `inheritedStereotypes` on connector stereotypes, "" to null.

   Re-uploading the previous MDG does not change these back.

## 2b. Add new (different technology id)

Needs the go of §0.

1. **+ Add Modeling Language** (top right).
2. Fill in **MDG Details**: Name (with version), Description, **Choose File** and the **full MDG XML**
   (the same file installed in EA; windows-1252 encoding is accepted), Status **Active**.
3. **Default Profile Settings** (they shape the generated profile):

| Setting | Default | Effect |
|---|---|---|
| Technology Properties Group | Show | tags defined by the MDG appear as a group |
| Properties of Base Stereotype | Include | tags inherited from the stereotype the MDG extends (for example ArchiMate) are included |
| Inherited Properties Group | Show | those inherited tags appear as their own group |

4. **Assigned User Groups**: the groups that get this language's profile. Select All unless told
   otherwise.
5. **Save**. Prolaborate confirms "Modeling Language added successfully" and that a default profile has
   been created with the default configuration of stereotypes, and offers **Configure Stereotypes**.

Upload the **full MDG**, not the UML-profile-only export: the full file carries the reference data
(Property Types) and matches what EA has installed.

## 3. Configure the profile

Each form save is a change. Get the go of §0 first, for the forms you list.

1. **Validate the generated profile.** Configure Stereotypes lists one row per UML-profile stereotype plus
   one per diagram type (Category: Element, Connector or Diagram). Count them in the MDG and compare.
   Toolbox pages never appear. The table **scrolls inside its own panel**; the page does not scroll.
2. For each element stereotype users look at: the gear on its row, then **Form Designer**. Recreate the
   groups and visible tags from the old profile (§1.6), mapped to the new stereotype names. **Profiles are
   keyed by stereotype name**: if stereotypes were renamed, nothing carries across automatically.
3. Whether to hide tags that are empty on every element is the customer's call. Ask; do not decide it.
   Some want every MDG field shown so people can fill it in. Use friendly display labels (the stereotype
   alias), not technology prefixes.
4. Reports built with *MDG Based Report* take their columns from this form, **in form order**, so field
   order matters. Custom properties on the form (Reports Configuration items) filter on stereotype names,
   so re-point them after a rename.
5. Repeat for every profile assigned to a user group, not just the default one.
6. Save each form, then read it back.

**Read both profiles through the API before touching a form** (read through the API, act through the
interface):

```js
// languages, with their default profile id
POST /api/mdg/GetAll            {repositoryId, dtLazyLoadingObject:{startIndex:0,rowLimit:100,sortField:'',sortOrder:1,isColumnFilterKeyUp:false,globalFilter:null,filters:[],multiFilters:[]}}
// every stereotype's form: groups[] -> properties[] with label, isEnabled (= Show), writeAccess, isDeleted
POST /api/mdg/stereptype/GetAll {mdgProfileId, dtLazyLoadingObject:{...same...}}
```

A freshly generated default profile shows **every** MDG tag; a curated old profile usually hides many.
Diff the two per stereotype by label. The list calls need the full body, with every field.

**Form Designer** (the gear on the stereotype's row; URL `.../MDGStereotype/Configure/repId/<repId>/<mdgId>/<profileId>/<Tech>::<Stereotype>/Element`,
for example `WBA::WBABusinessApplication`): groups such as Basic Attributes and `<Tech>::<Stereotype>
Attributes` list each tag as a row with a drag handle, label, display label, help text, a **Write**
toggle, a **Show** toggle and a cross (remove back to the right-hand panel). The right-hand panel offers
General, Technology, Inherited and Custom Properties to drag in. To hide a tag, switch **Show** off: it
stays in the group, as curated profiles do. **Save** (bottom right) returns to the stereotype list.

### 3b. Setting many forms by script

For a profile with many stereotypes, set the forms by script instead of by hand. Seen once: 26 forms set
up this way matched the reference profile when read back. The pattern, per form:

1. Open the form's route: `MDGStereotype/Configure/.../<qualified stereotype>/<Element|Connector|Diagram>`.
2. Toggle **Show**: the second checkbox in the tag's row.
3. Set the **Group Name** input with the browser's native value setter, then fire `input` and `change`
   events. Setting `.value` directly does not update the form's state:

```js
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(input, 'Basic Attributes');
input.dispatchEvent(new Event('input',  { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

4. **Save.** One form per save, never several forms in one go.
5. Read the form back through `POST /api/mdg/stereptype/GetAll` and compare it with what was meant. Stop
   at the first mismatch, tell the person, and change nothing further. **A form's first save rewrites
   fields the script did not touch**, to match what the Form Designer screen shows (seen once on one
   form, 5.6.1.5). Do not count these as a mismatch, and list them for the person before the first save:
   - Basic Attributes order and positions (for example from BaseType, Notes, Author, Name to Name,
     Notes, Author, BaseType, positions 0 to 3);
   - BaseType's Write, true to false (the screen shows it as a gray "Read");
   - Write, true to false, on properties in the Unassigned Group (Modified, Stereotype, Created and
     LinkedDocument were seen);
   - the technology tags' positions, renumbered 0, 1, 2 and so on;
   - `elementType` on the technology tags, set by an earlier in-place update, reset to null.

   Compare the intended changes (the Show states and group names the plan lists) and treat only
   differences outside this list as a mismatch. **The first save of a form can't be fully reversed**:
   saving the old values back through the form writes the screen's state again, so these fields do not
   return to what they were. Say so in the plan, and take the backup of §1.6 first.

Rules for the batch:

- Show the person the full plan before the first save: every stereotype, every tag's Show state and
  group name. The go covers that list and nothing outside it.
- The row positions, the checkbox order and the input labels are what the screen showed once. Check each
  on the first form and say where the screen differs.
- Do not script dragging a tag from the Technology Properties panel; it failed when tried (§2a).
- A tab that is not in front can swallow clicks. Bring it to the front, and if a Save click may have been
  swallowed, read the form back before clicking again.

## 4. Retire the old language

Needs the go of §0.

1. Pencil on the old language, then **Status: Inactive**, then Update. **Update saves metadata without
   re-choosing the file.**
2. Do **not** delete it yet. An inactive language keeps its profiles: they are the rollback path and the
   reference for §3.
3. Delete only after the new language has been accepted, with its own explicit go.

## 5. Verify

1. Language list: the new language Active with the expected version; the old one Inactive.
2. Configure Stereotypes count equals MDG stereotypes plus diagram types.
3. **Compare each form with the technology.** For every stereotype, read the form back through
   `stereptype/GetAll` and compare it two ways: against the MDG's tag list (every tag present, none from
   a removed tag; count only groups where `isUnassigned` is false, since a tag an in-place update added
   sits in the Unassigned Group with Show true) and against the recorded old profile (groups and Show
   states kept; ignore the expected noise listed in §2a step 6 and §3b step 5). Report each
   stereotype that differs, and which tags. After an in-place update (§2a), missing tags are dragged in by
   the person from Technology Properties, or the forms are rebuilt from a fresh profile.
4. Open an element of each main type: its properties panel shows the expected tag groups with values.
5. A designer chart (pie, bar or column, one stereotype): its **View dropdown** lists the tags that are
   **enumerations in the MDG** and visible on the active profile for that stereotype. Strings, numbers and
   dates never appear there.
6. Click a chart segment: the sub-report shows the profile's columns (unless *MDG Based Report* is off
   on that widget).
7. Model Search filters list the new types.
8. If anything still shows the old language, refresh the repository in Prolaborate and clear its cache.
   (Seen once: not needed, element pages showed the new groups straight away.)

## 6. Rollback

- **Added new:** set the new language Inactive and the old one Active. Needs the go of §0.
- **Updated in place:** edit the entry and upload the previous MDG XML. This does **not** restore the old
  profile exactly (seen once, 5.6.1.5). It removes tags the update added, but it keeps any form changes
  made since, and it does not change back the hidden fields the update altered (§2a step 6). The forms
  may need the recorded old profile applied again (§3), and a form save changes further hidden fields
  (§3b). **The only exact way back is the database backup** taken before the change (§1.6).
- Either way, the repository's EA content must match the language (see `ea-mdg-deploy` rollback).

## 7. Capture and automation notes

- The web portal opens in a **new tab**; follow it.
- If browser-extension reads time out, test the extension on a plain page before blaming Prolaborate. Fall
  back to desktop screenshots; do not retry the same read.

## 8. What is verified, and what is not

- Seen once, on one Sparx-hosted tenant, as a Super Admin: adding a language, the default profile, the Form
  Designer controls, retiring a language, the element-page check.
- Seen once, on one client engagement, as a Super Admin: an in-place update does not add new tags to
  existing forms; the 26-form script.
- Seen once, on Prolaborate 5.6.1.5, as a Super Admin, on an uncurated default profile: the same-version
  in-place update; the new tag listed in the Unassigned Group; the hidden-field changes of §2a step 6; the
  one-form script of §3b with the first-save side effects; the failed exact rollback of §6. Everything in
  this paragraph is verified as Super Admin only, Prolaborate 5.6.1.5, 16 Nov 2026.
- Not measured: whether a fresh profile can be generated for the same technology id; any of this as a
  restricted user; any of this on a Prolaborate other than 5.6.1.40.
- Say so in the report when you rely on any of it.

## Reference files

- [`references/test-cases.md`](references/test-cases.md): acceptance cases
- [`../prol-start-here/SKILL.md`](../prol-start-here/SKILL.md): preflight and routing
- [`../ea-mdg-deploy/SKILL.md`](../ea-mdg-deploy/SKILL.md): the EA side of an MDG release
- [`../_shared/references/prolaborate-session.md`](../_shared/references/prolaborate-session.md): session,
  token and list-request body
