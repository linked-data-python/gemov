# How to write a vocabulary

Three files, and you can run them at every step.

## 1. The configuration

`vocabulary.yml` — the namespace, the dimensions, the modules.

```yaml
base: https://example.org/
prefixes:
  ex: https://example.org/
  owl: http://www.w3.org/2002/07/owl#
  rdfs: http://www.w3.org/2000/01/rdf-schema#

dimensions:
  quantity:
    Temperature: {}
    Humidity: {}

modules:
  Upper:
    title: The upper ontology
    patterns: { patterns.upper: [] }
  Properties:
    title: The property ontology
    patterns: { patterns.property_family: [ quantity ] }
```

## 2. The patterns

`patterns.py`, next to it — the directory of the configuration is importable.

```python
from gemov import pattern
from rdflib import Literal, RDFS
from rdflib.namespace import OWL, RDF


@pattern
def upper(context):
    term = context.mint("Property", (RDF.type, OWL.Class))
    context.graph.add((term, RDFS.label, Literal("Property", lang="en")))
    context.graph.add((term, RDFS.isDefinedBy, context.module_iri()))


@pattern
def property_family(context, quantity):
    term = context.mint(quantity.key + "Property",
                        (RDF.type, OWL.Class),
                        (RDFS.subClassOf, context.term("Property")))
    context.graph.add((term, RDFS.label,
                       Literal("%s property" % quantity.key.lower(), lang="en")))
    context.graph.add((term, RDFS.isDefinedBy, context.module_iri()))
```

## 3. Run it

```text
gemov build vocabulary.yml            # everything, to stdout
gemov build vocabulary.yml -o out/    # one Turtle file per module
gemov check vocabulary.yml            # the coherence findings
```

`check` is the one to run first and often. It will tell you, for instance, that
a label has no language tag, or that a term you referred to is minted by
nobody.

## 4. Then

- hand a user a part of it: [profiles](../model/profiles.md);
- publish it: [documentation](../publish/documentation.md) and
  [the server](../publish/server.md);
- write the triples in Turtle's own notation: [in ldpy](ldpy.md).

## Growing it

Adding a quantity is one line in the configuration. Adding a *kind* of term —
an evaluation class, a property key, an alignment axiom — is one pattern, and
it applies to every quantity at once. That asymmetry is the point: the
configuration grows with the data, the code grows with the shapes, and neither
grows with the product.
