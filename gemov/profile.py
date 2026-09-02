"""Profiles: what a user gets when they ask for a part of the vocabulary.

Record ottr/302 left the word open. Here it is an operation, in three steps:

1. **Selection.** The user names items of dimensions — ``quantity=Temperature``,
   ``aggregation=Average``. Generation runs again with those dimensions
   restricted to those items, so the cartesian product shrinks instead of being
   filtered afterwards: what is not asked for is never minted.
2. **Closure.** The selection mints terms that refer to terms it did not mint
   (``seas:Property``, an alignment target, a term of another module). Their
   defining triples are pulled from the full generation, transitively, so the
   profile is self-contained.
3. **Explanation.** Every term added by the closure is returned with the term
   that pulled it in, so a profile can be justified line by line rather than
   trusted.

The result is one graph, plus the explanation.
"""

from rdflib import BNode, Graph, URIRef


class Profile:
    def __init__(self, graph, selected, closure, why):
        self.graph = graph
        #: terms minted by the selection itself
        self.selected = selected
        #: terms added to make it self-contained
        self.closure = closure
        #: term added -> the term that referred to it
        self.why = why

    def explain(self):
        lines = ["%d terms selected, %d added to close the profile"
                 % (len(self.selected), len(self.closure))]
        for term in sorted(self.closure, key=str):
            lines.append("  %s\n      because %s refers to it"
                         % (term, self.why[term]))
        return "\n".join(lines)

    def __len__(self):
        return len(self.graph)


def _definition(graph, subject, seen=None):
    """The triples that define a subject: those it heads, following blank
    nodes — an OWL restriction is part of the term that carries it."""
    seen = seen if seen is not None else set()
    if subject in seen:
        return
    seen.add(subject)
    for predicate, obj in graph.predicate_objects(subject):
        yield (subject, predicate, obj)
        if isinstance(obj, BNode):
            yield from _definition(graph, obj, seen)


def build(config, selection):
    """Generate the profile named by `selection` (dimension -> iterable of
    item keys)."""
    for name, keys in selection.items():
        if name not in config.dimensions:
            raise ValueError("no dimension %r" % name)
        unknown = set(keys) - set(config.dimensions[name])
        if unknown:
            raise ValueError("dimension %r has no item(s) %s"
                             % (name, ", ".join(sorted(unknown))))

    full = config.generate()
    full_graph = full.all_triples()
    partial = config.generate(selection={k: set(v)
                                         for k, v in selection.items()})

    graph = partial.all_triples()
    selected = {t for terms in partial.minted.values() for t in terms}
    known = set(selected)
    closure, why = set(), {}

    frontier = list(selected)
    while frontier:
        term = frontier.pop()
        for _, _, obj in _definition(graph if term in selected else full_graph,
                                     term):
            if not isinstance(obj, URIRef) or obj in known:
                continue
            if obj not in full.owner:            # not a term of this vocabulary
                continue
            known.add(obj)
            closure.add(obj)
            why[obj] = term
            for triple in _definition(full_graph, obj):
                graph.add(triple)
            frontier.append(obj)

    return Profile(graph, selected, closure, why)
