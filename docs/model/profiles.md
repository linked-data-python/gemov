# Profiles

A **profile** is what a user gets when they ask for part of the vocabulary: not
the ninety-nine quantities, only the two they work with. It is an operation in
three steps, and each one is there for a reason.

## 1. Selection — what is not asked for is never minted

```python
from gemov import Config, profile
config = Config.load("vocabulary.yml")
part = profile.build(config, {"quantity": ["Temperature"]})
```

Generation runs **again** with the dimensions restricted to the selection. The
cartesian product shrinks; nothing is generated and then filtered. On a large
vocabulary that is the difference between a second and a minute, and on a
degree-3 pattern it is the difference between possible and not.

## 2. Closure — the profile stands on its own

The selection mints terms that refer to terms it did not mint: a parent class
in another module, an alignment target, a quantity kind that was not selected.
Their definitions are pulled from the full generation, transitively, following
blank nodes — an OWL restriction is part of the term that carries it.

## 3. Explanation — a profile is justified, not trusted

Every term the closure added comes with the term that pulled it in.

```text
$ gemov profile vocabulary.yml quantity=Temperature kind=MechanicalQuantity --explain
9 terms selected, 1 added to close the profile
  https://w3id.org/seas/ThermodynamicQuantity
      because https://w3id.org/seas/TemperatureProperty refers to it
```

Nobody has to wonder why a term is in a profile they were handed.

## Over HTTP

The [server](../publish/server.md) exposes the same operation as a *view*:

```text
/view?dimension=quantity=Temperature&dimension=kind=MechanicalQuantity
/view?module=GenericPropertyOntology&term=Property&closure=1
```

On a generated vocabulary a view selects dimension items, which is the profile
above. On a vocabulary that is a directory of files there is nothing to re-run,
and a view is the modules and terms named, closed.

## The limit, and where it leads

Below a certain degree a profile is a *subset of terms*, which is what this
page describes. Above it — when a term is a composition rather than a name —
a profile becomes a *domain of expression*: not "here are the terms" but "here
are the variables you can form, and why those". That is
[the polynomial model](../why/polynomial.md), and it is not implemented yet.
