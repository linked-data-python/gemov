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

## A module page carries its terms

A module's page is not a table of contents: it **is** the documentation of
the terms the module defines. Each one gets its label, its types, its IRI, its
comment and the relations that place it — *sub class of*, *domain*, *range*,
*domain of*, *range of*. That is what the 2016 SEAS site did, and what a
reader came for; a page that only links to elsewhere makes the reader open
one tab per term.

### Prose is Markdown

A published vocabulary's `dcterms:description` and `rdfs:comment` are prose,
and SEAS has written that prose in Markdown since 2016 — links, images, bullet
lists and fenced Turtle examples. It is rendered. Showing the reader
`[SSN](http://…)` where the 2016 site showed a link is not a cosmetic loss:
in SEAS the examples *are* the documentation.

RDF says one thing about the **form** of a literal, and it is the datatype:
`rdf:HTML` is markup and goes in as it is, everything else is prose and is
rendered as Markdown. A language tag says which *language* the prose is in,
never which syntax — `"…"@en` is rendered like any other literal. Guessing the
syntax from the text was considered and rejected: it would make the rendering
of a comment depend on whether it happens to contain a backtick.

The dependency is optional. Without `markdown` installed the prose is escaped
and shown as written.

A link the prose writes **into the vocabulary's own namespace** becomes a link
into the site. SEAS writes `https://w3id.org/seas/SSNAlignment` and
`https://w3id.org/seas/featureofinterest.png`, and it is right to — an IRI is
not a path. But a page *of that namespace* that keeps them absolute sends its
own reader back out to whatever answers there, which is how a preview, a
static export or a deployment on another host ends up with broken figures. A
tail with a file extension is a file and is linked as it is; anything else is
a term and takes the site's suffix. Links out of the namespace are untouched.

### The order of the terms — `--order`

Two policies, and which one is right is a question about the vocabulary, not
about the tool.

`kind` *(default)* groups the terms — Classes, then Properties, then the rest
— and sorts each group alphabetically. This is what the 2016 site did. It is
easy to scan, and it is what a reader of the published SEAS is used to.

`source` follows the order the terms were **written** in, flat. An RDF graph
has no order, so it is read back from the Turtle: the first line that begins
with the term. A generated vocabulary has no text and needs none — the
patterns minted its terms in an order, and that order is the product of the
dimensions.

The difference is not stylistic. `GenericPropertyOntology` writes

```turtle
seas:TemperatureProperty a owl:Class ; …
seas:TemperatureEvaluation a owl:Class ; …
seas:temperature a owl:ObjectProperty , owl:FunctionalProperty ; …
```

— a quantity's three terms together, then the next quantity. `kind` scatters
each of those families across two sections and eleven screens; `source` keeps
them where their author put them. And it is the same order a pattern produces,
which is why the choice survives the move from a hand-written vocabulary to a
generated one.

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
