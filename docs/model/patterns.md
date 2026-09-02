# Patterns, roles and degree

A **pattern** is an ordinary Python function that writes triples. There is no
template language to learn: the whole of rdflib is available inside it, and so
is the whole of Python.

```python
from gemov import pattern
from rdflib import RDFS
from rdflib.namespace import OWL, RDF

@pattern
def property_family(context, quantity):
    """`<Q>Property` and `<Q>Evaluation`, for one quantity."""
    cls = context.mint(quantity.key + "Property",
                       (RDF.type, OWL.Class),
                       (RDFS.subClassOf, context.term("Property")))
    context.graph.add((cls, RDFS.label,
                       Literal("%s Property" % quantity.key, lang="en")))
```

## What the context gives you

| | |
|---|---|
| `context.mint(local, *triples)` | declare a term as belonging to this module, add the triples that define it, and return it |
| `context.term(local)` | an IRI in the vocabulary's namespace, minted or not |
| `context.resolve(curie)` | an IRI, a CURIE over the declared prefixes, or a local name |
| `context.graph` | the module's graph — plain rdflib, `add`, `+=`, everything |
| `context.module`, `context.module_iri()` | the module being generated |

`mint` is the one that matters: it is how ownership is recorded. Adding a
triple whose subject you never minted is allowed — that is how you say
something about a term another module owns — but the term stays theirs.

## Degree

A pattern's **degree** is its arity: how many dimensions it is specialised on.

```yaml
patterns:
  patterns.upper: []                    # degree 0 — runs once
  patterns.property_family: [ quantity ]        # degree 1 — once per item
  patterns.aggregated_evaluation:               # degree 2 — once per pair
    statisticalModifier: aggregation
    property: quantity
```

`context.degree(fn)` reports it. The degree is what a vocabulary *costs*: with
99 quantities and 51 modifiers, degree 2 is 5 049 terms and degree 3 is
580 635. [The polynomial model](../why/polynomial.md) is about what to do at
that point, and it is not "generate them all".

## Roles

At degree 2 and above, name which dimension plays which part:

```yaml
    patterns.aggregated_evaluation:
      statisticalModifier: aggregation
      property: quantity
```

```python
@pattern
def aggregated_evaluation(context, *, statisticalModifier, property):
    ...
```

The list form still works and passes the items positionally. Prefer the
mapping: `x × y` and `y × x` are different monomials, the role is what tells
them apart, and it is what an
[I-ADOPT](https://w3id.org/iadopt/ont) description needs in order to say which
term plays which part. The roles are kept in `context.roles`, and the
[generated documentation](../publish/documentation.md) prints them on the
pattern's own page.

## A pattern may call another

```python
@pattern
def aggregated_evaluation(context, *, statisticalModifier, property):
    property_family(context, property)      # make sure the quantity exists
    ...
```

The call goes through the context, so **the same specialisation runs once**
however many patterns ask for it: a diamond in the pattern graph produces one
copy of the triples, not two. And the callee still mints into *its own*
module, not the caller's.

## Where patterns live

Anywhere importable. The configuration names them `module.function`, and the
directory of the configuration is put on the path, so `patterns.py` next to
`vocabulary.yml` just works. A pattern may also carry a name of its own —
`@pattern("property-family")` — and be named that way in the configuration.

They may also be written in Turtle's notation: see
[patterns in Linked-Data Python](../guides/ldpy.md).
