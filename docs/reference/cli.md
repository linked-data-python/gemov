# Command line

```text
gemov build   CONFIG [-o OUT] [--format turtle]
gemov profile CONFIG dimension=Item[,Item] … [-o OUT] [--explain]
gemov check   CONFIG
gemov docs    CONFIG [-o site] [--prefix P] [--brand B] [--order O]  # [docs]
gemov serve   CONFIG [--host H] [--port N] [--prefix P]        # needs [server]
gemov serve   --files DIR… --namespace IRI [--prefix P]        # needs [server]
              [--mount /path] [--brand B] [--assets DIR] [--order O]
```

Every entry point is also `python -m gemov.cli …`.

## `build`

Runs every pattern of every module. Without `-o`, the whole vocabulary goes to
stdout in one graph; with `-o`, one file per module and a line per file.

## `profile`

```text
gemov profile vocabulary.yml quantity=Temperature kind=MechanicalQuantity --explain
```

Selects, closes and explains — see [profiles](../model/profiles.md).
`--explain` writes the explanation to stderr, so the graph on stdout stays
pipeable.

## `check`

Prints one finding per line and exits `1` if there is any. See
[how to check](../guides/check.md).

## `docs`

Writes the documentation site. `--prefix` is the prefix used for compact IRIs
in the pages (`seas:Temperature`).

## `serve`

Serves the namespace over HTTP — see [the server](../publish/server.md). Give
a configuration for a generated vocabulary, or `--files` with `--namespace` for
a directory of `Module-x.y.ttl`.

`--prefix` and `--mount` are unrelated and easy to confuse: the first is the
prefix of a compact IRI shown in a page (`seas:Temperature`), the second is
the path the site is served under (`/seas/EndNode`).

`--brand` names a YAML file — a logo, a name, the project the logo links to,
a footer note and two colours — and `--assets` a directory published under
`<mount>/static/`, which is where the logo is found. `gemov docs` takes the
same `--brand` for the static site.

`--order` is `kind` (default) or `source` — how a module lays out the terms it
defines; see [generated documentation](../publish/documentation.md).
