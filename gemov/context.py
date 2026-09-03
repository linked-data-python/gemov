"""The execution context: dimensions, modules, and who owns which term.

Generation is a cartesian product. A configuration declares *dimensions*
(named sets of items), *modules* (named ontologies), and, per module, which
patterns to specialise on which dimensions. Running it calls each pattern once
per combination.

Two invariants make the result an ontology rather than a pile of triples, and
both are checked here rather than left to the author:

* **a term belongs to exactly one module** — the module whose pattern minted
  it. A second module minting the same term is an error, not a merge;
* **a specialisation runs once** — patterns call each other freely, and the
  same (pattern, arguments) pair produces its triples a single time.
"""

import itertools

from rdflib import Graph, Literal, Namespace, RDFS, URIRef
from rdflib.namespace import DCTERMS, NamespaceManager, OWL, RDF


class OwnershipError(Exception):
    """Two modules mint the same term."""


class Item:
    """One item of a dimension: its key, and whatever the configuration
    attached to it. ``item.key`` is the identifier the naming rules use;
    ``item.value`` is the mapping (or the bare value) from the YAML."""

    __slots__ = ("dimension", "key", "value")

    def __init__(self, dimension, key, value):
        self.dimension = dimension
        self.key = key
        self.value = value

    def get(self, field, default=None):
        return self.value.get(field, default) if isinstance(self.value, dict) \
            else default

    def __iter__(self):
        """Unpacks as ``(key, value)``, as the first prototype did."""
        return iter((self.key, self.value))

    def __str__(self):
        return self.key

    def __repr__(self):
        return "Item(%s=%r)" % (self.dimension, self.key)


class ExecutionContext:
    """What a pattern writes into, and what remembers who wrote what."""

    def __init__(self, base="https://example.org/", prefixes=None):
        self.base = base
        self.prefixes = dict(prefixes or {})
        self.dimensions = {}
        self.modules = {}                 # name -> Graph
        self.owner = {}                   # URIRef -> module name
        self.minted = {}                  # module -> [URIRef], in mint order
        self.home = {}                    # pattern function -> its module
        self.roles = {}                   # pattern function -> {role: dimension}
        self._module = None
        self._done = set()
        self._namespace_manager = None

    # ------------------------------------------------------------ naming

    @property
    def ns(self):
        return Namespace(self.base)

    def term(self, local):
        """A term of this vocabulary, from its local name."""
        return URIRef(self.base + local)

    def resolve(self, uri_or_curie):
        """An IRI, a CURIE over the declared prefixes, or a local name."""
        if isinstance(uri_or_curie, URIRef):
            return uri_or_curie
        head, sep, tail = uri_or_curie.partition(":")
        if not sep:
            return self.term(uri_or_curie)
        if head in ("http", "https", "urn"):
            return URIRef(uri_or_curie)
        if head in self.prefixes:
            return URIRef(self.prefixes[head] + tail)
        raise ValueError("unknown prefix %r in %r" % (head, uri_or_curie))

    def namespace_manager(self):
        if self._namespace_manager is None:
            holder = Graph()
            for prefix, iri in self.prefixes.items():
                holder.namespace_manager.bind(prefix, iri, replace=True)
            self._namespace_manager = holder.namespace_manager
        return self._namespace_manager

    # ----------------------------------------------------------- modules

    @property
    def module(self):
        """The module being generated, or None outside a run."""
        return self._module

    @property
    def graph(self):
        """The graph of the module being generated. Patterns write here."""
        if self._module is None:
            raise RuntimeError("no module is being generated: a pattern must "
                               "be called through ExecutionContext.run()")
        return self.modules[self._module]

    @graph.setter
    def graph(self, value):
        """`context.graph += g` is how an rdflib user adds a graph, and `+=`
        on a property assigns the result back. rdflib returns the same object,
        so this accepts exactly that and refuses anything else — a module's
        graph is not replaceable."""
        if value is not self.modules.get(self._module):
            raise AttributeError(
                "a module's graph cannot be replaced; add to it instead "
                "(context.graph += other, or context.graph.add(triple))")

    def module_iri(self, name=None):
        return self.term(name or self._module)

    def declare_module(self, name, title=None, metadata=None):
        """Mint the module's own IRI as an ontology. A module that does not
        declare itself leaves every `rdfs:isDefinedBy` pointing at nothing —
        which is what `gemov check` reports as dangling.

        `metadata` is whatever else the module says about itself, as
        *predicate -> value* over the declared prefixes:
        `dcterms:description`, `dcterms:issued`, `owl:versionInfo`. A
        generated module that carries none is visibly poorer than a
        hand-written one on its own page, and a vocabulary that is partly
        generated should not be readable as two halves.
        """
        self.modules.setdefault(name, self._new_graph())
        previous, self._module = self._module, name
        try:
            iri = self.mint(name, (RDF.type, OWL.Ontology))
            self.graph.add((iri, RDFS.isDefinedBy, iri))
            if title:
                self.graph.add((iri, RDFS.label, Literal(title, lang="en")))
                self.graph.add((iri, DCTERMS.title, Literal(title, lang="en")))
            for key, values in (metadata or {}).items():
                predicate = self.resolve(key)
                for value in (values if isinstance(values, list) else [values]):
                    self.graph.add((iri, predicate, self._literal(value)))
        finally:
            self._module = previous
        return iri

    def _literal(self, value):
        """An IRI if it looks like one, otherwise English prose.

        A vocabulary's own metadata is either a link (a licence, a creator) or
        something someone wrote; guessing between them on the shape of the
        string is the only thing a YAML mapping leaves undecided."""
        text = str(value)
        if text.startswith(("http://", "https://", "urn:")):
            return URIRef(text)
        return Literal(text, lang="en")

    def mint(self, local, *triples):
        """Declare a term as belonging to the current module, and add the
        triples that define it. Returns the term, so it composes.

            cls = context.mint("TemperatureProperty",
                               (RDF.type, OWL.Class),
                               (RDFS.subClassOf, context.term("Property")))
        """
        subject = self.term(local) if not isinstance(local, URIRef) else local
        held = self.owner.get(subject)
        if held is not None and held != self._module:
            raise OwnershipError(
                "%s is minted by module %s and again by %s — a term belongs to "
                "one module" % (subject, held, self._module))
        if held is None:
            self.owner[subject] = self._module
            self.minted.setdefault(self._module, []).append(subject)
        graph = self.graph
        for triple in triples:
            graph.add((subject,) + tuple(triple) if len(triple) == 2
                      else tuple(triple))
        return subject

    # --------------------------------------------------------- execution

    def dimension(self, name):
        if name not in self.dimensions:
            raise ValueError("no dimension %r (declared: %s)"
                             % (name, ", ".join(sorted(self.dimensions))))
        return [Item(name, key, value)
                for key, value in self.dimensions[name].items()]

    def degree(self, fn):
        """The arity of a pattern: the degree of the monomial it generates
        (record ottr/308)."""
        return len(self.roles.get(fn, {}))

    def specialise(self, fn, *args, **kwargs):
        """Run a pattern once for these arguments — the guard that makes a
        pattern calling another pattern safe.

        A pattern the configuration assigns to a module always mints into
        *that* module, whoever calls it. Without this, the module a term
        belongs to would depend on which pattern happened to run first, and
        two runs of the same configuration could disagree."""
        signature = (fn, tuple(str(a) for a in args),
                     tuple(sorted((k, str(v)) for k, v in kwargs.items())))
        if signature in self._done:
            return
        self._done.add(signature)
        home = self.home.get(fn, self._module)
        previous, self._module = self._module, home
        self.modules.setdefault(home, self._new_graph())
        try:
            fn(self, *args, **kwargs)
        finally:
            self._module = previous

    def run(self, module, pattern_fn, dimensions, selection=None):
        """Specialise one pattern over the product of its dimensions, inside
        one module.

        `dimensions` is either a list of dimension names — the arguments are
        then positional, in that order — or a mapping *role -> dimension*, and
        the pattern receives one keyword argument per role. Record ottr/308
        argues for the second: a monomial is not a product of dimensions but a
        product of dimensions **with named roles**, since `x·y` and `y·x`
        differ, and the role is what an I-ADOPT description needs.

        `selection` restricts a dimension to some of its items — that is what a
        profile is (see gemov.profile).
        """
        self.modules.setdefault(module, self._new_graph())
        previous, self._module = self._module, module
        roles = list(dimensions) if isinstance(dimensions, dict) else None
        names = [dimensions[r] for r in roles] if roles else list(dimensions)
        self.roles[pattern_fn.gemov_pattern] = dict(dimensions) if roles \
            else {n: n for n in names}
        try:
            pools = []
            for name in names:
                items = self.dimension(name)
                keep = (selection or {}).get(name)
                if keep is not None:
                    items = [i for i in items if i.key in keep]
                pools.append(items)
            for combination in itertools.product(*pools):
                if roles:
                    self.specialise(pattern_fn.gemov_pattern,
                                    **dict(zip(roles, combination)))
                else:
                    self.specialise(pattern_fn.gemov_pattern, *combination)
        finally:
            self._module = previous

    def _new_graph(self):
        graph = Graph()
        graph.namespace_manager = NamespaceManager(graph)
        for prefix, iri in self.prefixes.items():
            graph.namespace_manager.bind(prefix, iri, replace=True)
        return graph

    # ------------------------------------------------------------ result

    def all_triples(self):
        graph = self._new_graph()
        for module_graph in self.modules.values():
            for triple in module_graph:
                graph.add(triple)
        return graph

    def __len__(self):
        return sum(len(g) for g in self.modules.values())
