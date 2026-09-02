# Generated documentation

```text
gemov docs vocabulary.yml -o site/ --prefix ex
```

Writes a static site: one page per term, one per module, one index — and one
per **pattern**.

## The shape, and where it comes from

[`saref-pypeline`](https://labs.etsi.org/rep/saref/saref-pypeline) generates
<https://saref.etsi.org/> by rewriting [pyLODE](https://github.com/RDFLib/pyLODE)'s
output in its own HTML. GEMOV does the same thing again, and keeps the shape
that work settled: a title, a summary of what the thing is — IRI, type, status,
defining module — and then the definition broken into sections: *sub class of*,
*equivalent to*, *sub classes*, *in the domain of*, *in the range of*, *sub
properties*.

What it does not keep is the machinery: no framework, one stylesheet, and the
queries in [Linked-Data Python](../guides/ldpy.md), because what a documentation
page needs from an ontology is a handful of graph patterns and they should read
as such:

```ldpy
parents  = [str(o) for o in m{ {term} rdfs:subClassOf ?p }]
children = [str(s) for s in m{ ?s rdfs:subClassOf {term} }]
range_of = [str(s) for s in m{ ?s rdfs:range {term} }]
```

## The page a hand-written ontology cannot have

A generated vocabulary knows *why* each family of terms exists, so it can
document the rule next to the results. A pattern's page gives its docstring,
the module it mints into, its **degree**, and the **roles** of its dimensions:

```text
Pattern aggregated_evaluation                     a rule, not a term — degree 2

Defined in   patterns
Mints into   StatisticsOntology
Degree       2 — one term family per aggregation × quantity
Roles        statisticalModifier   dimension aggregation
             property              dimension quantity
```

That is the documentation a reader of a generated ontology actually wants, and
it is the reason to generate one rather than write it.

## The cache

Pages are kept, and the invalidation rule is one line, which is the only kind
worth having: **a page is keyed by what it was built from** — the mtimes of the
Turtle files for a source that is files, the configuration for a generated one.
Served by [the server](server.md), a page carries an `ETag`, and a client that
already has it gets `304`. `/cache` reports hits, misses and entries.

## In Python

```python
from gemov import Config
from gemov.doc import write_site
from gemov.server.source import Generated

config = Config.load("vocabulary.yml")
write_site(Generated(config), "site/", prefix="ex", config=config)
```

`render_term`, `render_module`, `render_index`, `render_pattern` are available
individually if you want to put the pages somewhere else.

## Installing

```text
pip install gemov[docs]
```
