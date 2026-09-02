# Dimensions and items

A **dimension** is a named set of things a vocabulary varies over. A
**item** is one element of it, and it carries whatever data the patterns will
need — a label, a unit, a parent, a link to another dimension.

```yaml
dimensions:
  quantity:
    Temperature: { kind: ThermodynamicQuantity, unit: "unit:DEG_C" }
    Humidity:    { kind: ThermodynamicQuantity }
    Pressure:    { kind: MechanicalQuantity, unit: "unit:PA" }
  aggregation:
    Average: {}
  kind:
    - ThermodynamicQuantity
    - MechanicalQuantity
```

Two spellings, and they mean the same thing: a **mapping** when the items carry
data, a **list** when they carry nothing but their name. The list form is
sugar for a mapping to empty values.

## What a pattern receives

An item reaches a pattern as an `Item` object:

```python
@pattern
def property_family(context, quantity):
    quantity.key             # "Temperature" — the identifier the names use
    quantity.value           # {"kind": "ThermodynamicQuantity", ...}
    quantity.get("unit")     # None when the item does not carry it
    quantity.dimension       # "quantity"
    key, value = quantity    # it unpacks, for the terse cases
```

`key` is what naming rules are built from, and it must be usable in an IRI.
`value` is yours: GEMOV never looks inside it.

## Sharing dimensions between configurations

`import` merges another configuration before the current one, so a vocabulary
of dimensions lives in one file and the modules that use it in others:

```yaml
# quantities.yml — nothing but the dimension
dimensions:
  quantity: { Temperature: {}, Humidity: {} }
```

```yaml
# vocabulary.yml
import: quantities.yml
modules:
  GenericPropertyOntology:
    patterns: { patterns.property_family: [ quantity ] }
```

Keys already present win over the imported ones, so an importer refines
rather than being overridden. An `import` cycle is not an error: a file is
merged once.

## A dimension is not a class

It is worth saying, because the temptation is strong: a dimension is a
*generation-time* set. It does not have to appear in the output at all. In the
SEAS example the `kind` dimension does produce terms — through a pattern of its
own — while `aggregation` produces one term per item and mostly exists to be
crossed with `quantity`. What a dimension produces is decided by the patterns
you specialise on it, not by declaring it.
