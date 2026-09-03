# Configuration reference

A YAML file, **or a directory** — see [as a directory](#as-a-directory) below;
the two forms mean exactly the same thing. Every key is optional except that a
vocabulary with no `modules` generates nothing.

```yaml
base: https://w3id.org/seas/          # the namespace terms are minted in
prefixes:                             # for CURIEs, and for serialisation
  seas: https://w3id.org/seas/
  owl: http://www.w3.org/2002/07/owl#

import: [ quantities.yml ]            # merged first; a string or a list

dimensions:                           # `with dimensions:` is accepted too
  quantity:                           # a mapping when items carry data
    Temperature: { kind: ThermodynamicQuantity }
  kind:                               # a list when they carry only a name
    - ThermodynamicQuantity
    - MechanicalQuantity

modules:
  GenericPropertyOntology:
    title: The generic property ontology
    patterns:
      patterns.property_family: [ quantity ]        # positional
      patterns.aggregated_evaluation:               # by role
        statisticalModifier: aggregation
        property: quantity

default module: Ontology              # where a bare `specialize:` lands
specialize:                           # the first prototype's flat form
  patterns.legacy: [ quantity ]
```

| key | meaning |
|---|---|
| `base` | the namespace. `context.term("X")` is `base + "X"` |
| `prefixes` | prefix → IRI, for `context.resolve` and for serialisation. `dcterms` is added if absent |
| `import` | another configuration, merged **before** this one; later keys win. Cycles are ignored, not an error |
| `dimensions` | name → items. Items are a mapping (with data) or a list (names only) |
| `modules` | name → `{title, patterns}` |
| `modules.<M>.patterns` | pattern name → dimensions, as a list (positional) or a mapping role → dimension |
| `default module`, `specialize` | the flat form of the first prototype, kept working |

An unknown key at the top level is an error, with the file named: a
configuration that silently ignores a typo is a configuration you cannot debug.

## As a directory

One rule, applied recursively: **a directory is a mapping**, a file is one of
its entries, and a sub-directory is a nested mapping. The configuration above
is this tree:

```text
vocabulary/
  config.yaml                       base, prefixes, import
  dimensions/
    quantity/
      Temperature.yaml              { kind: ThermodynamicQuantity }
      Pressure.yaml
    kind/
      ThermodynamicQuantity.yaml    {}
  modules/
    GenericPropertyOntology.yml     title, patterns
  patterns.py                       left alone: not YAML
```

```text
gemov build vocabulary/ -o out/
gemov serve vocabulary/ --mount /seas
```

`config.yaml` (or `.yml`) is the one name with a meaning: **its keys belong to
the mapping that contains it**, which is where `base` and `prefixes` go. Every
other file takes its key from its own name without the extension. Hidden files
and anything that is not YAML are ignored, so a `README.md` and the
`patterns.py` the configuration names can live in the tree — and the tree's
directory is on the import path, as a file's directory is.

The point is not the syntax. A vocabulary of ninety-eight quantities in one
file is a file nobody reviews: a change to one quantity is then a diff in a
2 000-line document, and two people editing two quantities conflict. One file
per item makes a pull request read as what it does.

A cache keyed on the configuration keys on **every file of the tree**
(`config.sources`), because a directory's own mtime does not move when a file
inside it is edited.

## Naming a pattern

`module.function` — the directory of the configuration is put on the import
path, so `patterns.property_family` finds `patterns.py` (or `patterns.ldpy`)
next to it. A pattern declared as `@pattern("some-name")` may also be named
`some-name` directly.
