"""Serving a vocabulary: one namespace, modular and versioned.

    gemov serve --files src/main/ontop/1.0 --namespace https://w3id.org/seas/
    gemov serve --config vocabulary.yml

The source is either a directory of `Module-x.y.ttl` files or a gemov
configuration (see `source.py`); the contract is the same either way.

**The access contract is documented in `docs/server.md`**, and every clause of
it is a test in `tests/test_server.py`. It is not restated here: two copies of
a contract are one contract and one lie.
"""

import argparse

from flask import Blueprint, Flask, Response, abort, current_app, redirect, \
    request

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
    paths have no extension."""
    return page_body.replace('.html"', '"').replace('href="index"', 'href="/"')


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
        lambda: _linked(render_index(source, _prefix(), _facts())))
    if not_modified(etag):
        return Response(status=304)
    return html_response(body, etag=etag)


@bp.route("/patterns")
def patterns():
    facts = _facts()
    if not facts:
        abort(404, "this vocabulary is not generated from patterns")
    return html_response(_linked(render_patterns_index(facts)))


@bp.route("/pattern-<name>")
def pattern(name):
    for fact in _facts():
        if fact["name"] == name:
            return html_response(_linked(render_pattern(
                fact, _source().namespace, _prefix())))
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
                    % "".join('<li><a href="/%s">%s</a></li>'
                              % (esc(local(t, ns)), esc(short(t, ns, prefix)))
                              for t in sorted(report["closure"])))
    rows.append("<h2>The graph</h2><pre>%s</pre>"
                % esc(graph.serialize(format="turtle")))
    return html_response(page("View", "assembled on demand", "".join(rows),
                              home="/"))


@bp.route("/cache")
def cache_stats():
    return dict(_cache().stats())


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
            return redirect("/%s-%s" % (module, resolved.version), code=302)
        return _serve_module(exact, media, canonical=True)

    if source.is_module(bare):
        return _serve_module(source.latest(bare), media, canonical=False)

    return _serve_term(source.namespace + bare, media)


def _stamp():
    source = _source()
    return tuple(sorted(mv.stamp() for versions in source.versions.values()
                        for mv in versions.values()))


def _serve_module(module_version, media, canonical):
    source = _source()
    location = None if canonical else "/%s-%s" % (module_version.module,
                                                  module_version.version)
    if media in RDF_TYPES:
        return rdf_response(module_version.graph, media, location=location)
    facts = [f for f in _facts() if f["module"] == module_version.module]
    body, etag = _cache().get_or_build(
        ("module", module_version.module, module_version.version),
        module_version.stamp(),
        lambda: _linked(render_module(
            module_version, source.namespace, _prefix(),
            source.module_versions(module_version.module), facts)))
    if not_modified(etag):
        return Response(status=304)
    return html_response(body, etag=etag, location=location)


def _serve_term(iri, media):
    source = _source()
    definition, home = source.term_definition(iri)
    if definition is None:
        abort(404)
    if media in RDF_TYPES:
        return rdf_response(definition, media,
                            location="/%s-%s" % (home.module, home.version))
    body, etag = _cache().get_or_build(
        ("term", iri), home.stamp(),
        lambda: _linked(render_term(home.graph, iri, source.namespace,
                                    _prefix(), str(home))))
    if not_modified(etag):
        return Response(status=304)
    return html_response(body, etag=etag)


# -------------------------------------------------------------------- setup

def build_app(source, prefix="", config=None):
    """A Flask application serving one source."""
    application = Flask(__name__)
    application.config.update(SOURCE=source, PREFIX=prefix, CONFIG=config,
                              CACHE=Cache())
    application.register_blueprint(bp)
    return application


def from_files(directories, namespace, prefix=""):
    return build_app(Files(directories, namespace), prefix)


def from_config(config, prefix="", version="1.0"):
    return build_app(Generated(config, version), prefix, config)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--files", nargs="+", help="directories of "
                        "Module-x.y.ttl files")
    parser.add_argument("--namespace", help="required with --files")
    parser.add_argument("--config", help="a gemov configuration")
    parser.add_argument("--prefix", default="", help="prefix for compact IRIs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args(argv)

    if args.config:
        from ..config import Config
        from_config(Config.load(args.config), args.prefix)
    elif args.files:
        if not args.namespace:
            parser.error("--files needs --namespace")
        from_files(args.files, args.namespace, args.prefix)
    else:
        parser.error("give --files or --config")
    source = _source()
    print("%d modules in %s" % (len(source.modules()), source.namespace))
    app.run(host=args.host, port=args.port)
    return 0
