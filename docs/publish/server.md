# Serving the namespace

```text
gemov serve vocabulary.yml                              # a generated vocabulary
gemov serve --files ontologies/ --namespace https://w3id.org/seas/ --prefix seas
```

A vocabulary published under **one namespace**, **modular** and **versioned**,
has to answer for every IRI under that namespace. This is that server. The
source is either a gemov configuration or a directory of `Module-x.y.ttl`
files, and **the contract below is the same either way**.

## The access contract

| IRI | denotes | answer |
|---|---|---|
| `…/` | the vocabulary | **200** — an index of the modules |
| `…/BuildingOntology` | the module | **200** — its current version, with `Content-Location` naming the versioned IRI |
| `…/BuildingOntology-0.9` | that version of the module | **200** |
| `…/BuildingOntology-0` | the highest version with that major | **302** to the full version |
| `…/EndNode` | a term | **200** — its definition, from the module version that claims it |

Two rules cut across all of them.

**Content negotiation.** `Accept` decides among `text/turtle`,
`application/rdf+xml`, `application/ld+json`, `application/n-triples` and
`text/html`, and every answer carries `Vary: Accept` so that a shared cache
never serves HTML to a parser.

**An extension wins over `Accept`.** `…/BuildingOntology.ttl` and
`…/EndNode.html` name a representation directly — for a browser's address bar,
or a `curl` with no headers. SAREF publishes the same rule as `.conneg`
rewrites in Apache; here it is one function, and it is tested.

### Why the unversioned IRI is served and not redirected

SAREF redirects `core/` to `core/v3.1.1/`. This server does not, and the
difference is deliberate: the unversioned IRI **denotes the module itself**,
and dereferencing it gives the current version of that module. A redirect
would say instead that the module *is* its current version, which is false as
soon as there are two. `Content-Location` names the version actually served, so
a client that wants to pin one can follow it.

## Views

```text
/view?module=GenericPropertyOntology&term=Property&closure=1
/view?dimension=quantity=Temperature&dimension=kind=MechanicalQuantity
```

`module=`, `term=` (or `element=`) and `dimension=` may repeat. With
`closure=1` the graph is completed and the page lists what was pulled in and
why. On a generated vocabulary, `dimension=` is the
[profile](../model/profiles.md): the product is restricted, so what is not
asked for is never minted. On a source that is files there is nothing to
re-run, and asking for a dimension is a `400` that says so.

Views negotiate like everything else.

## Pattern pages

A generated vocabulary also serves `/patterns` and `/pattern-<name>` — see
[generated documentation](documentation.md).

## Notes for deployment

- an application is built **per source** (`build_app`, `from_files`,
  `from_config`), so several vocabularies can be served in one process, and
  there is no global state to trip over;
- pages are cached, with `ETag` and `304`; `/cache` reports the statistics;
- for a vocabulary that never changes, `gemov docs` writes the same pages as
  files and any static server will do. The server exists for the views, which
  cannot be enumerated in advance.

## Installing

```text
pip install gemov[server]
```
