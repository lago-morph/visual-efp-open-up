# EPF Practices — static method browser

A single static page (`index.html`, vanilla JS + [D3](https://d3js.org/), no
build step) that browses the **complete Eclipse Process Framework (EPF)
Practices method library** — all 54 plugins / 719 source files: every task,
work product, role, guideline, concept, checklist, template, capability pattern,
delivery process and term definition, plus the **UMA variability**
(`contributes` / `extends` / `replaces`) that the practices use to modify one
another. The reading pane shows each element as one **assembled** page — applying
variability at render time, the way the published site does — while the
underlying `data/method.json` stays faithful to the source, keeping every base
element and every variability fragment as a separate node joined by variability
edges. Browse by **element type**, by **plugin/practice**, or by **configuration**
(e.g. OpenUP), with a force-directed graph view and shareable `#guid` links.

> **Note on OpenUP:** OpenUP is not a separate download — it is one of the
> *configurations* inside this library (a selection of the `core.*` +
> `practice.*` plugins). Ingesting all 54 plugins therefore includes all of
> OpenUP plus the extra EPF practices layered around it. Use the **Configuration**
> facet to view just OpenUP (47 plugins / 686 elements), All EPF Practices, or
> Agile Business Rules Development.

## Enable GitHub Pages

Everything is served from the **repository root**, so: **Settings → Pages →
Build and deployment → Source: “Deploy from a branch” → Branch: `main` / `/ (root)`
→ Save.** The site then appears at
**https://lago-morph.github.io/visual-efp-open-up/** (a `.nojekyll` file is
included so `data/` and the `source/` resources serve as-is).

## Provenance

The method content is **EPF Practices 1.5.1.5**, dated **2012-12-12**, taken
verbatim from the Internet Archive item
[`epf-2021-11-26`](https://archive.org/download/epf-2021-11-26/Libraries/epf_practices_library_1.5.1.5_20121212.zip)
and committed unmodified under [`source/`](source/) (the canonical copy — never
edited). `tools/fetch_source.sh` documents the download.

## Licensing (dual)

This repository is **dual-licensed** — see [`LICENSE`](LICENSE) and
[`NOTICE`](NOTICE):

| Part | License |
|------|---------|
| **Viewer & tooling** — `index.html`, `tools/`, the `method.json` schema, docs | **MIT** © Lagomorph Labs — [`LICENSES/MIT.txt`](LICENSES/MIT.txt) |
| **Imported EPF content** — everything under `source/` and all method text in `data/method.json` | **EPL-1.0** — [`LICENSES/EPL-1.0.txt`](LICENSES/EPL-1.0.txt) |

The whole library carries a single uniform content license (EPL-1.0; verified
across all 52 plugin copyright statements and `source/epf_prac_1515/about.htm`).
Copyright holders (IBM, Telelogic, Armstrong Process Group, Number Six Software,
Xansa, Scaled Agile, and others) are preserved verbatim in [`NOTICE`](NOTICE).
**Every content node in `data/method.json` is tagged `"license": "EPL-1.0"`** and
the viewer shows each element's license with a link to the in-repo copy.

## `data/method.json` shape

A single viewer-agnostic file (re-usable by a later harvest pipeline). The two
core records:

- **node** — `{guid, name, presentation_name, type, plugin, body_html,
  sections:[{guid, name, description_html}], source_path}` — plus
  `content_guid`, `brief_description`, `variability_type`, `has_content`,
  `attachments[]`, and `license` ("EPL-1.0").
- **edge** — `{from_guid, to_guid, type, variability}` — `variability` is `true`
  for `contributes` / `extends` / `replaces`; ordinary references (`performedBy`,
  `mandatoryInput`, `output`, `guidelines`, …) are `false`. A `to_guid` not
  present as a node is a dead link (rendered grey, never fatal).

The file also carries `plugins[]`, `configurations[]` (each with its resolved
plugin list), and a `meta` block with provenance, license, and counts.
`guid` is the UMA **element** GUID (the cross-reference space); body prose is
joined in from the matching content file via the element's presentation link.

## Building `data/method.json`

```sh
python3 tools/build_method_json.py    # stdlib only; reads source/, writes data/method.json
```

The script parses each plugin's `plugin.xmi` (skeleton: typed elements,
relationship refs, variability), joins each to its prose content file, adds
capability-pattern / delivery-process nodes from per-pattern `model.xmi`,
extracts template `.dot` document structure (strings-style), resolves the three
configurations, tags content with EPL-1.0, and prints a verification report.

### Current counts

900 nodes · 1559 edges · 219 variability edges (187 `contributes`, 29 `extends`,
3 `replaces`) · 53 plugins · 3 configurations. Published (content-bearing)
elements by type: 80 tasks, 53 work products, 26 roles, 83 guidelines,
65 concepts, 20 checklists, 20 templates, 21 examples, 108 term definitions,
~26 capability patterns, 4 delivery processes. (Totals are higher than the
published counts because content-free `contributes` fragments from the `.assign`
plugins are kept as their own nodes; the assembled reading pane re-collapses
them — see [`PLAN.md`](PLAN.md).)

## Repository layout

```
index.html              the viewer (MIT)
data/method.json         generated graph (content is EPL-1.0)
tools/                   build_method_json.py, fetch_source.sh (MIT)
source/epf_prac_1515/    verbatim EPF Practices 1.5.1.5 archive (EPL-1.0)
LICENSE, NOTICE, LICENSES/   dual-license declaration + texts
PLAN.md                  design notes / reconnaissance findings
.nojekyll                serve data/ and source/ as-is on Pages
```
