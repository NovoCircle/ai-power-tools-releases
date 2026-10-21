# Publishing, service refresh, and Microsoft 365 Copilot

The long form of `SKILL.md` §6 (a published model's refresh), §6b (Microsoft 365 Copilot) and the
values step of §4.4. Every
fact here was measured on the Westbrook Bank reference model on 2026-10-19 with Power BI Desktop
2.159.883.0, unless it says it is Microsoft's documentation. Westbrook figures illustrate the shape of
a result, never what a customer will get. The records are in
[`measured-power-bi-behavior.md`](measured-power-bi-behavior.md) §11.

---

## 1. A published model on a SQL database in Fabric

Path B built into a SQL database in Microsoft Fabric (`ea-reporting-database` §3) gives a project
whose every partition reads `Sql.Database("<server>.database.fabric.microsoft.com,1433",
"<database>")`. No generator change is involved.

1. **Open and refresh in Power BI Desktop.** The SQL Server credential dialog offers Windows,
   Database and Microsoft account: choose **Microsoft account** and sign in.
2. **Publish from Power BI Desktop.** Publishing needs Power BI Desktop's own sign-in, which is
   separate from the data-source sign-in.
3. **Set the credentials in the service.** The first service refresh fails ("credentials not
   specified") until they are set: the semantic model's settings, *Data source credentials*, *Edit
   credentials*. Choose **OAuth2**, privacy level **Organizational**, and sign in. The settings page
   says "You don't need a gateway for this semantic model, because all of its data sources are in
   the cloud."
4. **Refresh.** The measured service refresh completed in seconds and returned the same counts as
   Desktop and the database.

**The misleading message.** If *Edit credentials* says **"You need to use SSL (HTTPS) when you use
OAuth 2.0 authentication"**, nothing is wrong with SSL: the browser blocked the Microsoft sign-in
pop-up. Allow pop-ups for the Power BI site and choose OAuth2 again; the sign-in window then opens.

**Not measured:** how long the stored OAuth2 credential, which is the person's own, keeps a scheduled
refresh working; the same model in a Pro workspace with this source; a workspace identity or a
service principal as the credential.

**The data behind it** is refreshed first, by the reporting refresh (`ea-reporting-database` §8),
which needs a person to complete the Microsoft sign-in once per server process.

**A local SQL Server** needs an on-premises data gateway for a published model to refresh. That is
the mechanism as Microsoft describes it; it has not been tested with this model.

---

## 2. Microsoft 365 Copilot

### What it does without any help

Microsoft 365 Copilot Chat was asked 11 fixed questions about the published Westbrook model, three
ways, twice each, in a fresh chat each time (66 chats):

| Way | Questions right in both runs |
|---|---|
| No report named | 6 of 11 |
| Report named | 9 of 11 |
| Model link pasted | 9 of 11 |

The model had no descriptions. Once Copilot reached it, it answered counts, tagged-value filters,
text inside a multi-valued tag ("GLBA" inside "GLBA, FFIEC"), and connector traversals in both
directions correctly, through the `Con_` tables. It failed in three places:

- **Finding the model.** With no report named, it found the model only when the question's words
  matched it, and otherwise answered from the person's other Microsoft 365 content, or not at all.
- **Business terms.** Asked which applications are being retired, it found the Sunset ones and
  missed Archive in all four runs that reached the model.
- **One row too many.** It answered 46 business applications once where there are 45, likely the
  blank member (`SKILL.md` §2).

### Descriptions, and how they reach it

- **Not required.** The baseline above had none.
- **They carry business terms.** The same question, with a description on the `lifecycle` column
  saying applications being retired are those in Sunset or Archive: 4 of 4 right. The same model
  without it, in the same workspace: 0 of 4.
- **Publish from Power BI Desktop.** Copilot used the description within minutes of a Desktop
  publish: a few minutes on a Pro workspace; on a Fabric workspace, about 1 minute was too soon and
  about 8 minutes was enough.
- **Other routes were not seen.** The same text written into the published model through the Fabric
  REST API (a definition update) and refreshed was returned by DAX on the model, but Copilot did
  not use it after more than 25 minutes. So a description is changed in the descriptions file,
  the project regenerated, opened, and published from Desktop again.
- **Length.** The measured description was 210 characters. Copilot in Power BI documents reading
  the first 200; the generator refuses file entries over 250.
- Microsoft does not document that Microsoft 365 Copilot reads descriptions at all, so a change on
  Microsoft's side could alter this.

### Helping it find the model

Copilot finds Power BI **reports**; a semantic model on its own is reached by pasting its link.
Tell the person to name the report in the question, attach it from Copilot's attach menu, or paste
the model's link, and to give the project a name people will actually say. A fresh project's
Overview page puts the Table Directory and the entity counts on a report page; **whether that helps
Copilot find the model unprompted is not measured.**

### What it needs (Microsoft's documentation, and what was measured)

- **No Copilot capacity.** Measured: Copilot answered from a model in a Power BI Pro workspace and in
  a Fabric workspace. Microsoft documents Pro, Premium Per User, Premium and Fabric capacities as
  supported and Embedded capacities as not. Copilot in Power BI, and Prep data for AI, are a
  different product with a paid-capacity requirement; do not conflate them.
- **Per person who asks:** a Microsoft 365 Copilot license (without it, the free Copilot Chat does
  not answer from Power BI) and a Power BI Pro or Premium Per User license, with access to the
  report or model.
- **Microsoft 365 admin center:** Copilot settings, *Fabric data available in Microsoft Copilot*,
  on for those people.
- **Fabric admin portal, tenant settings:** *Share Fabric data with your Microsoft 365 services*,
  on. It lets Copilot find reports without being pointed at them, and list them in the attach
  menu.
- **Outside the United States and the European Union:** the tenant setting that lets data sent to
  Azure OpenAI be processed outside the capacity's region.

These are the customer's administrators' settings. Say what is needed; never change them.

### Not measured

Copilot in Power BI, Fabric data agents and any Copilot other than Microsoft 365 Copilot Chat;
whether Copilot uses the count measures instead of writing its own DAX; the Overview page's effect on
finding the model; descriptions over 210 characters; a model past the 1,000 tables-plus-columns
limit. **Copilot is not deterministic**: the same question once gave 45 and once 46, so ask twice
before quoting an answer.

---

## 3. The values behind a business term (`SKILL.md` §4.4, step 1)

Read the distinct values of every tag on one stereotype's elements from EA itself, on any path,
with one read-only query:

```
ea_analyze(operation="execute_sql", params={"sql":
  "SELECT p.Property, p.Value, COUNT(*) AS elements FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Stereotype = '<stereotype>' GROUP BY p.Property, p.Value ORDER BY p.Property, p.Value"})
```

- `<stereotype>` is the bare stereotype name as EA stores it in `t_object.Stereotype`, not the
  alias the table is named by. Read it from the technology, or from the Table Directory's
  `stereotype` column.
- Add `AND p.Property = '<tag>'` to read one tag only.
- It reads the whole repository, so it can show values from packages the profile excludes; say so
  if a value appears that the business layer does not hold.
- `t_object.Stereotype` holds an element's first stereotype. An element carrying two of the
  technology's stereotypes is counted under its first only.
- EA stores a value longer than 255 characters as `<memo>`; the text itself is in the row's
  `Notes`.
- Plain SQL only, no dialect functions: the same query runs on a SQL Server repository and a `.qea`
  file, and a statement EA cannot run opens a dialog that blocks every later call.

Illustration, on Westbrook Bank's `WBABusinessApplication` (substitute your own stereotype and
tags): `lifecycle` returns Archive 2, Current 33, Deprecated 1, Strategic 8 and Sunset 2. Show the
person those values, then ask which of them each of their terms covers.
