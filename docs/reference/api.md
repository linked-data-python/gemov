# Python API

```python
from gemov import Config, ExecutionContext, Item, OwnershipError, pattern
from gemov import check, profile
```

## `Config`

| | |
|---|---|
| `Config.load(path)` | read a configuration, `import` resolved |
| `.base`, `.prefixes`, `.dimensions`, `.modules` | what it says |
| `.context()` | a fresh `ExecutionContext` for it |
| `.generate(selection=None, context=None)` | run every pattern; returns the context |

`selection` is `{dimension: iterable of item keys}` — what a profile restricts.

## `ExecutionContext`

What a pattern writes into.

| | |
|---|---|
| `mint(local, *triples)` | claim a term for the current module and define it |
| `term(local)`, `resolve(curie)` | IRIs |
| `graph`, `module`, `module_iri(name=None)` | the module being generated |
| `modules` | name → `Graph` |
| `owner` | IRI → module name |
| `minted` | module → the terms it minted, in order |
| `roles` | pattern → `{role: dimension}` |
| `home` | pattern → its module, fixed before anything runs |
| `degree(fn)` | the arity of a pattern |
| `all_triples()` | every module in one graph |

`OwnershipError` is raised when two modules mint the same term.

## `Item`

One element of a dimension: `.key`, `.value`, `.dimension`, `.get(field)`, and
it unpacks as `(key, value)`.

## `pattern`

```python
@pattern
def f(context, quantity): ...

@pattern("named-in-the-configuration")
def g(context, *, statisticalModifier, property): ...
```

## `profile`

```python
result = profile.build(config, {"quantity": ["Temperature"]})
result.graph, result.selected, result.closure, result.why
result.explain()
```

## `check`

```python
findings = check.check(context)       # sorted, de-duplicated, [] when clean
finding.rule, finding.term, finding.message
```

## `gemov.doc` (extra `docs`)

`write_site(source, directory, prefix, config)`, and `render_index`,
`render_module`, `render_term`, `render_pattern`, `render_patterns_index`;
`describe`, `module_contents`, `ontology_header` are the ldpy queries.

## `gemov.server` (extra `server`)

`from_config(config, prefix)`, `from_files(directories, namespace, prefix)`
and `build_app(source, prefix, config)` return a Flask application.
`Files` and `Generated` are the two sources.
