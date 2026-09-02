"""Coherence checks — the defects hand-writing produces, caught mechanically.

Every rule here was written after measuring the published SEAS 1.0, where each
of them is violated at least once. A generator that does not check these buys
nothing over a text editor.
"""

from rdflib import RDFS, URIRef
from rdflib.namespace import OWL, RDF

VS_TERM_STATUS = URIRef("http://www.w3.org/2003/06/sw-vocab-status/ns#term_status")

#: `vs:term_status` is a closed vocabulary; SEAS 1.0 contains "test", a typo
#: for "testing", nine times.
TERM_STATUS = {"unstable", "testing", "stable", "archaic"}


class Finding:
    __slots__ = ("rule", "term", "message")

    def __init__(self, rule, term, message):
        self.rule, self.term, self.message = rule, term, message

    def __str__(self):
        return "%-16s %s — %s" % (self.rule, self.term, self.message)


def check(context):
    """Every finding, in a stable order. An empty list is the passing case."""
    findings = []
    graph = context.all_triples()

    for module, terms in sorted(context.minted.items()):
        for term in terms:
            findings += _check_term(graph, context, module, term)

    # a term referred to by the vocabulary but minted by nobody
    minted = set(context.owner)
    for subject, predicate, obj in graph:
        for node in (subject, obj):
            if not isinstance(node, URIRef) or node in minted:
                continue
            if str(node).startswith(context.base):
                findings.append(Finding(
                    "dangling", node,
                    "inside the vocabulary namespace but no module mints it"))
    seen, unique = set(), []
    for f in findings:
        key = (f.rule, str(f.term), f.message)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return sorted(unique, key=lambda f: (f.rule, str(f.term)))


def _check_term(graph, context, module, term):
    out = []
    labels = list(graph.objects(term, RDFS.label))
    if not labels:
        out.append(Finding("no-label", term, "no rdfs:label"))
    for label in labels:
        if str(label) != str(label).strip():
            out.append(Finding("label-space", term,
                               "label %r has a stray space" % str(label)))
        if not str(label.language or ""):
            out.append(Finding("label-lang", term,
                               "label %r carries no language tag" % str(label)))
    defined = list(graph.objects(term, RDFS.isDefinedBy))
    if not defined:
        out.append(Finding("no-defined-by", term, "no rdfs:isDefinedBy"))
    elif context.module_iri(module) not in defined:
        out.append(Finding("wrong-module", term,
                           "rdfs:isDefinedBy %s, but module %s mints it"
                           % (defined[0], module)))
    for status in graph.objects(term, VS_TERM_STATUS):
        if str(status) not in TERM_STATUS:
            out.append(Finding("term-status", term,
                               "vs:term_status %r is not one of %s"
                               % (str(status), ", ".join(sorted(TERM_STATUS)))))
    if (term, RDF.type, OWL.Class) not in graph and \
            (term, RDF.type, OWL.ObjectProperty) not in graph and \
            (term, RDF.type, OWL.DatatypeProperty) not in graph and \
            (term, RDF.type, OWL.AnnotationProperty) not in graph and \
            (term, RDF.type, OWL.Ontology) not in graph:
        out.append(Finding("no-type", term, "minted with no OWL type"))
    return out
