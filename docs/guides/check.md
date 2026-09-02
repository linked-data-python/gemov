# How to check a vocabulary

```text
gemov check vocabulary.yml
```

Prints one line per finding and exits non-zero if there is any. Every rule was
written after measuring the published SEAS 1.0, where each of them is violated
at least once — a generator that does not check these buys nothing over a text
editor.

| rule | what it catches | in SEAS 1.0 |
|---|---|---|
| `label-space` | a label with a leading or trailing space | 79 labels |
| `label-lang` | a label with no language tag | |
| `no-label` | a term with no `rdfs:label` | |
| `no-type` | a term minted with no OWL type | |
| `no-defined-by` | no `rdfs:isDefinedBy` | |
| `wrong-module` | `rdfs:isDefinedBy` pointing at another module than the one that mints it | 11 terms |
| `term-status` | a `vs:term_status` outside its closed vocabulary | `test` for `testing`, 9 times |
| `dangling` | an IRI in the namespace that no module mints | how the "a module declares itself" rule was found |

## In Python

```python
from gemov import Config, check

context = Config.load("vocabulary.yml").generate()
findings = check.check(context)
for finding in findings:
    print(finding.rule, finding.term, finding.message)
assert not findings
```

`check.check` returns a list, sorted and de-duplicated; an empty list is the
passing case. Putting that assertion in your test suite is the point: a
vocabulary that has to be checked by hand will not be.

## Two invariants you cannot switch off

They raise instead of reporting, because a result that violates them is not a
vocabulary with a defect but a vocabulary that does not exist:

- **a term belongs to one module** — `OwnershipError`;
- **a pattern mints into one module** — `ValueError`, raised before anything
  runs.

See [modules](../model/modules.md).
