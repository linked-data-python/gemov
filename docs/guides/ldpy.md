# Patterns in Linked-Data Python

A pattern is mostly triples. [Linked-Data
Python](https://github.com/linked-data-python/ldpy) puts Turtle's notation
inside Python, so they can be written as what they are. GEMOV installs its
import hook when it is installed, so a `.ldpy` pattern module needs no
ceremony.

```ldpy
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix vs:   <http://www.w3.org/2003/06/sw-vocab-status/ns#> .

from gemov import pattern


@pattern
def property_family(context, quantity):
    """`<Q>Property`, for one quantity."""
    @graph context.graph          # the module's graph becomes the current one
    module = context.module_iri()
    words = quantity.key

    +{ {context.mint(quantity.key + "Property")} a owl:Class ;
           rdfs:subClassOf {context.term("Property")} ;
           rdfs:label {"%s Property" % words}@en ;
           rdfs:comment {"The class of %s properties." % words.lower()}@en ;
           rdfs:isDefinedBy {module} ;
           vs:term_status "testing" }
```

Two constructs carry it. `@graph context.graph` makes the module's graph the
**current** one for the rest of the block, and `+{ … }` adds to it in place —
which is both the idiom the language teaches and the fast one.

## It is a convenience, never a requirement

GEMOV itself calls only rdflib. Whether your patterns are `.py` or `.ldpy`
changes nothing else: same configuration, same checks, same output.

The example that ships with GEMOV carries **both spellings of the same
patterns** — `examples/seas/patterns.py` and `patterns_ldpy.ldpy` — and a test
asserts the two graphs are isomorphic. If you are hesitating, read them side by
side.

## Installing

```text
pip install gemov[ldpy]
```

The documentation generator uses ldpy too, for its own queries: what a
documentation page needs from an ontology is a handful of graph patterns. See
[generated documentation](../publish/documentation.md).
