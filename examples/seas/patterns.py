"""The SEAS patterns, in plain Python over rdflib.

They reproduce the shape that SEAS 1.0 carries by hand: for each quantity, a
property class and an evaluation class; for each aggregation and quantity, the
aggregated evaluation. `patterns_ldpy.ldpy` is the same thing written in
Turtle's notation — the test suite asserts the two graphs are equal.
"""

from rdflib import Literal, RDFS, URIRef
from rdflib.namespace import OWL, RDF

from gemov import pattern

VS = URIRef("http://www.w3.org/2003/06/sw-vocab-status/ns#term_status")


def _words(camel):
    """`AirCO2Level` -> `Air CO2 Level`, the label SEAS writes by hand."""
    out = []
    for i, char in enumerate(camel):
        if char.isupper() and i and not camel[i - 1].isupper():
            out.append(" ")
        out.append(char)
    return "".join(out)


def _common(context, term, label, comment):
    context.graph.add((term, RDFS.label, Literal(label, lang="en")))
    context.graph.add((term, RDFS.comment, Literal(comment, lang="en")))
    context.graph.add((term, RDFS.isDefinedBy, context.module_iri()))
    context.graph.add((term, VS, Literal("testing")))


@pattern
def upper(context):
    """`Property` and `Evaluation`, the two classes everything hangs from.
    A pattern specialised on no dimension runs once."""
    for local, comment in (("Property", "The class of properties."),
                           ("Evaluation", "The class of evaluations."),
                           ("QuantityKind", "The class of quantity kinds.")):
        term = context.mint(local, (RDF.type, OWL.Class))
        _common(context, term, _words(local), comment)
    context.mint("quantityKind", (RDF.type, OWL.ObjectProperty))
    _common(context, context.term("quantityKind"), "quantity kind",
            "The kind of quantity a property quantifies.")


@pattern
def quantity_kind(context, kind):
    """One term per kind of quantity — a module of its own, so that a profile
    can leave the kinds it does not need behind."""
    term = context.mint(kind.key, (RDF.type, OWL.Class),
                        (RDFS.subClassOf, context.term("QuantityKind")))
    _common(context, term, _words(kind.key),
            "The %s kind of quantity." % _words(kind.key).lower())


@pattern
def property_family(context, quantity):
    """`<Q>Property` and `<Q>Evaluation`, for one quantity."""
    words = _words(quantity.key)
    cls = context.mint(quantity.key + "Property",
                       (RDF.type, OWL.Class),
                       (RDFS.subClassOf, context.term("Property")))
    _common(context, cls, "%s Property" % words,
            "The class of %s properties." % words.lower())
    if quantity.get("kind"):
        context.graph.add((cls, context.term("quantityKind"),
                           context.term(quantity.get("kind"))))

    ev = context.mint(quantity.key + "Evaluation",
                      (RDF.type, OWL.Class),
                      (RDFS.subClassOf, context.term("Evaluation")))
    _common(context, ev, "%s Evaluation" % words,
            "The class of evaluations of %s properties." % words.lower())


@pattern
def aggregated_evaluation(context, aggregation, quantity):
    """`<A><Q>Evaluation` — the cartesian product record 302 asks for.

    It calls `property_family`, so the quantity's own terms exist whether or
    not the configuration also specialises that pattern: the context runs a
    specialisation once, whoever asks for it.
    """
    property_family(context, quantity)
    words = "%s %s" % (_words(aggregation.key), _words(quantity.key))
    term = context.mint(aggregation.key + quantity.key + "Evaluation",
                        (RDF.type, OWL.Class),
                        (RDFS.subClassOf,
                         context.term(quantity.key + "Evaluation")),
                        (RDFS.subClassOf, context.term(aggregation.key +
                                                       "Evaluation")))
    _common(context, term, "%s Evaluation" % words,
            "The %s of evaluations of %s properties."
            % (_words(aggregation.key).lower(), _words(quantity.key).lower()))


@pattern
def aggregation_class(context, aggregation):
    """`<A>Evaluation`, the aggregation's own class."""
    words = _words(aggregation.key)
    term = context.mint(aggregation.key + "Evaluation",
                        (RDF.type, OWL.Class),
                        (RDFS.subClassOf, context.term("Evaluation")))
    _common(context, term, "%s Evaluation" % words,
            "The class of evaluations that are a %s." % words.lower())
