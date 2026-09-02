# The model, in one page

Four words carry everything, and they are worth fixing before anything else.

| word | what it is | in the configuration |
|---|---|---|
| **dimension** | a named set of things you vary over — the quantities, the aggregations, the kinds of device | `dimensions:` |
| **item** | one element of a dimension, with whatever data you attach to it | an entry under a dimension |
| **module** | an ontology you publish, with an IRI and a version | `modules:` |
| **pattern** | a Python function that mints terms for one combination of items | `patterns:` inside a module |

And two words that describe what comes out.

**Degree.** A pattern's arity: how many dimensions it is specialised on. A
pattern of degree 0 runs once, of degree 1 runs once per item, of degree 2 once
per pair. The degree is what a vocabulary costs — see
[the polynomial model](../why/polynomial.md).

**Role.** In a pattern of degree 2 or more, which dimension plays which part.
`statisticalModifier × property` is not the same as `property ×
statisticalModifier`, and naming the roles is what lets the two be told apart
by something other than argument order.

## How they fit

```text
dimensions ──┐
             ├── a pattern of degree n, once per combination ──> terms
items      ──┘                    │
                                  └── minted into exactly one module
```

Read on: [dimensions and items](dimensions.md) · [modules](modules.md) ·
[patterns, roles and degree](patterns.md) · [profiles](profiles.md).
