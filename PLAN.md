# Plan — Static single-page browser for the full EPF Practices method library

A vanilla-JS, single-page, GitHub-Pages-deployable browser for the **complete
EPF Practices method library** (54 plugins / 719 `.xmi` files), with UMA
variability (`contributes` / `extends` / `replaces`) as first-class structure,
configuration facets (incl. OpenUP), and a viewer-side **assembled view** that
re-creates the published, human-readable pages from the faithfully decomposed
data.

This document is the agreed plan. It is written **after a reconnaissance pass**
over the actual archive, so the data-model decisions below are grounded in what
the files really contain, not assumptions.

---

## 0. Provenance

- Source: Internet Archive item `epf-2021-11-26`, file
  `Libraries/epf_practices_library_1.5.1.5_20121212.zip` (4.4 MB zipped,
  ~20 MB unzipped, 719 `.xmi` files under `epf_prac_1515/`).
- Content: **EPF Practices 1.5.1.5**, dated **2012-12-12**, license **EPL-1.0**.
- The zip is downloaded, unzipped into `source/`, and committed **verbatim**.
  `source/` is canonical and is never edited.
- OpenUP is **not** a separate download — it is one of the *configurations*
  inside this library (a selection of the `core.*` + `practice.*` plugins).

---

## 0b. Licensing & copyright preservation (added requirement)

Licensing terms and copyright notices **must be preserved**. Investigation of
the archive found a single, uniform content license:

- **All imported EPF content is EPL-1.0.** `about.htm` states the content is
  provided under the Eclipse Public License v1.0; the per-element
  `copyright.xmi` repeats it; and **all 52 plugins reference the same
  copyright statement** (`#_uuunoPsDEdmyhNQr5STrZQ`) — there is no second
  content license.
- **Copyright holders are multiple but the license is one**: IBM, Telelogic,
  Armstrong Process Group, Number Six Software, Xansa, Scaled Agile, "and
  others" (preserved verbatim in `NOTICE`).

The repository is therefore **dual-licensed**, as the user confirmed:

- **Viewer & tooling code → MIT** (`LICENSES/MIT.txt`, © Lagomorph Labs):
  `index.html`, `tools/`, the JSON schema/code, docs.
- **Imported EPF content → EPL-1.0** (`LICENSES/EPL-1.0.txt`): everything under
  `source/` and all method text embedded in `data/method.json`.

Implementation consequences:
- Root `LICENSE` explains the split; `NOTICE` preserves the copyright notices +
  provenance; both license texts live under `LICENSES/`.
- **Every content node in `data/method.json` carries `"license": "EPL-1.0"`**
  (plus the resolved `copyright_statement` GUID where present), and top-level
  `meta` records the holders + a link to `LICENSES/EPL-1.0.txt`.
- The viewer shows a per-element license line/badge linking to the in-repo
  license copy, and a global footer crediting EPL-1.0 + the copyright holders.
- The original copyright element ("EPF Copyright") remains a browseable node.
- Should any element ever resolve to a *different* copyright statement, the
  build tags that node with its own license rather than assuming EPL-1.0.

---

## 1. Reconnaissance findings (why the model below is shaped this way)

The single most important discovery: EPF splits every element into a
**skeleton** and **prose**, across two files and **two GUID spaces**.

### 1a. `plugin.xmi` = skeleton (names, types, relationships, variability)
Each of the 53 plugin directories has a `plugin.xmi` containing:
- a `ResourceManager` with `resourceDescriptors` mapping
  `id="<contentGuid>" uri="<relative/path.xmi>"` — i.e. a **GUID → content-file
  map** for that plugin;
- a `MethodPlugin` (with `name` = directory name, `guid`, `presentationName`,
  and `bases` hrefs to the plugins it extends);
- nested `methodPackages`/`childPackages` (`ContentPackage`/`ProcessPackage`)
  containing the real **`contentElements`**, each with:
  - `xsi:type` (`Task`, `Role`, `Artifact`, `Deliverable`, `Outcome`,
    `Guideline`, `Concept`, `Checklist`, `Template`, `Example`,
    `TermDefinition`, `SupportingMaterial`, `Practice`, `Tool`, `RoleSet`,
    `Discipline`, `Domain`, `CustomCategory`, `CapabilityPattern`,
    `DeliveryProcess`, `ProcessComponent`, …),
  - `xmi:id` / `guid` (the **element GUID** — what all cross-refs point at),
  - `name`, `presentationName`, `briefDescription`,
  - **relationship refs**, either as space-separated GUID-list attributes
    (`performedBy`, `mandatoryInput`, `output`, `responsibleFor`,
    `conceptsAndPapers`, `guidelines`, `examples`, `templates`,
    `contentReferences`, …) **or** as child elements with
    `href="uma://<pluginGuid>#<elementGuid>"`,
  - **variability**: a `variabilityType="contributes|extends|replaces"`
    attribute plus a `<variabilityBasedOnElement href="uma://…#<baseGuid>"/>`
    child,
  - a `<presentation href="uma://<contentGuid>#<contentGuid>"/>` linking to its
    prose file (via the ResourceManager `uri` map). **Content-free fragments
    omit this.**

### 1b. The 719 typed `.xmi` files = prose (HTML body + ordered sections)
Files under `tasks/`, `workproducts/`, `roles/`, `guidances/<kind>/`,
`capabilitypatterns/`, `deliveryprocesses/`, etc. Each is a `…Description`
object (e.g. `TaskDescription`) holding `mainDescription`, `purpose`,
`keyConsiderations`, `sections` (ordered, each with own `guid`, `name`,
`sectionDescription`), etc. **Their own `name`/`presentationName` are usually
absent or garbage** (e.g. `name=",_jcjbM…"`) — the human name lives on the
matching `plugin.xmi` element. Their `guid` is the **content GUID**
(= the element's `presentation` GUID), a *different* value from the element
GUID.

### 1c. Base vs contributor — the `.assign` plugins
Many plugins ending in `.assign` (and others) contain **content-free
contributing fragments**: `contentElements` with `variabilityType="contributes"`
and **no `<presentation>`/content file**, existing only to wire relationships
onto a base element (e.g. `test_domain.assign` contributes `workProducts` links
to the base `test_domain`). This is the heart of UMA variability and is exactly
why the brief wants "separate nodes joined by variability edges" plus an
"assembled view."

### 1d. Counts — two legitimate numbers
The brief's expected counts match the **content-file** count per directory:

| type | content files (≈ brief estimate) | defining `contentElements` (faithful) |
|------|----------------------------------:|--------------------------------------:|
| tasks | 83 | 165 |
| work products (Artifact/Deliverable/Outcome) | 55 | ~80 |
| roles | 26 | 47 |
| checklists | 20 | 20 |
| templates | 20 | 20 |
| guidelines | 84 | 93 |
| concepts | 65 | 72 |
| capability patterns | 56 *(.xmi files)* | **25** *(real patterns)* |
| delivery processes | 10 *(.xmi files)* | **4** *(real processes)* |
| term definitions | 108 | 108 |
| examples | 21 | 21 |

> **Process-count correction:** the brief's ~56 capability patterns and 10
> delivery processes are counts of `.xmi` files under those directories, but
> each pattern/process is a *subdirectory* (`content.xmi` + `model.xmi` +
> per-pattern `diagram.xmi`/`*.diagram`), so the **real** counts are **25
> capability patterns** and **4 delivery processes**. Their actual
> `CapabilityPattern`/`DeliveryProcess` elements live in the per-pattern
> `model.xmi` (name/presentationName/guid), referenced from `plugin.xmi` by
> href. Nodes for these come from the `model.xmi` element; deep activity/WBS
> trees stay out of scope per §10. Reported precisely at build time.

The faithful element count is **higher** wherever content-free contributors
exist (tasks, roles, work products, guidelines, concepts); it matches exactly
where they don't (checklists, templates, term definitions, examples). The brief
flags "if counts are wildly off, stop and show me" — see §11 / the question in
the summary. The plan reconciles both: **element-level nodes (faithful)** +
**assembled view that collapses to the published page count**.
(*Delivery-process content files vs `DeliveryProcess` process elements are
counted differently; reported precisely at build time.)

### 1e. Configurations
`configurations/{openup,all_epf_practices,tech.abrd}.xmi` are
`MethodConfiguration`s. Each lists `methodPluginSelection
href="uma://<pluginGuid>#…"` (openup → 47 plugins, all_epf_practices → 49,
tech.abrd → 20) and finer `methodPackageSelection` entries. A config resolves
to a set of plugin GUIDs → plugin dirs → the element nodes in those plugins.

### 1f. Binary resources (reality differs from the brief)
- **16 `.dot`** Word templates under `guidances/templates/resources/` — present,
  extract readable structure via printable-string scan.
- **0 `.doc`** files. Example attachments are instead **2 `.pdf`, 1 `.ppt`,
  6 `.xls`** under `guidances/examples/resources/` (plus 175 `.gif`, 48 `.jpg`
  images used inline). Plan adapts: strings-extraction for `.dot`, light text
  extraction for `.pdf`, and **download link only** for `.ppt`/`.xls` (binary,
  not text-extractable) — never fabricate structure.
- `variabilityType` values present: `contributes` (188), `extends` (29),
  `replaces` (4). **No `extends-replaces`** appears; code will still handle it
  if encountered.

---

## 2. Data model (`data/method.json`)

**Decision: one node per *method element* (the `plugin.xmi` `contentElements`),
keyed by element GUID.** This is mandatory for the brief's requirements —
variability edges connect *elements* (a content-free contributor and its base
must each be a node), and the assembled view can only merge fragments that exist
as nodes. Content-bearing elements get their prose by resolving
`presentation → content file`; content-free contributors have empty body and
`source_path` = their `plugin.xmi`.

```jsonc
// node
{
  "guid": "_NOBsuCZLEd-QuZFPf_YdqQ",      // element GUID (cross-ref target space)
  "name": "tailor_process",                // internal name (from plugin.xmi)
  "presentation_name": "Tailor the Process",
  "type": "Task",                          // xsi:type, normalized
  "plugin": "practice.mgmt.project_process_tailoring.base",
  "body_html": "<…unescaped HTML…>",       // joined main fields (see below)
  "sections": [
    { "guid": "_tJ7fc…", "name": "Verify the Environment", "description_html": "<…>" }
  ],
  "source_path": "epf_prac_1515/practice.mgmt.project_process_tailoring.base/tasks/verify_tool_config_installation.xmi",

  // extra fields (faithful + viewer convenience; documented in README)
  "content_guid": "-YTA7QOxZpdM-is9Zx_tJXQ", // presentation/content-file GUID, or null
  "brief_description": "…",
  "has_content": true                       // false for content-free contributors
}
```

```jsonc
// edge
{
  "from_guid": "_NOBsuCZLEd-QuZFPf_YdqQ", // element GUID
  "to_guid":   "_2CEzsLrREd-0rKmWr1vEGQ", // element GUID (may be unresolved → dead link)
  "type": "mandatoryInput",                // or contributes/extends/replaces/performedBy/…
  "variability": false                     // true for contributes/extends/replaces/extends-replaces
}
```

Top-level JSON also carries `configurations` (name, presentation_name, guid,
plugin list, resolved element-guid set), a `plugins` table
(dir → presentationName/guid), and small `meta`/`counts` blocks. Body main
fields (`mainDescription`, `purpose`, `keyConsiderations`, `alternatives`, …)
are unescaped once and concatenated into `body_html` under labeled headings; raw
fields are also kept in a `fields` map for fidelity.

**Edges are emitted in element-GUID space.** All `href="uma://#<guid>"` and
attribute GUID-lists already use element GUIDs, so they resolve directly against
node keys. Targets not present in the library are kept verbatim → rendered as
dead/grey links. Faithfulness rule: data is **never pre-merged**; assembly is a
pure render-time function.

---

## 3. Build pipeline (`tools/build_method_json.py`, committed, not shipped)

Stdlib-only Python 3 (`xml.etree.ElementTree`, `html`, `glob`, `re`):

1. **Index plugins.** Parse every `*/plugin.xmi`: record plugin (dir, guid,
   presentationName, `bases`); build the per-plugin `resourceDescriptors`
   GUID→uri map; walk `contentElements` recursively → emit a node per element
   (capture type, name, presentationName, briefDescription, plugin, presentation
   GUID, all relationship refs, variability).
2. **Index content files.** Parse the 719 typed `.xmi`; key by content GUID;
   extract main fields + ordered `sections`; unescape HTML once.
3. **Join.** node.content_guid → content file → fill `body_html`, `sections`,
   `source_path`. Build `elementGuid ↔ contentGuid` alias map for link
   rewriting.
4. **Edges.** From every node's refs + variability → typed edges; mark
   variability edges; leave unresolved targets as dead links.
5. **Configurations.** Parse the 3 config files → resolve plugin selections →
   element-guid membership sets.
6. **Resources.** For each `.dot`/`.pdf` referenced by a Template/Example,
   printable-string/text extraction → store extracted outline + relative file
   path; `.ppt`/`.xls` → path only, `extracted: null`.
7. **Emit** `data/method.json`; print counts by type, by plugin, by config; run
   the §11 self-checks.

A Bash helper `tools/fetch_source.sh` documents the download/unzip step for
reproducibility.

---

## 4. Front end (`index.html`, vanilla JS + D3 via CDN, no build/framework/localStorage)

- **Left sidebar** — three facet groups, each collapsible with live counts:
  1. **Element type** (Task, Work Product, Role, Checklist, Template,
     Guideline, Concept, Capability Pattern, Delivery Process, …);
  2. **Plugin / practice** (53 plugins, grouped by `core.* / practice.* /
     process.* / publish.*`);
  3. **Configuration** (All · OpenUP · All EPF Practices · tech.abrd) — picking
     one restricts every list + the graph to that config's element set.
  Plus a **text filter** over name/presentationName. Counts update with the
  active facets.
- **Reading pane (assembled by default)** — name, type badge, owning plugin,
  assembled `body_html`, ordered steps/sections, and (templates/examples) the
  extracted **document structure** + raw download link. Inline archive links and
  images are rewritten (see §6). An **"assembled from" provenance strip** lists
  the base + each contributing plugin, each click-through to the raw fragment.
- **Links panel** — inbound + outbound cross-refs as clickable nav. **Variability
  edges are visually distinct and prominent** ("↳ *replaces* «base»",
  "↳ *contributes to* «base»") and grouped above ordinary references.
- **Graph view (toggle)** — D3 force-directed; node color = element type;
  **variability edges styled distinctly** (color + dashed/weight) from reference
  edges; click a node → open it in the reading pane. Scoped to the active
  facet/config to stay legible; legend included.
- **State in URL hash** (`#<guid>`, plus optional facet params) so any view is
  shareable; back/forward works.
- **Defensive sanitization** of all archive HTML (allowlist tags/attrs; strip
  `<script>`, `on*`, `javascript:`), even though origin is trusted.

---

## 5. Assembled view — render-time merge (pure function of the data)

For the selected base element B:
1. Find incoming **`contributes`** edges; for each contributor C:
   - append C's `sections` after B's (steps merged in order);
   - merge C's body fields into B's under their headings;
   - union C's relationship refs into B's links panel;
   - add C's plugin to the provenance strip.
2. **`replaces` / `extends-replaces`**: show the replacer's content as effective;
   keep the replaced original available but visually demoted (collapsed/toggle).
3. **`extends`**: treat as additive (like contributes) unless placement is
   determinable otherwise.
4. **Ambiguity rule:** if correct placement can't be determined from the XMI,
   render the fragment in a clearly labeled **"additional content from «plugin»"**
   block on the base page — never drop content, never invent an order.

The sidebar can show both a faithful element count and an assembled
(published-page) count so the two numbers in §1d are both visible and explained.

---

## 6. Link & image rewriting

Body HTML contains `<a class="elementLink" href="./../…/foo.html"
guid="_xxx">` and `<img src="…/resources/x.gif">`. At render time:
rewrite element links to `#<guid>` SPA navigation (grey if guid unresolved);
rewrite resource `src`/download `href` to the committed `source/…` path so
images and downloads work on Pages.

---

## 7. Deployment

- **Location: repo root** (chosen for simplicity; `index.html`, `data/`,
  `source/`, `README.md`, `.nojekyll` all at root). `source/` is served but
  unreferenced except for the `.dot`/`.pdf`/`.gif`/etc. files that the pages
  link to.
- Add `.nojekyll` (so `_`-prefixed paths and `data/` serve correctly).
- **README.md**: one-paragraph what-this-is; provenance (EPF Practices 1.5.1.5,
  2012-12-12, EPL-1.0); the `data/method.json` shape (3–4 lines); and the
  one-line Pages instruction.
- **Pages setting:** Settings → Pages → Build and deployment → Source =
  "Deploy from a branch", Branch = `main`, folder = `/ (root)` (after merge);
  resulting URL `https://lago-morph.github.io/visual-efp-open-up/`.

---

## 8. Commit sequence (logical steps)

1. `PLAN.md` (this file) — **now**, before implementation.
2. `source/` verbatim archive + `.gitattributes`/`.nojekyll`.
3. `tools/` build script(s).
4. `data/method.json` (generated) + counts in commit message.
5. `index.html` front end (sidebar/reading/links).
6. Graph view + assembled view + resource rendering.
7. `README.md` + final polish.
PR is opened after the first push and accumulates these commits.

---

## 9. Libraries / constraints

- Front end: vanilla JS, **D3 v7** from CDN for the graph only. No framework, no
  bundler, no localStorage.
- Build: Python 3 stdlib only (no pip installs needed).
- Everything static; the page works by `fetch('data/method.json')`.

---

## 10. Risks / boundaries

- **Process breakdown depth:** capability patterns & delivery processes are
  included as nodes (body + sections + contained-element refs); full nested
  activity/WBS tree reconstruction is *out of scope* for v1 (noted, not
  silently dropped).
- **Config membership granularity:** resolved at **plugin** level first;
  `methodPackageSelection` refinement is a possible enhancement.
- **Binary extraction** is best-effort/strings-style by design; `.ppt`/`.xls`
  get download-only.
- **Graph scale:** ~1k nodes / many edges — mitigated by facet/config scoping
  and emphasizing variability edges.

---

## 11. Verification before "done"

- Print element counts **by type** and **by plugin** (and by configuration).
- Assert `data/method.json` parses.
- Assert every edge's `from_guid` resolves to a real node; report the count of
  `to_guid`s that are unresolved (expected: some dead links — rendered grey).
- Report both the faithful element counts and the assembled/published counts,
  and compare the latter to the brief's estimate (83 tasks, 55 WPs, 26 roles,
  20 checklists, 20 templates, ~84 guidelines, ~65 concepts, ~56 capability
  patterns, 10 delivery processes). If the *published* counts are wildly off,
  stop and report rather than guess.
- State the exact Settings → Pages config and resulting URL.

---

## 12. Open question for the user (see chat summary)

The one decision worth confirming before building: **node granularity / counts.**
The faithful model yields more elements than the brief's estimate (e.g. ~165 raw
task elements vs the estimated 83) because content-free `contributes` fragments
from the `.assign` plugins each become their own node. The assembled view
re-collapses these to the ~83 published task pages. Recommended: keep the
faithful element-level nodes (required for first-class variability + assembled
view) and surface both counts. Confirmation requested before implementation.
