"""Views: a graph assembled on demand from what the query asks for.

    /view?module=GenericPropertyOntology&term=Temperature&closure=1

A view names **modules**, **terms** and — when the vocabulary is generated
from a configuration — **dimension items**, and gets back one graph containing
them. With `closure=1` the graph is completed: every term of the namespace
that the selection refers to is pulled in with its definition, transitively,
so the view stands on its own.

It is the profile of `gemov.profile` reachable over HTTP. On a generated
source the two are the same operation: selecting dimension items re-runs the
patterns restricted to them, so what is not asked for is never minted. On a
source that is a directory of files there is nothing to re-run, and a view is
the modules and terms named, closed.
"""

from rdflib import BNode, Graph, URIRef


def _definition(source, subject, target, seen):
    if subject in seen:
        return
    seen.add(subject)
    for predicate, obj in source.predicate_objects(subject):
        target.add((subject, predicate, obj))
        if isinstance(obj, BNode):
            _definition(source, obj, target, seen)


def build(source, modules=(), terms=(), selection=None, close=False):
    """Assemble the view. Returns (graph, report)."""
    namespace = source.namespace
    out = Graph()
    report = {"modules": [], "terms": [], "closure": [], "unknown": [],
              "selection": dict(selection or {})}

    if selection:
        # a generated source can restrict the product itself: what is not
        # asked for is never minted, rather than filtered afterwards
        from .. import profile as profile_mod
        result = profile_mod.build(source.config, selection)
        for triple in result.graph:
            out.add(triple)
        report["closure"].extend(str(t) for t in result.closure)

    for name in modules:
        module_version = source.resolve_version(*_split(name))
        if module_version is None:
            report["unknown"].append(name)
            continue
        for triple in module_version.graph:
            out.add(triple)
        for prefix, ns in module_version.graph.namespaces():
            out.namespace_manager.bind(prefix, ns, replace=True)
        report["modules"].append(str(module_version))

    for name in terms:
        iri = name if name.startswith("http") else namespace + name
        definition, home = source.term_definition(iri)
        if definition is None:
            report["unknown"].append(name)
            continue
        for triple in definition:
            out.add(triple)
        report["terms"].append(iri)

    if close:
        seen = {s for s in out.subjects() if isinstance(s, URIRef)}
        frontier = [o for o in out.objects()
                    if isinstance(o, URIRef) and str(o).startswith(namespace)
                    and o not in seen]
        while frontier:
            iri = frontier.pop()
            if iri in seen:
                continue
            seen.add(iri)
            definition, home = source.term_definition(str(iri))
            if definition is None:
                continue
            report["closure"].append(str(iri))
            for triple in definition:
                out.add(triple)
                if isinstance(triple[2], URIRef) and \
                        str(triple[2]).startswith(namespace) and triple[2] not in seen:
                    frontier.append(triple[2])
    report["triples"] = len(out)
    return out, report


def _split(name):
    """`BuildingOntology-0.9` -> ("BuildingOntology", "0.9")."""
    if "-" in name:
        module, _, version = name.rpartition("-")
        return module, version
    return name, None
