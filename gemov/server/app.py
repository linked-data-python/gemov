"""Serving a vocabulary: one namespace, modular and versioned.

    gemov serve --files src/main/ontop/1.0 --namespace https://w3id.org/seas/
    gemov serve --config vocabulary.yml

The source is either a directory of `Module-x.y.ttl` files or a gemov
configuration (see `source.py`); the contract is the same either way.

**The access contract is documented in `docs/server.md`**, and every clause of
it is a test in `tests/test_server.py`. It is not restated here: two copies of
a contract are one contract and one lie.
"""

import os

from flask import Blueprint, Flask, Response, abort, current_app, redirect, \
    request, send_from_directory, url_for

from . import views
from .source import Files, Generated
from ..doc import Cache, render_index, render_module, render_term
from ..doc.cache import local, short
from ..doc.render import esc, page, pattern_facts, render_pattern, \
    render_patterns_index

#: media type -> (rdflib serialisation, file extension)
RDF_TYPES = {
    "text/turtle": ("turtle", "ttl"),
    "application/rdf+xml": ("xml", "rdf"),
    "application/ld+json": ("json-ld", "jsonld"),
    "application/n-triples": ("nt", "nt"),
    "text/n3": ("n3", "n3"),
}
EXTENSIONS = {ext: media for media, (_, ext) in RDF_TYPES.items()}
EXTENSIONS["html"] = "text/html"

#: Routes are registered on a blueprint, and an application is built per
#: source: a library must not hold a global app, and two vocabularies must be
#: servable in one process — which is also what makes the tests independent.
bp = Blueprint("gemov", __name__)


def _source():
    return current_app.config["SOURCE"]


def _prefix():
    return current_app.config["PREFIX"]


def _cache():
    return current_app.config["CACHE"]


def _brand():
    return current_app.config["BRAND"]


def _order():
    return current_app.config["ORDER"]


def _home():
    """The URL of the index, whatever the site is mounted under.

    `url_for` folds in both the blueprint's `url_prefix` and the WSGI
    `SCRIPT_NAME`, so a site mounted at `/seas/` — directly or behind a
    reverse proxy — links to itself and not to the server's root."""
    return url_for("gemov.index")


# --------------------------------------------------------------- negotiation

def wanted(path):
    """(bare path, media type). An extension wins over `Accept`."""
    base, dot, ext = path.rpartition(".")
    if dot and ext in EXTENSIONS:
        return base, EXTENSIONS[ext]
    offers = list(RDF_TYPES) + ["text/html"]
    return path, request.accept_mimetypes.best_match(offers,
                                                     default=None) or "text/html"


def rdf_response(graph, media, location=None):
    response = Response(graph.serialize(format=RDF_TYPES[media][0]),
                        mimetype=media)
    response.headers["Vary"] = "Accept"
    if location:
        response.headers["Content-Location"] = location
    return response


def html_response(body, etag=None, location=None):
    response = Response(body, mimetype="text/html")
    response.headers["Vary"] = "Accept"
    if etag:
        response.headers["ETag"] = etag
    if location:
        response.headers["Content-Location"] = location
    return response


def not_modified(etag):
    return etag and etag in (request.headers.get("If-None-Match") or "")


def _facts():
    source, config = _source(), current_app.config["CONFIG"]
    if config is None or not hasattr(source, "context"):
        return []
    return pattern_facts(source.context, config)


def _linked(page_body):
    """The pages are written for a static site (`x.html`); served live, the
    paths have no extension.

    Every other link stays **relative**, which is what lets the same page be
    correct at `/EndNode` and at `/seas/EndNode`: a relative `href="Foo"`
    resolves against the directory of the current URL either way.  Only the
    link to the index cannot be relative, and it is the one resolved here."""
    return page_body.replace('.html"', '"').replace(
        'href="index"', 'href="%s"' % _home())


# ------------------------------------------------------------------- routes

@bp.route("/")
def index():
    source = _source()
    _, media = wanted("")
    if media in RDF_TYPES:
        graph, _ = views.build(source, modules=source.modules())
        return rdf_response(graph, media)
    body, etag = _cache().get_or_build(
        ("index",), _stamp(),
        lambda: _linked(render_index(source, _prefix(), _facts(),
                                     brand=_brand())))
    if not_modified(etag):
        return Response(status=304)
    return html_response(body, etag=etag)


@bp.route("/patterns")
def patterns():
    facts = _facts()
    if not facts:
        abort(404, "this vocabulary is not generated from patterns")
    return html_response(_linked(render_patterns_index(facts,
                                                      brand=_brand())))


@bp.route("/pattern-<name>")
def pattern(name):
    for fact in _facts():
        if fact["name"] == name:
            return html_response(_linked(render_pattern(
                fact, _source().namespace, _prefix(), brand=_brand())))
    abort(404)


@bp.route("/view")
def view():
    source = _source()
    modules = request.args.getlist("module")
    terms = request.args.getlist("term") + request.args.getlist("element")
    selection = {}
    for pair in request.args.getlist("dimension"):
        name, _, items = pair.partition("=")
        if items:
            selection.setdefault(name, []).extend(items.split(","))
    for name in source.dimensions:
        if request.args.get(name):
            selection.setdefault(name, []).extend(
                request.args.get(name).split(","))
    if not modules and not terms and not selection:
        abort(400, "name at least one module=, term= or dimension=")
    if selection and not hasattr(source, "config"):
        abort(400, "this vocabulary is not generated: dimensions cannot be "
                   "selected, name modules or terms instead")
    graph, report = views.build(source, modules, terms, selection or None,
                                request.args.get("closure", "").lower()
                                in ("1", "true", "yes"))
    _, media = wanted(request.path)
    if media in RDF_TYPES:
        return rdf_response(graph, media)
    ns, prefix = source.namespace, _prefix()
    rows = ['<dl><dt>Triples</dt><dd>%d</dd>'
            '<dt>Modules</dt><dd>%s</dd><dt>Terms</dt><dd>%s</dd>'
            '<dt>Dimensions</dt><dd>%s</dd>'
            '<dt>Closure</dt><dd>%d term(s)</dd></dl>'
            % (report["triples"], esc(", ".join(report["modules"]) or "—"),
               esc(", ".join(short(t, ns, prefix) for t in report["terms"])
                   or "—"),
               esc(", ".join("%s = %s" % (k, ", ".join(v))
                             for k, v in report["selection"].items()) or "—"),
               len(report["closure"]))]
    if report["unknown"]:
        rows.append("<h2>Not found</h2><p>%s</p>"
                    % esc(", ".join(report["unknown"])))
    if report["closure"]:
        rows.append("<h2>Pulled in to close the view</h2><ul>%s</ul>"
                    % "".join('<li><a href="%s%s">%s</a></li>'
                              % (esc(_home()), esc(local(t, ns)),
                                 esc(short(t, ns, prefix)))
                              for t in sorted(report["closure"])))
    rows.append("<h2>The graph</h2><pre>%s</pre>"
                % esc(graph.serialize(format="turtle")))
    return html_response(page("View", "assembled on demand", "".join(rows),
                              home=_home(), brand=_brand()))


@bp.route("/cache")
def cache_stats():
    return dict(_cache().stats())


@bp.route("/static/<path:filename>")
def asset(filename):
    """A logo, and whatever else a brand needs.

    Served by the blueprint rather than by Flask's own static folder so that
    it lands under the mount point with everything else: at `/seas/`, the
    pages ask for the relative `static/logo.png` and get
    `/seas/static/logo.png`."""
    directory = current_app.config["ASSETS"]
    if not directory:
        abort(404)
    return send_from_directory(directory, filename)


@bp.route("/<path:name>")
def resource(name):
    source = _source()
    bare, media = wanted(name)

    module, _, version = bare.rpartition("-")
    if module and source.is_module(module):
        exact = source.versions[module].get(version)
        if exact is None:
            resolved = source.resolve_version(module, version)
            if resolved is None:
                abort(404)
            return redirect(url_for("gemov.resource",
                                    name="%s-%s" % (module, resolved.version)),
                            code=302)
        return _serve_module(exact, media, canonical=True)

    if source.is_module(bare):
        return _serve_module(source.latest(bare), media, canonical=False)

    # A file under the namespace, from the assets directory. SEAS descriptions
    # point at `https://w3id.org/seas/featureofinterest.png`, and that URL is
    # this server's to answer: the 2016 site served those figures at exactly
    # those IRIs, and a documentation whose figures 404 is a documentation
    # with holes in it. Checked after the modules so a module always wins.
    served = _serve_asset(name)
    if served is not None:
        return served

    return _serve_term(source.namespace + bare, media)


def _serve_asset(name):
    """The asset of that name, if the deployment has one."""
    directory = current_app.config["ASSETS"]
    if not directory or not os.path.splitext(name)[1]:
        return None
    path = os.path.normpath(os.path.join(directory, name))
    if not path.startswith(directory + os.sep) or not os.path.isfile(path):
        return None
    return send_from_directory(directory, name)


def _stamp():
    source = _source()
    return tuple(sorted(mv.stamp() for versions in source.versions.values()
                        for mv in versions.values()))


def _serve_module(module_version, media, canonical):
    source = _source()
    location = None if canonical else url_for(
        "gemov.resource", name="%s-%s" % (module_version.module,
                                          module_version.version))
    if media in RDF_TYPES:
        return rdf_response(module_version.graph, media, location=location)
    facts = [f for f in _facts() if f["module"] == module_version.module]
    body, etag = _cache().get_or_build(
        # the order is part of the key: the same module laid out two ways is
        # two pages, and a cache that forgot it would serve the wrong one
        ("module", module_version.module, module_version.version, _order()),
        module_version.stamp(),
        lambda: _linked(render_module(
            module_version, source.namespace, _prefix(),
            source.module_versions(module_version.module), facts,
            brand=_brand(), order=_order())))
    if not_modified(etag):
        return Response(status=304)
    return html_response(body, etag=etag, location=location)


def _serve_term(iri, media):
    source = _source()
    definition, home = source.term_definition(iri)
    if definition is None:
        abort(404)
    if media in RDF_TYPES:
        return rdf_response(definition, media, location=url_for(
            "gemov.resource",
            name="%s-%s" % (home.module, home.version)))
    body, etag = _cache().get_or_build(
        ("term", iri), home.stamp(),
        lambda: _linked(render_term(home.graph, iri, source.namespace,
                                    _prefix(), str(home), brand=_brand())))
    if not_modified(etag):
        return Response(status=304)
    return html_response(body, etag=etag)


# -------------------------------------------------------------------- setup

def build_app(source, prefix="", config=None, mount="", brand=None,
              assets=None, order="kind"):
    """A Flask application serving one source.

    ``mount`` is the path the vocabulary is served under — ``/seas`` puts the
    index at ``/seas/`` and a term at ``/seas/EndNode``.  It is a deployment
    decision, not a property of the vocabulary: the same files served at the
    root and under a context path must produce the same pages, which is why
    every link a page carries is relative and the few that cannot be go
    through ``url_for``.
    """
    # `static_folder=None`: the assets are the deployment's, served by the
    # blueprint so they land under the mount point. Flask's own `/static/`
    # route would otherwise shadow it whenever the mount is the root.
    application = Flask(__name__, static_folder=None)
    application.config.update(SOURCE=source, PREFIX=prefix, CONFIG=config,
                              CACHE=Cache(), BRAND=brand, ORDER=order,
                              ASSETS=os.path.abspath(assets)
                              if assets else None)
    application.register_blueprint(
        bp, url_prefix=("/" + mount.strip("/")) if mount.strip("/") else None)
    return application


def from_files(directories, namespace, prefix="", mount="", brand=None,
               assets=None, order="kind"):
    return build_app(Files(directories, namespace), prefix, mount=mount,
                     brand=brand, assets=assets, order=order)


def from_config(config, prefix="", version="1.0", mount="", brand=None,
                assets=None, order="kind"):
    return build_app(Generated(config, version), prefix, config, mount=mount,
                     brand=brand, assets=assets, order=order)
