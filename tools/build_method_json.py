#!/usr/bin/env python3
"""
Build data/method.json from the verbatim EPF Practices library under source/.

EPF stores every element as a SKELETON (in each plugin's plugin.xmi:
typed contentElements with the real presentationName, relationship refs, and
UMA variability) plus PROSE (the 719 typed *.xmi content files: HTML body +
ordered sections), joined by a <presentation> link across two GUID spaces.

This script parses both, keeps base + contributing fragments as SEPARATE nodes
joined by variability edges (faithful; never pre-merged), and emits a single
viewer-agnostic data/method.json. Standard library only.

Licensing: every imported content node is tagged "license": "EPL-1.0".
See NOTICE / LICENSES/EPL-1.0.txt. The viewer code is MIT (separate).
"""
import os, re, glob, json, html, datetime
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source", "epf_prac_1515")
SRC_PREFIX = "source/epf_prac_1515"
OUT = os.path.join(ROOT, "data", "method.json")

CONTENT_LICENSE = "EPL-1.0"
COPYRIGHT_HOLDERS = [
    "© Copyright IBM Corp. 1987, 2012. All Rights Reserved.",
    "© Copyright Telelogic AB. 2006, 2007. All Rights Reserved.",
    "© Copyright Armstrong Process Group, Inc. 2006. All Rights Reserved.",
    "© Copyright Number Six Software, Inc. 2006, 2007. All Rights Reserved.",
    "© Copyright Xansa plc. 2006, 2007. All Rights Reserved.",
    "© Copyright Scaled Agile, Inc. 2011. All Rights Reserved.",
    "And others. All Rights Reserved.",
]

GUIDTOK = re.compile(r'^([_-][\w.\-]*|\d+\.\d+E-?\d+)$')

# Localname -> human label, in the order we want them rendered into body_html.
FIELD_ORDER = [
    ("purpose", "Purpose"),
    ("mainDescription", "Description"),
    ("refinedDescription", "Description"),
    ("keyConsiderations", "Key Considerations"),
    ("problem", "Problem"),
    ("background", "Background"),
    ("goals", "Goals"),
    ("application", "Application"),
    ("levelsOfAdoption", "Levels of Adoption"),
    ("skills", "Skills"),
    ("assignmentApproaches", "Assignment Approaches"),
    ("representationOptions", "Representation Options"),
    ("impactOfNotHaving", "Impact of Not Having This Work Product"),
    ("reasonsForNotNeeding", "Reasons for Not Needing This Work Product"),
    ("alternatives", "Alternatives"),
    ("briefOutline", "Brief Outline"),
    ("usageNotes", "Usage Notes"),
    ("usageGuidance", "Usage Guidance"),
    ("scope", "Scope"),
    ("summary", "Summary"),
    ("synonyms", "Synonyms"),
    ("additionalInfo", "Additional Information"),
]
FIELD_LABELS = dict(FIELD_ORDER)
FIELD_NAMES = [n for n, _ in FIELD_ORDER]
# structural children of a *Description that are NOT body prose fields
STRUCTURAL = {"sections", "attachments", "nodeicon", "shapeicon"}

# attribute localnames on contentElements that are identity/data, never refs
DATA_ATTRS = {
    "id", "guid", "type", "name", "presentationName", "briefDescription",
    "variabilityType", "nodeicon", "shapeicon", "isAbstract", "orderingGuide",
    "version", "changeDate", "prefix", "suffix", "authors", "globalId",
    "hasMultipleOccurrences", "isOptional", "isPlanned", "isRepeatable",
    "isOngoing", "isEventDriven", "isAbstract", "presentationName",
}

PROCESS_TYPES = {"CapabilityPattern", "DeliveryProcess"}


def lname(tag):
    return tag.rsplit('}', 1)[-1]


def local_attrs(el):
    d = {}
    for k, v in el.attrib.items():
        d[lname(k)] = v
    return d


def frag(href):
    """element guid = the fragment after # in a uma:// href."""
    if not href:
        return None
    return href.split('#', 1)[1] if '#' in href else href


def inner_html(el):
    """Return the element's inner content. EPF stores HTML escaped in .text,
    so ElementTree's single decode IS the 'unescape once'. Serialize any real
    child nodes too, just in case."""
    parts = [el.text or '']
    for c in el:
        parts.append(ET.tostring(c, encoding='unicode'))
        parts.append(c.tail or '')
    return ''.join(parts).strip()


def is_guidlist(val):
    toks = val.split()
    return bool(toks) and all(GUIDTOK.match(t) for t in toks)


def parse(path):
    try:
        return ET.parse(path).getroot()
    except Exception as e:
        print(f"  !! parse error {path}: {e}")
        return None


# ---------------------------------------------------------------------------
# 1. Index plugins: dir/guid/name/presentationName/bases + resourceDescriptor map
# ---------------------------------------------------------------------------
plugins = {}          # dir -> {...}
plugin_guid_to_dir = {}
resmap = {}           # dir -> {contentGuid: uri}

for pf in sorted(glob.glob(os.path.join(SRC, "*", "plugin.xmi"))):
    pdir = os.path.basename(os.path.dirname(pf))
    root = parse(pf)
    if root is None:
        continue
    rm = {}
    mp = None
    for el in root.iter():
        ln = lname(el.tag)
        if ln == "resourceDescriptors":
            a = local_attrs(el)
            if a.get("id") and a.get("uri"):
                rm[a["id"]] = a["uri"]
        elif ln == "MethodPlugin" and mp is None:
            mp = el
    resmap[pdir] = rm
    a = local_attrs(mp) if mp is not None else {}
    bases = []
    if mp is not None:
        for c in mp:
            if lname(c.tag) == "bases":
                g = frag(local_attrs(c).get("href"))
                if g:
                    bases.append(g)
    g = a.get("guid")
    plugins[pdir] = {
        "dir": pdir,
        "guid": g,
        "name": a.get("name", pdir),
        "presentation_name": a.get("presentationName", pdir),
        "brief_description": a.get("briefDescription", ""),
        "bases": bases,
    }
    if g:
        plugin_guid_to_dir[g] = pdir

print(f"plugins indexed: {len(plugins)}")

# ---------------------------------------------------------------------------
# 2. Index content prose: guid -> {fields, sections, attachments, source_path}
#    Index every *Description object (root or nested, e.g. process descriptors)
# ---------------------------------------------------------------------------
content_by_guid = {}


def extract_sections(el, level=1):
    out = []
    for c in el:
        if lname(c.tag) != "sections":
            continue
        a = local_attrs(c)
        desc = ""
        for cc in c:
            if lname(cc.tag) == "sectionDescription":
                desc = inner_html(cc)
        out.append({
            "guid": a.get("guid") or a.get("id"),
            "name": a.get("name", ""),
            "description_html": desc,
            "level": level,
        })
        out.extend(extract_sections(c, level + 1))  # nested sub-sections
    return out


def rel_source(path):
    return SRC_PREFIX + "/" + os.path.relpath(path, SRC).replace(os.sep, "/")


for cf in glob.glob(os.path.join(SRC, "**", "*.xmi"), recursive=True):
    base = os.path.basename(cf)
    if base == "plugin.xmi" or base == "library.xmi":
        continue
    if os.sep + "configurations" + os.sep in cf:
        continue
    root = parse(cf)
    if root is None:
        continue
    sp = rel_source(cf)
    cdir = os.path.dirname(cf)
    for el in root.iter():
        if not lname(el.tag).endswith("Description"):
            continue
        a = local_attrs(el)
        gid = a.get("guid") or a.get("id")
        if not gid:
            continue
        fields = {}
        attachments = []
        for c in el:
            cln = lname(c.tag)
            if cln == "attachments":
                txt = (c.text or "").strip()
                if txt:
                    attachments.append(txt)
            elif cln in STRUCTURAL:
                continue
            elif cln in FIELD_LABELS:
                v = inner_html(c)
                if v:
                    fields[cln] = v
        sections = extract_sections(el)
        if not (fields or sections or attachments):
            continue
        att = []
        for ap in attachments:
            full = os.path.normpath(os.path.join(cdir, ap))
            ext = os.path.splitext(ap)[1].lower().lstrip(".")
            att.append({"path": rel_source(full), "filename": os.path.basename(ap), "ext": ext})
        content_by_guid[gid] = {
            "fields": fields,
            "sections": sections,
            "attachments": att,
            "source_path": sp,
        }

print(f"content objects indexed: {len(content_by_guid)}")


def compose_body(fields):
    parts = []
    used = set()
    for name in FIELD_NAMES:
        if name in fields and name not in used:
            used.add(name)
            label = FIELD_LABELS[name]
            parts.append(f'<section class="field field-{name}"><h3>{html.escape(label)}</h3>{fields[name]}</section>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3. Walk contentElements in every plugin.xmi -> nodes + edges
# ---------------------------------------------------------------------------
nodes = {}     # guid -> node
edges = []
copyright_refs = {}  # node guid -> copyright statement element guid


def add_edge(frm, to, typ, variability=False):
    if frm and to:
        edges.append({"from_guid": frm, "to_guid": to, "type": typ, "variability": variability})


def handle_element(el, pdir):
    a = local_attrs(el)
    gid = a.get("guid") or a.get("id")
    if not gid:
        return
    etype = (a.get("type") or "").rsplit(":", 1)[-1] or "Unknown"
    variability_type = a.get("variabilityType")

    content_guid = None
    cp_guid = None
    # child references
    for c in el:
        cln = lname(c.tag)
        ca = local_attrs(c)
        href_g = frag(ca.get("href"))
        if cln == "presentation":
            content_guid = href_g or ca.get("id")
        elif cln == "variabilityBasedOnElement":
            if href_g:
                add_edge(gid, href_g, variability_type or "variability", True)
        elif cln == "copyrightStatement":
            cp_guid = href_g
        elif href_g:
            add_edge(gid, href_g, cln, False)
    # attribute references
    for an, v in a.items():
        if an in DATA_ATTRS:
            continue
        if an == "variabilityBasedOnElement":
            add_edge(gid, v.split()[0], variability_type or "variability", True)
            continue
        if is_guidlist(v):
            for t in v.split():
                add_edge(gid, t, an, False)

    if cp_guid:
        copyright_refs[gid] = cp_guid

    # body / sections / source
    body_html, sections, source_path, attachments, has_content = "", [], None, [], False
    cont = content_by_guid.get(content_guid) if content_guid else None
    if cont:
        body_html = compose_body(cont["fields"])
        sections = cont["sections"]
        source_path = cont["source_path"]
        attachments = cont["attachments"]
        has_content = True
    if source_path is None:
        uri = resmap.get(pdir, {}).get(content_guid) if content_guid else None
        source_path = (SRC_PREFIX + "/" + pdir + "/" + uri) if uri else (SRC_PREFIX + "/" + pdir + "/plugin.xmi")

    node = {
        "guid": gid,
        "name": a.get("name", ""),
        "presentation_name": a.get("presentationName", a.get("name", "")),
        "type": etype,
        "plugin": pdir,
        "body_html": body_html,
        "sections": sections,
        "source_path": source_path,
        "content_guid": content_guid,
        "brief_description": a.get("briefDescription", ""),
        "variability_type": variability_type,
        "has_content": has_content,
        "attachments": attachments,
        "license": CONTENT_LICENSE,
        "copyright_statement": cp_guid,
    }
    # don't clobber a content-bearing node with a later content-free duplicate guid
    if gid in nodes:
        if not nodes[gid]["has_content"] and has_content:
            nodes[gid] = node
    else:
        nodes[gid] = node


for pf in sorted(glob.glob(os.path.join(SRC, "*", "plugin.xmi"))):
    pdir = os.path.basename(os.path.dirname(pf))
    root = parse(pf)
    if root is None:
        continue
    for el in root.iter():
        if lname(el.tag) == "contentElements":
            handle_element(el, pdir)

print(f"contentElement nodes: {len(nodes)}")

# ---------------------------------------------------------------------------
# 4. Process nodes: CapabilityPattern / DeliveryProcess from per-pattern model.xmi
# ---------------------------------------------------------------------------
proc_added = 0
for mf in glob.glob(os.path.join(SRC, "*", "capabilitypatterns", "*", "model.xmi")) + \
          glob.glob(os.path.join(SRC, "*", "deliveryprocesses", "*", "model.xmi")):
    pdir = os.path.relpath(mf, SRC).split(os.sep)[0]
    root = parse(mf)
    if root is None:
        continue
    rm = {}
    for el in root.iter():
        if lname(el.tag) == "resourceDescriptors":
            a = local_attrs(el)
            if a.get("id") and a.get("uri"):
                rm[a["id"]] = a["uri"]
    primary_proc = None
    for el in root.iter():
        a = local_attrs(el)
        etype = (a.get("type") or "").rsplit(":", 1)[-1]
        if etype not in PROCESS_TYPES:
            continue
        gid = a.get("guid") or a.get("id")
        if not gid or gid in nodes:
            if gid and primary_proc is None:
                primary_proc = gid
            continue
        if primary_proc is None:
            primary_proc = gid
        # presentation -> content object in this pattern's content.xmi
        content_guid = None
        for c in el:
            if lname(c.tag) == "presentation":
                content_guid = frag(local_attrs(c).get("href")) or local_attrs(c).get("id")
        cont = content_by_guid.get(content_guid) if content_guid else None
        # edges: descriptor refs to real tasks/roles/work products used by this process
        seen = set()
        for d in el.iter():
            dln = lname(d.tag)
            if dln in ("task", "role", "workProduct"):
                tg = frag(local_attrs(d).get("href"))
                if tg and (gid, tg, dln) not in seen:
                    seen.add((gid, tg, dln))
                    add_edge(gid, tg, "uses_" + dln, False)
        mdir = os.path.dirname(mf)
        src = (SRC_PREFIX + "/" + os.path.relpath(mdir, SRC).replace(os.sep, "/") + "/" +
               (rm.get(content_guid) or "model.xmi"))
        nodes[gid] = {
            "guid": gid,
            "name": a.get("name", ""),
            "presentation_name": a.get("presentationName", a.get("name", "")),
            "type": etype,
            "plugin": pdir,
            "body_html": compose_body(cont["fields"]) if cont else "",
            "sections": cont["sections"] if cont else [],
            "source_path": src,
            "content_guid": content_guid,
            "brief_description": a.get("briefDescription", ""),
            "variability_type": a.get("variabilityType"),
            "has_content": bool(cont),
            "attachments": cont["attachments"] if cont else [],
            "license": CONTENT_LICENSE,
            "copyright_statement": None,
        }
        proc_added += 1

    # model-level UMA variability: Activities/Iterations that extend or
    # contribute to capability patterns — attribute to the primary process node
    if primary_proc:
        for el in root.iter():
            a = local_attrs(el)
            vt = a.get("variabilityType")
            if not vt:
                continue
            base = None
            for c in el:
                if lname(c.tag) == "variabilityBasedOnElement":
                    base = frag(local_attrs(c).get("href"))
            if not base and a.get("variabilityBasedOnElement"):
                base = a["variabilityBasedOnElement"].split()[0]
            if base:
                add_edge(primary_proc, base, vt, True)

print(f"process nodes added: {proc_added}")

# ---------------------------------------------------------------------------
# 5. Resource extraction: .dot Word templates -> strings-style outline
# ---------------------------------------------------------------------------
def extract_dot(path):
    try:
        data = open(path, "rb").read()
    except Exception:
        return None
    runs = []
    for enc, pat in (("latin-1", rb"[\x20-\x7e]{4,}"),):
        for m in re.finditer(pat, data):
            try:
                s = m.group().decode(enc, "ignore").strip()
            except Exception:
                continue
            runs.append(s)
    # also pull UTF-16LE text (Word stores text as UTF-16)
    try:
        u = data.decode("utf-16-le", "ignore")
        for s in re.findall(r"[ -~]{4,}", u):
            runs.append(s.strip())
    except Exception:
        pass
    out, seen = [], set()
    noise = re.compile(r"(Microsoft|Word\.Document|MSWordDoc|Root Entry|WordDocument|"
                       r"SummaryInformation|ObjectPool|CompObj|Times New Roman|Arial|"
                       r"Normal\.dot|Symbol|\\[a-z]|MERGEFORMAT|FORMTEXT|FORMCHECKBOX|"
                       r"PAGEREF|STYLEREF|HYPERLINK|\bTOC\b|\bSEQ\b|bjbj|Hlt\d|\\\*|\\@|"
                       r"_PID_|DocumentSummary|MsoNormal|Default Paragraph)", re.I)
    for s in runs:
        s = s.strip()
        if len(s) < 4 or len(s) > 200:
            continue
        if not re.search(r"[A-Za-z]{3,}", s):
            continue
        if noise.search(s):
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[:120] if out else None


resources_extracted = 0
for node in nodes.values():
    for att in node.get("attachments", []):
        if att["ext"] == "dot":
            full = os.path.join(ROOT, att["path"])
            lines = extract_dot(full)
            att["extracted"] = lines
            if lines:
                resources_extracted += 1
        else:
            att["extracted"] = None  # .pdf/.ppt/.xls -> download link only

print(f"template .dot resources with extracted outline: {resources_extracted}")

# ---------------------------------------------------------------------------
# 6. Configurations
# ---------------------------------------------------------------------------
configurations = []
for cfgf in sorted(glob.glob(os.path.join(SRC, "configurations", "*.xmi"))):
    root = parse(cfgf)
    if root is None:
        continue
    a = local_attrs(root)
    sel = []
    for el in root.iter():
        if lname(el.tag) == "methodPluginSelection":
            g = frag(local_attrs(el).get("href"))
            d = plugin_guid_to_dir.get(g)
            if d and d not in sel:
                sel.append(d)
    configurations.append({
        "guid": a.get("guid") or a.get("id"),
        "name": a.get("name", ""),
        "presentation_name": a.get("presentationName", a.get("name", "")),
        "brief_description": a.get("briefDescription", ""),
        "plugins": sel,
        "source_path": rel_source(cfgf),
    })
print(f"configurations: {[(c['name'], len(c['plugins'])) for c in configurations]}")

# ---------------------------------------------------------------------------
# 7. Counts + meta, then emit
# ---------------------------------------------------------------------------
node_list = list(nodes.values())
by_type, by_type_pub, by_plugin = {}, {}, {}
for n in node_list:
    by_type[n["type"]] = by_type.get(n["type"], 0) + 1
    if n["has_content"]:
        by_type_pub[n["type"]] = by_type_pub.get(n["type"], 0) + 1
    by_plugin[n["plugin"]] = by_plugin.get(n["plugin"], 0) + 1

node_guids = set(nodes.keys())
unresolved = sorted({e["to_guid"] for e in edges if e["to_guid"] not in node_guids})
var_edges = [e for e in edges if e["variability"]]

# dedupe edges
seen, dedup = set(), []
for e in edges:
    k = (e["from_guid"], e["to_guid"], e["type"])
    if k not in seen:
        seen.add(k)
        dedup.append(e)
edges = dedup

data = {
    "meta": {
        "title": "EPF Practices method library",
        "provenance": {
            "library": "EPF Practices 1.5.1.5",
            "date": "2012-12-12",
            "archive_item": "epf-2021-11-26",
            "archive_file": "Libraries/epf_practices_library_1.5.1.5_20121212.zip",
        },
        "content_license": CONTENT_LICENSE,
        "content_license_file": "LICENSES/EPL-1.0.txt",
        "copyright_holders": COPYRIGHT_HOLDERS,
        "viewer_license": "MIT",
        "generated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "nodes": len(node_list),
            "edges": len(edges),
            "variability_edges": len(var_edges),
            "unresolved_targets": len(unresolved),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "by_type_published": dict(sorted(by_type_pub.items(), key=lambda x: -x[1])),
            "plugins": len(plugins),
            "configurations": len(configurations),
        },
    },
    "plugins": [plugins[d] for d in sorted(plugins)],
    "configurations": configurations,
    "nodes": node_list,
    "edges": edges,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

# ---------------------------------------------------------------------------
# Verification report
# ---------------------------------------------------------------------------
print("\n================= VERIFICATION =================")
size = os.path.getsize(OUT)
print(f"data/method.json written: {size/1e6:.2f} MB  ({len(node_list)} nodes, {len(edges)} edges)")
print(f"variability edges: {len(var_edges)}  (by type: " +
      ", ".join(f"{t}={sum(1 for e in var_edges if e['type']==t)}"
                for t in sorted({e['type'] for e in var_edges})) + ")")
print("\nNodes by type (total / with-content):")
for t in sorted(by_type, key=lambda x: -by_type[x]):
    print(f"  {t:22} {by_type[t]:4d} / {by_type_pub.get(t,0)}")
print(f"\nNodes by plugin: {len(by_plugin)} plugins")
print(f"\nEdges with unresolved (dead-link) target: "
      f"{sum(1 for e in edges if e['to_guid'] not in node_guids)} "
      f"(distinct targets: {len(unresolved)})")
# integrity: every edge from_guid resolves to a real node
bad_from = [e for e in edges if e["from_guid"] not in node_guids]
print(f"Edges whose from_guid is NOT a real node: {len(bad_from)}  (must be 0)")
# parse-back check
with open(OUT, encoding="utf-8") as f:
    reparsed = json.load(f)
print(f"Re-parse of method.json OK: {len(reparsed['nodes'])} nodes")
print("\nConfigurations:")
for c in configurations:
    incl = sum(1 for n in node_list if n["plugin"] in c["plugins"])
    print(f"  {c['presentation_name']:20} {len(c['plugins'])} plugins, {incl} elements")
print("================================================")
