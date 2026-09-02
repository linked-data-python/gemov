# Modules

A **module** is an ontology you publish: an IRI, a version, a set of terms, and
a document someone can read. In the configuration it names the patterns that
fill it.

```yaml
modules:
  GenericPropertyOntology:
    title: The generic property ontology
    patterns:
      patterns.property_family: [ quantity ]
  StatisticsOntology:
    title: The statistics ontology
    patterns:
      patterns.aggregation_class: [ aggregation ]
      patterns.aggregated_evaluation:
        statisticalModifier: aggregation
        property: quantity
```

## A module declares itself

Before any pattern runs, GEMOV mints the module's own IRI as an `owl:Ontology`
with its title. Without it every `rdfs:isDefinedBy` in the module would point
at nothing — which is what `gemov check` reports as *dangling*, and how this
rule was found.

## A term belongs to exactly one module

This is the invariant that makes the output an ontology rather than a pile of
triples, and GEMOV enforces it rather than hoping for it.

```python
OwnershipError: https://w3id.org/seas/Clash is minted by module A and again
by B — a term belongs to one module
```

The subtlety is *which* module, and it is not obvious. A pattern may call
another pattern; if the callee minted into the caller's module, then the module
a term belongs to would depend on **which pattern ran first**, and two runs of
the same configuration could disagree. So a pattern's module is decided from
the configuration **before anything runs**, and a pattern assigned to two
modules is refused:

```python
ValueError: pattern patterns.property_family is assigned to modules
GenericPropertyOntology and Elsewhere — a pattern mints into one module
```

!!! note "Found in the wild"
    The published SEAS 1.0 has **eleven terms claimed by two or three modules
    at once**, with different labels and comments in each.
    `TemperatureProperty` is `rdfs:isDefinedBy` both
    `ClimateAndForecastOntology` and `GenericPropertyOntology`. This invariant
    exists because that happens.

## Versions

The generator produces the current version of each module; the
[server](../publish/server.md) and the documentation know about several, and
the access contract says what an unversioned IRI means.
