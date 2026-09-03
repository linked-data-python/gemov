"""HTML for a vocabulary, in the shape `saref-pypeline` gave SAREF.

A page is a title, a summary of what the thing is, and then its definition
broken into sections — sub classes, super classes, in domain of, in range of.
That is pyLODE's shape, which `saref-pypeline` rewrote in its own HTML for
https://saref.etsi.org/, and which is rewritten again here: the sections are
the same, the queries behind them are `_queries.ldpy`, and the output is a
single stylesheet with no framework.

Four kinds of page:

    render_index            the vocabulary: its modules
    render_module           a module: its metadata and its terms
    render_term             a term: its definition and what points at it
    render_pattern          the rule that minted a family of terms

The last has no equivalent in a hand-written ontology, and it is the one a
generator owes its reader: *why* does this family of terms exist, over which
dimensions, at which degree.
"""

import html
import os
import re

from rdflib import URIRef

from .cache import local, short
from .queries import describe, module_contents, ontology_header

STYLE = """
 :root{--ink:#182026;--dim:#5c6b6a;--brand:#0f3d3e;--accent:#116466;
       --rule:#dfe6e5;--soft:#f6f8f8}
 *{box-sizing:border-box}
 body{font:16px/1.55 system-ui,-apple-system,sans-serif;margin:0;color:var(--ink);background:#fff}
 header{background:var(--brand);color:#fff;padding:1.1rem 1.5rem;
        display:flex;align-items:center;gap:1rem}
 header .titles{min-width:0}
 header .mark{flex:0 0 auto;display:block;background:#fff;border-radius:.25rem;
              padding:.35rem .5rem;line-height:0}
 header .mark img{height:2.6rem;width:auto;display:block}
 header a{color:#fff;text-decoration:none}
 header h1{margin:0;font-size:1.25rem;font-weight:600}
 header .meta{color:rgba(255,255,255,.78);font-size:.85rem;margin-top:.25rem}
 main{max-width:58rem;margin:0 auto;padding:1.4rem 1.5rem 3rem}
 h2{font-size:1rem;margin:1.7rem 0 .5rem;color:var(--brand);
    border-bottom:1px solid var(--rule);padding-bottom:.25rem}
 a{color:var(--accent)} code,.t{font-family:ui-monospace,SFMono-Regular,monospace;font-size:.92em}
 ul{margin:.3rem 0;padding-left:1.15rem} li{margin:.12rem 0}
 dl{margin:.4rem 0;display:grid;grid-template-columns:max-content 1fr;gap:.15rem .9rem}
 dt{color:var(--dim);font-size:.85rem} dd{margin:0}
 p.d{white-space:pre-wrap;margin:.5rem 0}
 .d p{margin:.6rem 0} .d img{max-width:100%;height:auto;display:block;
      margin:1rem auto} .d ul{padding-left:1.3rem}
 .d pre{background:var(--soft);border:1px solid var(--rule);padding:.7rem;
        overflow:auto;font-size:.82rem;border-radius:.2rem}
 .d code{background:var(--soft);padding:.05rem .25rem;border-radius:.2rem}
 .d pre code{background:none;padding:0}
 .d blockquote{margin:.6rem 0;padding-left:.8rem;border-left:3px solid var(--rule);color:var(--dim)}
 .cols{display:flex;flex-wrap:wrap;gap:1.6rem} .cols>section{flex:1 1 15rem;min-width:0}
 .pill{display:inline-block;background:var(--soft);border:1px solid var(--rule);
       border-radius:1rem;padding:.02rem .5rem;font-size:.8rem;color:var(--dim)}
 pre{background:var(--soft);border:1px solid var(--rule);padding:.7rem;
     overflow:auto;font-size:.82rem;border-radius:.2rem}
 nav.f{margin-top:2.5rem;font-size:.86rem;color:var(--dim);
       border-top:1px solid var(--rule);padding-top:.7rem}
 section.term{border-top:1px solid var(--rule);padding-top:.9rem;
              margin-top:1.4rem}
 section.term h3{margin:0 0 .2rem;font-size:1.02rem;color:var(--brand)}
 section.term h3 a{color:inherit;text-decoration:none}
 section.term h3 a:hover{text-decoration:underline}
 .tiri{font-size:.8rem;color:var(--dim);margin-bottom:.35rem}
 p.rel{font-size:.85rem;color:var(--dim);margin:.5rem 0 0}
 p.rel span{margin-right:.2rem} p.rel b{color:var(--ink);font-weight:500}
 p.toc{font-size:.85rem;margin:.3rem 0 .2rem;line-height:1.9}
 table{border-collapse:collapse;font-size:.9rem} td,th{text-align:left;
   padding:.2rem .8rem .2rem 0;vertical-align:top} th{color:var(--dim);font-weight:500}
"""


def esc(text):
    return html.escape(str(text))


def _markdown():
    """Python-Markdown, if it is installed.

    The descriptions and comments of a published vocabulary are prose, and
    SEAS has written that prose in **Markdown** since 2016 — links, images,
    bullet lists and fenced Turtle examples, in `dcterms:description` and
    `rdfs:comment`. Rendering it as plain text shows the reader
    `[SSN](http://…)` where the 2016 site showed a link, which is not a
    detail: the examples are the documentation.

    It stays optional. Without it the prose is escaped and shown as it is
    written, which is what this did before."""
    try:
        import markdown
    except ImportError:                                      # pragma: no cover
        return None
    return markdown.Markdown(extensions=["fenced_code", "tables",
                                         "sane_lists", "attr_list"])


_MD = _markdown()


def _localise(html_text, namespace, suffix):
    """Links into the vocabulary's own namespace become links into this site.

    SEAS descriptions write absolute IRIs — `https://w3id.org/seas/SSNAlignment`
    for a module, `https://w3id.org/seas/featureofinterest.png` for a figure —
    and they are right to: an IRI is not a path. But a page *of that
    namespace* that keeps them absolute sends its own reader back out to
    whatever answers there, which is how a preview, a static export or a
    deployment on another host ends up with broken figures.

    A tail that has a file extension is a file and is linked as it is;
    anything else is a term, and takes the site's suffix."""
    if not namespace:
        return html_text

    def relative(match):
        attribute, tail = match.group(1), match.group(2)
        if not tail or tail.startswith(("#", "?")):
            return match.group(0)
        if not os.path.splitext(tail)[1]:
            tail += suffix
        return '%s="%s"' % (attribute, tail)

    return re.sub(r'\b(src|href)="%s([^"]*)"' % re.escape(namespace),
                  relative, html_text)


def prose(texts, namespace=None, suffix=""):
    """One or more Markdown paragraphs, as HTML.

    The content comes from the vocabulary's own source files, which are as
    trusted as the code that renders them; nothing is sanitised beyond what
    Markdown does, and a vocabulary you would not run is a vocabulary you
    would not serve either."""
    if isinstance(texts, str):
        texts = [texts]
    out = []
    for text in texts:
        text = (text or "").strip()
        if not text:
            continue
        if _MD is None:
            out.append('<p class="d">%s</p>' % esc(text))
        else:
            _MD.reset()
            out.append('<div class="d">%s</div>'
                       % _localise(_MD.convert(text), namespace, suffix))
    return "".join(out)


def _brand_style(brand):
    """Only the two colours a logo can clash with are overridable."""
    if not brand or not (brand.ink or brand.accent):
        return ""
    rules = []
    if brand.ink:
        rules.append("--brand:%s" % brand.ink)
    if brand.accent:
        rules.append("--accent:%s" % brand.accent)
    return ":root{%s}\n" % ";".join(rules)


def _brand_mark(brand):
    """The logo, in the header, linking to the project it belongs to."""
    if not brand or not brand.logo:
        return ""
    img = '<img src="%s" alt="%s">' % (esc(brand.logo), esc(brand.name))
    if brand.home:
        img = '<a class="mark" href="%s">%s</a>' % (esc(brand.home), img)
    else:
        img = '<span class="mark">%s</span>' % img
    return img


def page(title, subtitle, body, home="index.html", brand=None):
    note = ""
    if brand and brand.note:
        note = "<br>%s" % esc(brand.note)
    # The browser tab says which vocabulary this is; the heading says which
    # page of it.
    document_title = ("%s · %s" % (title, brand.name)
                      if brand and brand.name else title)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="gemov">
<title>%s</title><style>%s%s</style></head><body>
<header>%s<div class="titles"><h1><a href="%s">%s</a></h1>%s</div></header>
<main>%s<nav class="f">Generated by <code>gemov</code>. Every page is also RDF:
append <code>.ttl</code>, <code>.rdf</code>, <code>.jsonld</code> or
<code>.nt</code>, or send an <code>Accept</code> header.%s</nav></main>
</body></html>""" % (esc(document_title), STYLE, _brand_style(brand),
                     _brand_mark(brand), home, esc(title),
                     '<div class="meta">%s</div>' % subtitle if subtitle else "",
                     body, note)


def _links(iris, namespace, prefix, suffix=".html"):
    if not iris:
        return '<span class="pill">none</span>'
    return "<ul>%s</ul>" % "".join(
        '<li><a class="t" href="%s%s">%s</a></li>'
        % (esc(local(i, namespace)), suffix, esc(short(i, namespace, prefix)))
        if i.startswith(namespace) else '<li><code>%s</code></li>' % esc(i)
        for i in iris)


def _dl(pairs):
    rows = "".join("<dt>%s</dt><dd>%s</dd>" % (esc(k), v)
                   for k, v in pairs if v)
    return "<dl>%s</dl>" % rows if rows else ""


# ------------------------------------------------------------------ pages

def render_term(graph, iri, namespace, prefix="", home_label=None,
                suffix=".html", brand=None):
    data = describe(graph, iri)
    title = data["labels"][0] if data["labels"] else local(iri, namespace)
    body = []
    if data["comments"]:
        body.append(prose(data["comments"], namespace, suffix))
    body.append(_dl([
        ("IRI", "<code>%s</code>" % esc(iri)),
        ("Type", ", ".join('<span class="pill">%s</span>'
                           % esc(short(k, namespace, prefix))
                           for k in data["kinds"])),
        ("Preferred label", ", ".join(esc(p) for p in data["preferred"])),
        ("Status", '<span class="pill">%s</span>' % esc(data["status"])
         if data["status"] else ""),
        ("Defined by", _links(data["defined_by"], namespace, prefix, suffix)),
    ]))
    sections = [("Sub class of", data["parents"]),
                ("Equivalent to", data["equivalents"]),
                ("Sub classes", data["children"]),
                ("In the domain of", data["domain_of"]),
                ("In the range of", data["range_of"]),
                ("Sub properties", data["sub_properties"])]
    shown = [(t, v) for t, v in sections if v]
    if shown:
        body.append('<div class="cols">%s</div>' % "".join(
            "<section><h2>%s</h2>%s</section>"
            % (t, _links(v, namespace, prefix, suffix)) for t, v in shown))
    return page(title, "<code>%s</code>%s" % (esc(iri),
                                              " · " + esc(home_label)
                                              if home_label else ""),
                "".join(body), home="index" + suffix, brand=brand)


#: How the terms of a module are laid out on its page.
#:
#: `kind` reproduces the 2016 site: Classes, then Object properties, then the
#: rest, alphabetically within each. It is easy to scan and it is what a
#: reader of the published SEAS is used to.
#:
#: `source` follows the order the terms were written in — or, for a generated
#: vocabulary, minted in. It keeps a family together:
#: `GenericPropertyOntology` writes `TemperatureProperty`,
#: `TemperatureEvaluation` and `temperature` one after the other, and `kind`
#: scatters those three across two sections and eleven screens.
ORDERS = ("kind", "source")


def _kind(iri):
    """`owl:Class` reads as *Class*.

    A term's types come from OWL and RDFS, not from the vocabulary's own
    namespace, so `short()` — which compacts what is inside the namespace —
    leaves them as full IRIs. The last segment is the name in every
    vocabulary that names its types at all, and it is what a reader wants to
    see on a badge."""
    tail = iri.rstrip("/").rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return tail or iri


def _term_block(graph, iri, namespace, prefix, suffix):
    """A term's documentation, inline in its module's page."""
    data = describe(graph, iri)
    name = local(iri, namespace)
    label = data["labels"][0] if data["labels"] else name
    kinds = " ".join('<span class="pill">%s</span>' % esc(_kind(k))
                     for k in sorted(data["kinds"]))
    rows = []
    for title, key in (("sub class of", "parents"),
                       ("equivalent to", "equivalents"),
                       ("sub property of", "sub_of"),
                       ("domain", "domain"), ("range", "range"),
                       ("sub classes", "children"),
                       ("domain of", "domain_of"),
                       ("range of", "range_of"),
                       ("sub properties", "sub_properties")):
        values = data.get(key)
        if values:
            rows.append("<span><b>%s</b> %s</span>" % (
                title, ", ".join(
                    '<a class="t" href="%s%s">%s</a>'
                    % (esc(local(v, namespace)), suffix,
                       esc(short(v, namespace, prefix)))
                    if v.startswith(namespace) else "<code>%s</code>" % esc(v)
                    for v in values)))
    return ('<section class="term" id="%s"><h3><a href="%s%s">%s</a> %s</h3>'
            '<div class="tiri"><code>%s</code></div>%s%s</section>'
            % (esc(name), esc(name), suffix, esc(label), kinds, esc(iri),
               prose(data["comments"], namespace, suffix),
               '<p class="rel">%s</p>' % " · ".join(rows) if rows else ""))


def _module_terms(module_version, contents, namespace, prefix, suffix, order):
    """Every term the module defines, documented, in the asked-for order."""
    graph = module_version.graph
    if order == "source":
        positions = module_version.declaration_order()
        everything = (contents["classes"] + contents["properties"]
                      + contents["other"])
        groups = [("Terms", sorted(
            everything,
            key=lambda i: (positions.get(URIRef(i), (9, 9e9)), i)))]
    else:
        groups = [(label, contents[key]) for label, key in
                  (("Classes", "classes"), ("Properties", "properties"),
                   ("Other terms", "other"))]
    out = []
    for label, terms in groups:
        if not terms:
            continue
        out.append("<h2>%s (%d)</h2>" % (label, len(terms)))
        out.append('<p class="toc">%s</p>' % " · ".join(
            '<a class="t" href="#%s">%s</a>'
            % (esc(local(i, namespace)), esc(short(i, namespace, prefix)))
            for i in terms))
        out.extend(_term_block(graph, i, namespace, prefix, suffix)
                   for i in terms)
    return "".join(out)


def render_module(module_version, namespace, prefix="", versions=(),
                  patterns=(), suffix=".html", brand=None, order="kind"):
    graph = module_version.graph
    header = ontology_header(graph, module_version.iri)
    contents = module_contents(graph, module_version.iri)
    title = header["titles"][0] if header["titles"] else module_version.module
    body = []
    if header["descriptions"]:
        body.append(prose(header["descriptions"], namespace, suffix))
    body.append(_dl([
        ("IRI", "<code>%s</code>" % esc(module_version.iri)),
        ("Version", esc(module_version.version)),
        ("Versions", " · ".join('<a href="%s-%s%s">%s</a>'
                                % (esc(module_version.module), esc(v), suffix,
                                   esc(v)) for v in versions)),
        ("Issued", ", ".join(esc(i) for i in header["issued"])),
        ("Imports", _links(header["imports"], namespace, prefix, suffix)),
        ("Terms", "%d classes, %d properties, %d other"
         % (len(contents["classes"]), len(contents["properties"]),
            len(contents["other"]))),
    ]))
    if patterns:
        body.append("<h2>Generated by</h2>%s" % "<ul>%s</ul>" % "".join(
            '<li><a href="pattern-%s%s">%s</a> '
            '<span class="pill">degree %d</span></li>'
            % (esc(p["name"]), suffix, esc(p["name"]), p["degree"])
            for p in patterns))
    body.append(_module_terms(module_version, contents, namespace, prefix,
                              suffix, order))
    return page(title, "<code>%s</code> · version %s"
                % (esc(module_version.iri), esc(module_version.version)),
                "".join(body), home="index" + suffix, brand=brand)


def render_index(source, prefix="", patterns=(), suffix=".html", brand=None):
    body = ["<h2>Modules (%d)</h2><ul>%s</ul>"
            % (len(source.modules()), "".join(
                '<li><a class="t" href="%s%s">%s</a> '
                '<span class="pill">%s</span></li>'
                % (esc(m), suffix, esc(m),
                   esc(" · ".join(source.module_versions(m))))
                for m in source.modules()))]
    if source.dimensions:
        body.append("<h2>Dimensions (%d)</h2><table>%s</table>"
                    % (len(source.dimensions), "".join(
                        "<tr><th>%s</th><td>%d items — %s</td></tr>"
                        % (esc(name), len(items),
                           esc(", ".join(sorted(items)[:8]) +
                               (" …" if len(items) > 8 else "")))
                        for name, items in sorted(source.dimensions.items()))))
    if patterns:
        body.append('<h2>Patterns (%d)</h2><p>The rules that minted the terms: '
                    '<a href="patterns%s">the list</a>.</p>'
                    % (len(patterns), suffix))
    return page(brand.name if brand and brand.name else "Vocabulary",
                "one namespace, modular and versioned",
                "".join(body), home="index" + suffix, brand=brand)


# ------------------------------------------------- the reflexive pages

def pattern_facts(context, config):
    """What is known about each pattern: where it is, its degree, the roles of
    its dimensions, the module it mints into, and what it minted."""
    out = []
    for fn, module in sorted(context.home.items(), key=lambda kv: kv[0].__name__):
        roles = context.roles.get(fn, {})
        minted = [str(t) for t in context.minted.get(module, [])]
        out.append({
            "name": fn.__name__,
            "module": module,
            "degree": len(roles),
            "roles": roles,
            "doc": (fn.__doc__ or "").strip(),
            "source": getattr(fn, "__module__", ""),
            "minted": sorted(minted),
        })
    return out


def render_pattern(fact, namespace, prefix="", suffix=".html", brand=None):
    body = []
    if fact["doc"]:
        body.append(prose(fact["doc"]))
    body.append(_dl([
        ("Defined in", "<code>%s</code>" % esc(fact["source"])),
        ("Mints into", '<a href="%s%s">%s</a>'
         % (esc(fact["module"]), suffix, esc(fact["module"]))),
        ("Degree", '<span class="pill">%d</span> — %s'
         % (fact["degree"],
            "independent of the dimensions" if not fact["degree"]
            else "one term family per %s"
            % " × ".join(fact["roles"].values()))),
        ("Roles", "<table>%s</table>" % "".join(
            "<tr><th>%s</th><td>dimension <code>%s</code></td></tr>"
            % (esc(role), esc(dim)) for role, dim in fact["roles"].items())
         if fact["roles"] else ""),
    ]))
    body.append("<h2>Terms of its module (%d)</h2>%s"
                % (len(fact["minted"]),
                   _links(fact["minted"][:60], namespace, prefix, suffix)))
    return page("Pattern %s" % fact["name"],
                "a rule, not a term — degree %d" % fact["degree"],
                "".join(body), home="index" + suffix, brand=brand)


def render_patterns_index(facts, suffix=".html", brand=None):
    rows = "".join(
        '<tr><th><a href="pattern-%s%s">%s</a></th><td>%d</td>'
        '<td>%s</td><td><a href="%s%s">%s</a></td></tr>'
        % (esc(f["name"]), suffix, esc(f["name"]), f["degree"],
           esc(", ".join("%s: %s" % (r, d) for r, d in f["roles"].items()) or "—"),
           esc(f["module"]), suffix, esc(f["module"]))
        for f in facts)
    return page("Patterns", "the rules that minted this vocabulary",
                "<table><tr><th>pattern</th><th>degree</th><th>roles</th>"
                "<th>module</th></tr>%s</table>" % rows,
                home="index" + suffix, brand=brand)


# ------------------------------------------------------------ static site

def write_site(source, directory, prefix="", config=None, brand=None,
               order="kind"):
    """Write the whole documentation as files — what `saref-pypeline` does for
    SAREF. Returns the list of paths written."""
    os.makedirs(directory, exist_ok=True)
    written = []
    namespace = source.namespace
    facts = []
    if config is not None and hasattr(source, "context"):
        facts = pattern_facts(source.context, config)

    def put(name, text):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        written.append(path)

    put("index.html", render_index(source, prefix, facts, brand=brand))
    for module in source.modules():
        versions = source.module_versions(module)
        for version in versions:
            mv = source.versions[module][version]
            module_patterns = [f for f in facts if f["module"] == module]
            html_text = render_module(mv, namespace, prefix, versions,
                                      module_patterns, brand=brand,
                                      order=order)
            put("%s-%s.html" % (module, version), html_text)
            if version == versions[-1]:
                put("%s.html" % module, html_text)
    for iri, homes in sorted(source.index_terms().items(), key=lambda kv: str(kv[0])):
        home = homes[-1]
        put("%s.html" % local(str(iri), namespace),
            render_term(home.graph, str(iri), namespace, prefix, str(home),
                        brand=brand))
    if facts:
        put("patterns.html", render_patterns_index(facts, brand=brand))
        for fact in facts:
            put("pattern-%s.html" % fact["name"],
                render_pattern(fact, namespace, prefix, brand=brand))
    return written
