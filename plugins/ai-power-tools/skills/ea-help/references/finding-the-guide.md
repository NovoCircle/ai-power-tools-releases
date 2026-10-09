# Finding the right page in Sparx's user guide

Everything in this file is about one problem: getting to the correct page, of the correct
version, without pulling a documentation site into a session's context budget.

---

## 1. The address

```
https://sparxsystems.com/enterprise_architect_user_guide/<major>.<minor>/<section>/<page>.html
```

The version segment is `major.minor` — `17.2`, `17.1`, `17.0`, `16.1`, `16.0`, `15.2`, `15.1`,
`15.0`, `14.0`. Nothing in the path encodes a build number, an edition or a language.

Top-level section folders in the current generation of the guide:

| Folder | Holds |
|---|---|
| `getting_started` | Editions, licensing, installation, first steps |
| `the_application_desktop` | Ribbons, windows, docked views, workspace layouts |
| `the_model_repository` | Project files, DBMS repositories, Pro Cloud Server, security |
| `modeling_fundamentals` | Baselines, comparison, traceability, element properties |
| `modeling_languages` | UML, SysML, BPMN, ArchiMate and the rest |
| `modeling_frameworks` | MDG technologies, profiles, toolboxes, the technology wizard |
| `modeling_domains` | Code engineering, database engineering, grammars |
| `model_exchange` | XMI import and export, package control, merges |
| `model_publishing` | Documents, templates, HTML output |
| `add-ins___scripting` | The Automation Interface — one page per COM class |
| `teams___collaboration`, `model_security`, `model_simulation`, `execution_analysis`, `project_build___deploy`, `guide_books`, `glossary` | As named |

Older versions use different folder names for the same material — `modeling_frameworks` content
sits under `modeling` in 15.2, for example. **Page slugs survive version changes far better than
folder names do.** Rewriting only the version segment of a working URL is a first guess, not an
answer.

---

## 2. Two redirects that return success

Both of these return HTTP 200 and land you somewhere plausible.

**The bare version directory resolves to the current version.** Requesting the version root, or
`index.html` beneath it, lands on the *newest published* guide's welcome page — not the version
in the URL you typed. A session that starts there and follows links is reading the wrong guide
with nothing to signal it.

**An unknown page under a real version resolves to that version's welcome page.** A misspelled,
renamed or version-absent slug does not 404. It redirects to `<version>/welcome/index.html` with
a 200.

So:

> Status codes are useless here. **Compare the final URL after redirects against the URL you
> asked for.** It must carry the same version segment and the same page. Landing on
> `welcome/index.html` means the page you wanted was not served.

The one place a status code does help: a version with no guide at all 404s on its bare
directory. That is a usable existence probe for the version, and nothing more — confirm a real
content page before trusting the version resolved.

Entry points that are real pages rather than directories:

| Version range | Guide entry page |
|---|---|
| 16.0 and later | `<version>/welcome/index.html` |
| 15.2 and earlier | `<version>/index/index.html` |

---

## 3. Searching the guide

Sparx runs a full-text search across its site. Scoped to the user guide:

```
https://sparxsystems.com/search/sphider/search.php?query=<terms>&catid=24&search=1&tab=1
```

`catid=24` is the user-guide category. Results come back as a page of links to guide pages.

Three properties that decide how you use it:

**The index is pinned to a single version.** Results carry one version in their URLs, and it is
not necessarily the newest guide, let alone the user's. Treat a result as a *page slug*: take
the section and page from it, rebuild the URL against the user's version, and verify the final
URL per section 2.

**Short queries work; long ones return nothing.** Two to four plain words find the topic
reliably. Adding punctuation, an exact identifier or a whole phrase collapses the result set to
empty rather than degrading to a near miss. When a query returns nothing, shorten it — do not
rephrase it at the same length.

| Query | Result |
|---|---|
| `MDG Technology Wizard mts` | Ten relevant pages, wizard topic first |
| `SetAppearance element appearance` | The Element Class page |
| `merge baseline compare` | Baselines, compare utility, Project Class |
| A dotted element name plus three words | Empty |

**The results page is large HTML.** Extract the links from it; do not read it. A results page
runs to roughly 175 KB of markup around a dozen useful URLs.

---

## 4. The per-version sitemap

Every version publishes a complete index of itself:

```
https://sparxsystems.com/enterprise_architect_user_guide/<version>/sitemap.xml
```

For 17.1 that is roughly 2 MB: about 4,160 page URLs and about 6,390 image URLs. Each `<url>`
entry carries the page address and, beneath it, the addresses of the images on that page.

Use it for what the search cannot do:

- **When the search returns nothing.** Filter the page URLs on the slug and pick the match.
  Slugs are descriptive, so keyword matching on the path works well.
- **When you need a page's screenshots.** The per-page `<image:loc>` entries are where the
  screenshot addresses live.
- **When you need to know a version's folder layout**, because it differs from another version's.

**Never read the sitemap into context.** Fetch it, filter it, keep the handful of matching
URLs, discard the rest.

---

## 5. What this costs

| Fetch | Size |
|---|---|
| A task topic page | 1,000–5,000 characters of text |
| An Automation Interface class page | 20,000–50,000 characters — extract the method block |
| A search results page | ~175 KB of HTML, a dozen useful links |
| A version sitemap | ~2 MB, thousands of URLs |

A normal lookup — one search plus two or three topic pages — is a few thousand tokens. The whole
guide is therefore searchable within a session, provided nothing is ever read in bulk: filter
the large artifacts outside the context window and pull in only the page you need.

For a class page, find the method name and take the block around it. Reading `Element Class` or
`Project Class` whole costs more than the entire rest of the lookup.

---

## 6. Live, not cached

Fetch the guide live each session, and hold nothing on disk.

- Pages are small and the whole lookup is cheap, so a cache saves little.
- A version's guide is republished in place. A cached copy goes stale with no signal, and a
  stale procedure is exactly the failure this skill exists to prevent.
- Within a session, keep what you already resolved — the guide base URL for the version, and
  pages you have already read. Do not re-fetch the same page twice in one session.

Two consequences worth stating out loud:

- **This needs network access.** When the site cannot be reached, say so and stop. Reconstructing
  a menu path from memory is the behavior this skill replaces.
- **It needs a real browser context.** The site sits behind bot protection, and a plain HTTP
  client is answered with a challenge page rather than the guide — an HTTP error, not content.
  If a fetch comes back as a short "checking your browser" document, that is what happened; it
  is not a missing page.

---

## 7. Screenshots

The written steps are the useful part. They name the ribbon path and the exact control labels —
a menu route, a named list, a specific button — which is what is needed to find a control in the
live application. Computer use sees EA's actual dialogs at full fidelity, so a picture of the
same dialog adds nothing.

Two facts that follow:

- **Many topic pages carry no guide screenshots at all.** On those pages every image in the
  markup is site furniture. The absence of an image is not a sign the page is the wrong one.
- **Screenshots are addressable when you do want one.** They live under
  `<version>/images/<name>.png` and are listed per page in the version sitemap.

Fetch an image only when a written step is genuinely ambiguous about which control it means —
and prefer screenshotting the live dialog instead, which is both current and free.
