# GEMOV

**Generating Modular Ontologies and Vocabularies.** An ontology whose terms are
a cartesian product should be generated, not typed.

You describe **dimensions** (named sets of items), **modules** (the ontologies
you publish) and **patterns** (ordinary Python functions writing triples). GEMOV
runs the patterns over the product of their dimensions and gives you one RDF
graph per module — plus the checks that say the result is coherent, the
**profiles** that hand a user only the part they asked for, a **documentation
site**, and a **server** for the namespace.

```yaml
dimensions:
  quantity: { Temperature: {}, Humidity: {}, Pressure: {} }
  aggregation: { Average: {} }

modules:
  StatisticsOntology:
    patterns:
      patterns.aggregated_evaluation:
        statisticalModifier: aggregation
        property: quantity
```

```python
@pattern
def aggregated_evaluation(context, *, statisticalModifier, property):
    context.mint(statisticalModifier.key + property.key + "Evaluation",
                 (RDF.type, OWL.Class),
                 (RDFS.subClassOf, context.term(property.key + "Evaluation")))
```

Three quantities and one aggregation give `AverageTemperatureEvaluation`,
`AverageHumidityEvaluation` and `AveragePressureEvaluation`. Ninety-nine
quantities give ninety-nine, and neither file grows.

## Why it exists, measured

The published [SEAS](https://w3id.org/seas/) ontologies are the motivating
case, and the numbers come from a script that ships with GEMOV
(`examples/seas/analyse_seas.py`):

| | |
|---|---|
| the vocabulary | 34 282 triples, 632 classes, 1 890 object properties |
| the product, written by hand | 139 classes end in `Evaluation`, 99 in `Property` |
| what hand-writing left | 51 quantities have an `Evaluation` and no `Property`, 79 labels carry a stray space, `vs:term_status` says `test` nine times |
| and worse | **11 terms are claimed by two or three modules at once**, with different labels and comments in each |

Every one of those is something a generator cannot produce and a check can
catch. That is the whole argument.

## Where to go

| I want to… | Go to |
|---|---|
| **understand the model** | [dimensions and items](model/dimensions.md), then [modules](model/modules.md) and [patterns](model/patterns.md) |
| **write one** | [write a vocabulary](guides/write-a-vocabulary.md) |
| **write patterns in Turtle notation** | [patterns in Linked-Data Python](guides/ldpy.md) |
| **hand a user a part of it** | [profiles](model/profiles.md) |
| **publish it** | [generated documentation](publish/documentation.md), [serving the namespace](publish/server.md) |
| **know why it is shaped this way** | [the polynomial model](why/polynomial.md) |

## Install

```text
pip install gemov              # the generator: rdflib and PyYAML
pip install gemov[docs]        # + the documentation generator
pip install gemov[server]      # + the HTTP server
```

The generator itself depends on rdflib and PyYAML and nothing else. The
documentation and the server are optional, and so is writing your patterns in
[Linked-Data Python](https://github.com/linked-data-python/ldpy).
