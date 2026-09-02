# GEMOV — Generating Modular Ontologies and Vocabularies

An ontology whose terms are a cartesian product should be generated, not
typed. GEMOV takes a YAML description of **dimensions**, **modules** and
**patterns**, runs the patterns over the product, and gives you one RDF graph
per module — plus the checks that tell you the result is coherent, and a
**profile** operation that hands a user only the part they asked for.

It is a library on [rdflib](https://github.com/RDFLib/rdflib): a pattern is an
ordinary Python function writing triples, and the whole of rdflib is available
inside it. Nothing new has to be learnt to write one.

## The case for it, measured

The published [SEAS](https://w3id.org/seas/) ontologies are the motivating
example, and `examples/seas/analyse_seas.py` reports on them:

```text
52 files, 34282 triples, 632 classes, 1890 object properties
   Evaluation   139 classes end in it
   Property      99 classes end in it
   99 quantities have a *Property class, 139 have a *Evaluation one
   asymmetric: 11 Property with no Evaluation, 51 the other way
   79 labels carry a stray space, e.g. ' Acceleration Evaluation'
   vs:term_status values: testing×4086, stable×75, unstable×38, test×9
```

A vocabulary that is 99 quantities × a handful of patterns, written out by
hand, with the asymmetries and the stray spaces that hand-writing leaves. That
is what this library exists to stop.

## A configuration

```yaml
base: https://w3id.org/seas/

dimensions:
  quantity:
    Temperature: { kind: ThermodynamicQuantity }
    Pressure:    { kind: MechanicalQuantity }
  aggregation:
    Average: {}

modules:
  GenericPropertyOntology:
    title: The SEAS generic property ontology
    patterns:
      patterns.property_family: [ quantity ]
  StatisticsOntology:
    patterns:
      patterns.aggregated_evaluation: [ aggregation, quantity ]
```

`import:` merges another configuration first, so a vocabulary of dimensions is
shared and a module is added without touching it.

## A pattern

```python
from gemov import pattern
from rdflib import RDFS
from rdflib.namespace import OWL, RDF

@pattern
def property_family(context, quantity):
    cls = context.mint(quantity.key + "Property",
                       (RDF.type, OWL.Class),
                       (RDFS.subClassOf, context.term("Property")))
    context.graph.add((cls, RDFS.label, ...))
```

`context.mint` records that this term belongs to the module being generated;
`context.graph` is that module's graph. A pattern may call another pattern —
the context runs each specialisation once, so a diamond produces one copy of
the triples.

### The same pattern, in Linked-Data Python

A pattern is mostly triples, and
[ldpy](https://github.com/linked-data-python/ldpy) lets them be written in
Turtle's own notation, inside Python. GEMOV installs its import hook when it is
installed, so a `.ldpy` pattern module just works:

```ldpy
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

@pattern
def property_family(context, quantity):
    @graph context.graph
    +{ {context.mint(quantity.key + "Property")} a owl:Class ;
           rdfs:subClassOf {context.term("Property")} ;
           rdfs:label {"%s Property" % words}@en }
```

This is a convenience for the pattern's author, never a requirement: GEMOV
itself calls only rdflib. `examples/seas/` carries both spellings of the same
patterns, and the test suite asserts the two graphs are isomorphic.

## Three invariants, checked rather than hoped for

| | |
|---|---|
| **A term belongs to one module** | the module the configuration assigns its pattern to. A second module minting it is an error, and the assignment is fixed *before* anything runs, so generation does not depend on the order the modules are visited. |
| **A specialisation runs once** | patterns call each other freely. |
| **A module declares itself** | each module mints its own IRI as an `owl:Ontology`, so no `rdfs:isDefinedBy` points at nothing. |

`gemov check` adds the rules that catch what hand-writing produces — stray
spaces in labels, a label with no language tag, a `vs:term_status` outside its
vocabulary, a term minted with no OWL type, an IRI in the namespace that no
module mints. Every one of them is violated by the published SEAS 1.0.

## Profiles

Record `ottr/302` left the word open; here it is an operation in three steps.
The user **selects** items of dimensions, and generation runs again with those
dimensions restricted — what is not asked for is never minted, rather than
filtered afterwards. The selection is then **closed**: terms it refers to but
did not mint are pulled in transitively, so the profile stands alone. And every
term the closure added comes with the term that pulled it, so a profile is
**explained** rather than trusted.

```text
$ gemov profile examples/seas/vocabulary.yml quantity=Temperature kind=MechanicalQuantity --explain
9 terms selected, 1 added to close the profile
  https://w3id.org/seas/ThermodynamicQuantity
      because https://w3id.org/seas/TemperatureProperty refers to it
```

## Documentation, and a server for the namespace

A generated vocabulary can document itself, including the **rules** that
minted it — a page per pattern, with its degree and the roles of its
dimensions, which a hand-written ontology cannot have:

```text
gemov docs  vocabulary.yml -o site/     # a static site, pyLODE-shaped
gemov serve vocabulary.yml              # the namespace over HTTP, with views
```

The server answers for one namespace, modular and versioned: content
negotiation, versioned and unversioned IRIs, and `/view?…` which assembles a
graph from the modules, terms and dimension items a query names. Both are
optional extras.

## Use

```text
pip install -e .              # the generator: rdflib and PyYAML
pip install -e .[docs]        # + the documentation generator (uses ldpy)
pip install -e .[server]      # + the HTTP server (Flask)

gemov build   vocabulary.yml -o out/
gemov profile vocabulary.yml quantity=Temperature --explain
gemov check   vocabulary.yml
gemov docs    vocabulary.yml -o site/
gemov serve   vocabulary.yml
python -m pytest tests
```

**The full documentation is in `docs/`** (mkdocs, readthedocs-ready):
`mkdocs serve`. It is where dimensions, items, modules, patterns, roles,
degree, profiles and the access contract are defined.

## Layout

```
gemov/patterns.py   the @pattern decorator and the registry
gemov/context.py    dimensions, modules, term ownership, the product
gemov/config.py     the YAML model, with `import`
gemov/profile.py    selection, closure, explanation
gemov/check.py      the coherence rules
gemov/cli.py        build | profile | check | docs | serve
gemov/doc/          the documentation generator; its queries are in ldpy
gemov/server/       the HTTP server, over a source of modules
examples/seas/      the demonstration of record ottr/302, in Python and in ldpy
docs/               this project's own documentation
```

Design decisions are recorded in the `pilotage` repository, records `ottr/302`
and `ottr/308`.
