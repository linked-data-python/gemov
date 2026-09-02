"""What the server serves: a source of modules, versions and terms.

Two kinds, and the server does not know which it has:

* **`Files`** — a directory of Turtle files named `Module-x.y.ttl`, which is
  how SEAS has published since 2016. Nothing is generated; the files are the
  truth.
* **`Generated`** — a gemov configuration. The modules are produced on demand
  from the patterns, and a *view* can then select items of a dimension, which
  a directory of files cannot offer.

Both answer the same three questions — which modules, which versions, which
module claims a term — so the access contract is written once.
"""

import glob
import os
import re

from rdflib import Graph, RDFS, URIRef
from rdflib.namespace import OWL, RDF

#: `ActorOntology-0.9.ttl`
FILE = re.compile(r"^(?P<module>[A-Za-z][A-Za-z0-9]*)-"
                  r"(?P<version>[0-9]+(?:\.[0-9]+)*)\.ttl$")


def version_key(version):
    return tuple(int(p) for p in version.split("."))


class ModuleVersion:
    """One module at one version, and the graph behind it."""

    def __init__(self, module, version, namespace, loader, sources=()):
        self.module = module
        self.version = version
        self.namespace = namespace
        self._loader = loader
        self.sources = list(sources)
        self._graph = None

    @property
    def graph(self):
        if self._graph is None:
            self._graph = self._loader()
        return self._graph

    @property
    def iri(self):
        return URIRef(self.namespace + self.module)

    def terms(self):
        return {s for s in self.graph.subjects(RDFS.isDefinedBy, self.iri)
                if str(s).startswith(self.namespace)}

    def stamp(self):
        """What the cache keys on: the mtimes of what this was built from."""
        return tuple(sorted((os.path.basename(p), os.path.getmtime(p))
                            for p in self.sources if os.path.exists(p)))

    def __repr__(self):
        return "%s-%s" % (self.module, self.version)


class Source:
    """The interface the server uses. Subclasses fill `versions`."""

    namespace = None
    dimensions = {}

    def __init__(self):
        self.versions = {}                 # module -> {version: ModuleVersion}
        self._term_home = None

    # ------------------------------------------------------------ lookups

    def modules(self):
        return sorted(self.versions)

    def module_versions(self, module):
        return sorted(self.versions.get(module, {}), key=version_key)

    def latest(self, module):
        versions = self.module_versions(module)
        return self.versions[module][versions[-1]] if versions else None

    def is_module(self, name):
        return name in self.versions

    def resolve_version(self, module, wanted=None):
        """`None` or a partial version (`1`, `1.0`) gives the highest match."""
        versions = self.module_versions(module)
        if not versions:
            return None
        if wanted is None:
            return self.versions[module][versions[-1]]
        exact = self.versions[module].get(wanted)
        if exact is not None:
            return exact
        prefix = wanted.split(".")
        matching = [v for v in versions if v.split(".")[:len(prefix)] == prefix]
        return self.versions[module][matching[-1]] if matching else None

    def index_terms(self):
        if self._term_home is None:
            self._term_home = {}
            for module in self.modules():
                for version in self.module_versions(module):
                    mv = self.versions[module][version]
                    for term in mv.terms():
                        self._term_home.setdefault(term, []).append(mv)
        return self._term_home

    def term_definition(self, iri):
        """The triples defining a term, from the latest module that claims it,
        blank nodes followed."""
        homes = self.index_terms().get(URIRef(iri))
        if not homes:
            return None, None
        home = sorted(homes, key=lambda mv: version_key(mv.version))[-1]
        out = Graph()
        for prefix, ns in home.graph.namespaces():
            out.namespace_manager.bind(prefix, ns, replace=True)
        _copy(home.graph, URIRef(iri), out, set())
        return out, home


class Files(Source):
    """A directory of `Module-x.y.ttl` files."""

    def __init__(self, directories, namespace):
        super().__init__()
        self.namespace = namespace
        self.directories = [os.path.abspath(d) for d in directories]
        for directory in self.directories:
            for path in sorted(glob.glob(os.path.join(directory, "*.ttl"))):
                match = FILE.match(os.path.basename(path))
                if not match:
                    continue
                module = match.group("module")
                version = match.group("version")
                self.versions.setdefault(module, {})[version] = ModuleVersion(
                    module, version, namespace,
                    (lambda p=path: _parse(p)), sources=[path])


class Generated(Source):
    """A gemov configuration: the modules are produced by the patterns."""

    def __init__(self, config, version="1.0"):
        super().__init__()
        self.config = config
        self.namespace = config.base
        self.dimensions = config.dimensions
        context = config.generate()
        self.context = context
        sources = [config.path] if config.path else []
        for module, graph in context.modules.items():
            self.versions[module] = {version: ModuleVersion(
                module, version, config.base, (lambda g=graph: g),
                sources=sources)}


def _parse(path):
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def _copy(source, subject, target, seen):
    from rdflib import BNode
    if subject in seen:
        return
    seen.add(subject)
    for predicate, obj in source.predicate_objects(subject):
        target.add((subject, predicate, obj))
        if isinstance(obj, BNode):
            _copy(source, obj, target, seen)
