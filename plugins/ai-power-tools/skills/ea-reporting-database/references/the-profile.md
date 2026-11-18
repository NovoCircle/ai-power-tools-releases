# The profile

The saved profile is one JSON file the user keeps; every refresh reuses it. `SKILL.md` §4 has the
shape. Westbrook Bank's `WBA` technology is an illustration; substitute your own.

| Part | What it is |
|---|---|
| `technology` | The MDG technology id the layer follows. Read from EA in whichever place it is stored (a registered file, Location: Project or Location: Model). The build result's `technology.source` says where the definition was read from (for example, the model, Location: Model); that is not `get_mdg_from_runtime`'s `source: live`, which says only whether EA has the technology loaded |
| `scope.roots`, `scope.exclude` | Package GUIDs. A whole package subtree is the unit; a renamed or moved package keeps its setting. Find GUIDs with `execute_sql`: `SELECT ea_guid, Name, Parent_ID FROM t_package` |
| `inclusion` | The answer to the §2b question - paste `resolve_answer(...).inclusion` here. Both lists empty is "only what my MDG defines" |
| `inclusion_choice` | `answer.record()` from §2b: the option chosen, the gaps excluded, the technology version at the time. Optional, but **save it**: builds and refreshes use it to flag a stereotype or connector key it does not cover (`not_covered_by_inclusion_choice`) and a changed technology version (`mdg_version_changed`) |
| `target.kind` | `ea_database`, `reporting_database` or `parquet` (§3) |
| `target.server`, `target.database` | Paths A and B. For A, the EA repository's own database. For B, a separate database: letters, digits, `_` and `-` only. On SQL Server it is created if it does not exist; a SQL database in Microsoft Fabric is created in the Fabric portal first, and its database name is the one on its connection strings, not the display name ([`the-cloud-database.md`](the-cloud-database.md)). A reporting build refuses a database that holds an EA repository's own tables, because it replaces the tables in its target |
| `target.authentication` | How the database is signed in to: `windows` (the default: the Windows account running AI Power Tools) or `entra-interactive` (a person signs in with a Microsoft work account; for a SQL database in Fabric or an Azure SQL Database). Direct access (`ea_database`) refuses `entra-interactive` |
| `target.user` | With `entra-interactive` only: the account the sign-in window suggests. Set it with Microsoft's OLE DB Driver 18, which refuses an interactive sign-in without it (measured 13 Nov 2026). Refused with `windows` |
| `target.output` | Path B only: `views` (the default), `tables` (each business view also copied into a keyed table, for Fabric) or `script` (the views, the two scope tables and a T-SQL file of the views for a Fabric SQL analytics endpoint, with no business tables). On another path, refused. `SKILL.md` §3c, [`the-cloud-database.md`](the-cloud-database.md) §5 |
| `target.schema` | The schema the business tables go in. `logical` when the profile gives none, on every path |
| `target.folder` | Path C: the folder the Parquet files go in |
| `source_id` | Optional top-level text. A lowercase slug naming the repository, for example `westbrook-bank` (letters and digits in groups joined by single hyphens, at most 64 characters). The skill proposes it from the repository name and the person confirms it. The server validates it and keeps it as given but never writes it, and reports it as `source.id` in the definition JSON, `source_id` in the load record and the one-row `Source` view or table (paths A and B). A value that breaks the rule is refused with a message saying so; fix it in the profile |

**Proposing `source_id`.** Make the default from the repository name: lowercase it, turn each run of characters other than a-z and 0-9 into one hyphen, trim hyphens from the ends, cut at 64 characters. `WestbrookBank.qea` gives `westbrookbank`; the person may prefer `westbrook-bank`. Show it and ask the person to confirm or change it, and write the confirmed value into the profile. Never write a guess silently. A profile with no `source_id` still builds and every operation's result carries a `warnings` entry; an existing profile is not blocked.

**Scope rules.** `scope.roots` entries may be any package; its whole subtree is kept. A *root package*, for the new-root flag below, is a top-level package, one with no parent package (`Parent_ID` 0). There is no masking: everything in a kept package is in the output, including
EA's own notes and tagged values. To keep content out, exclude the package. A root package created
after setup is **left out and flagged** on the next build; an exclusion that matches nothing is
flagged; a package deleted in EA is gone after the next build.

**List every root package you do not want reported in `scope.exclude`, by GUID.** A root package
the profile names in neither `roots` nor `exclude` is flagged `new_root_left_out` on every
preflight, build and refresh of the reporting-database and Parquet paths (direct access does not
report it), because the flag is meant for packages created after setup and
cannot tell those from ones you chose to leave out. Naming it in `exclude` is what records the
decision and silences the flag.

**The census cannot tell a documentation subtree from model content.** A repository can hold packages
that describe the modeling language (a hand-built metamodel or pattern library) using the same
stereotypes as real content. The census reads the stereotype an element carries, never the package it
sits in, so those elements are counted as business data and inflate every count. No check can find
them. Look at the top-level package layout before choosing `roots`, ask whether any subtree describes
the language rather than the estate, and scope it out: name only the roots that hold the estate, and
list the rest in `scope.exclude`.
