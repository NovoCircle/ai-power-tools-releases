# A reporting database in the cloud

The long form of `SKILL.md` §3b: path B built into a SQL database in Microsoft Fabric (measured) or an
Azure SQL Database (expected to work, not measured), signed in with Microsoft Entra. Westbrook Bank
values are an illustration; substitute your own server, database and account.

---

## 1. Before the first build

**A SQL database in Fabric needs a Fabric capacity.** The workspace that holds it must be on one. Check
that the capacity is not paused before a build or a refresh. A customer without a Fabric capacity keeps a local SQL Server (path B) or Parquet (path C).

**Create the database in the Fabric portal first.** AI Power Tools cannot create it there: a SQL
database in Fabric refuses the `master` database that a local SQL Server build uses to create a
missing one. Then read two values from the database's connection strings in the portal:

| Profile key | Where it comes from | Measured form |
|---|---|---|
| `target.server` | The server name | `<id>.database.fabric.microsoft.com,1433` |
| `target.database` | The database name | The display name followed by the item id, `<DisplayName>-<item id>`. **Not the display name alone** |

**The profile.** Illustration with Westbrook Bank; substitute your own:

```json
"target": {"kind": "reporting_database",
           "server": "<id>.database.fabric.microsoft.com,1433",
           "database": "WestbrookReporting-<item id>", "schema": "logical",
           "authentication": "entra-interactive", "user": "architect@westbrookbank.example"}
```

| Key | Values |
|---|---|
| `target.authentication` | `windows` (the default, as before: the Windows account running AI Power Tools) or `entra-interactive` (a person signs in with a Microsoft work account). Anything else is refused |
| `target.user` | Optional, with `entra-interactive` only: the account the sign-in window suggests. With `windows` it is refused: Windows authentication uses the Windows account |

Direct access (`target.kind` `ea_database`) refuses `entra-interactive`: Entra sign-in was measured on
reporting databases only. A Parquet profile has no database to sign in to. A server older than the
version named in `SKILL.md` §3b ignores `target.authentication` and connects with Windows
authentication, which a SQL database in Fabric refuses.

**The driver.** Entra sign-in uses the Microsoft OLE DB Driver for SQL Server: version 18 (provider
`MSOLEDBSQL`) was measured; version 19 (`MSOLEDBSQL19`) is used only when 18 is absent and is not
measured. With neither installed the operation is refused with Microsoft's download page. The older
`SQLOLEDB` provider is never used for Entra, and every Entra error names the provider and driver it
used.

---

## 2. The sign-in

- **A person completes it.** The first operation that opens the database in a server process shows
  Microsoft's sign-in window ("Windows Azure Authentication" on driver 18), restored and brought to
  the front. Someone signs in there, with multifactor approval if the tenant asks for it.
- **Once per server process.** Later calls in the same process reuse the sign-in without a prompt.
  Measured with the approach the server uses, EA attached: a build, then two refreshes five minutes
  apart, on one sign-in. A restart of the server needs a new sign-in. How long a sign-in lasts
  beyond five minutes is not measured; when it expires, the next call shows the window again.
- **No one answers.** After about ten minutes the operation stops with a sign-in failure and writes
  nothing; a refresh leaves the previous reporting data live. A canceled or failed sign-in is
  reported as such, not as a missing database (`replay_reporting_database` returns
  `sign_in_failed`, or `cannot_connect` when the server could not be reached).
- **Unattended sign-in is not offered.** A scheduled refresh into a SQL database in Fabric (`SKILL.md`
  §8) needs someone at the machine when the server process first connects. There is no service
  principal option.

---

## 3. What was measured on Westbrook

Path B into a SQL database in Fabric on a Fabric trial capacity, with the server's own build and
check and the Entra connection: the build was `aligned`, and `check_business_layer` compared 1,008
cells against an independent read through EA with **0 differences**, the same cell count as the
local SQL Server build. A second build (a refresh) also succeeded. Westbrook is small; these are not
timings or sizes a customer should expect.

---

## 4. Power BI, and what is not supported

- **Power BI reads it in Import**, like any path B database. The project needs no change for a cloud
  database. A published model refreshes in the Power BI service with **no gateway**, using OAuth2
  credentials: `ea-power-bi` §6, including the misleading "use SSL" message when the browser blocks
  the sign-in pop-up.
- **Direct Lake and OneLake copies of the business layer are not supported.** The database copies
  itself into OneLake automatically, but only its tables: EA's tables are there, the business
  layer's views are not. Direct Lake reads tables only, and the database's SQL analytics endpoint
  cannot run the business layer's views (they use recursive queries it refuses).
- **Removing the layer** (`SKILL.md` §7) stops a published model's refresh exactly as it does on a
  local SQL Server.
