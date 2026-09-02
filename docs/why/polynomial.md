# The polynomial model

A module of an ontology can be read as a **polynomial over its dimensions**:

$$a_0 + a_1 x + a_2 x y + a_3 x y z + \dots$$

| degree | what it is | in GEMOV |
|---|---|---|
| $a_0$ | a graph that depends on no dimension — the upper classes, the annotation properties | a pattern of arity 0 |
| $a_1 x$ | one term per item of a dimension — `TemperatureProperty` | `[ quantity ]` |
| $a_2 x y$ | one term per pair — `AverageTemperatureEvaluation` | `[ aggregation, quantity ]` |
| $a_3 x y z$ | *the average temperature of the room over 24 h* | possible, and where everything changes |

**A pattern's degree is its arity**, so the model describes what GEMOV already
does. What it adds is a quantity nobody was looking at, and what that quantity
costs.

## What the degree costs

SEAS 1.0 carries 99 quantities, 51 modifiers and about 115 entities, in a
vocabulary of 632 classes:

```text
degree 1:  99                       ~ 10²
degree 2:  99 × 51 = 5 049          ~ 10³    eight times the vocabulary
degree 3:  99 × 51 × 115 = 580 635  ~ 10⁶    nine hundred times
```

The jump is not quantitative. At degree 3 you cannot mint names at all: not
document them, not maintain them, not load them. And SEAS knows it without
saying so — its 51 modifiers with no matching quantity are exactly the degree-2
monomials nobody dared expand.

## The decision: there is a degree beyond which you describe instead of naming

**Below the frontier, a vocabulary.** Terms with an IRI, a subsumption, a
documentation, a version. You mint them, you publish them, you commit to them.
GEMOV generates them.

**Above it, a grammar.** You do not mint `AverageRoomTemperatureOver24h`; you
describe the composition — a graph per instance, whose bricks are the terms of
the lower degrees. GEMOV then generates not terms but *what is needed to form
descriptions*: the admissible domain, and the legitimacy constraints.

Placing that frontier is the real work. "Degree ≤ 2 you name, ≥ 3 you describe"
is probably wrong as a rule: what decides is not the degree but the product of
the cardinalities, and the usage. `AverageTemperature` deserves a name because
people say it every day; `TendencyOfAtmosphereMolesOfLimonene` has one in SEAS
and nobody has ever said it.

## I-ADOPT names that frontier

[I-ADOPT](https://w3id.org/iadopt/ont) gives the vocabulary of the *describing*
side:

- a **`Variable`** is not a name but a composition — `hasObjectOfInterest`
  (an `Entity`), `hasProperty` (a `Property`), `hasStatisticalModifier`,
  `hasConstraint`, `hasMatrix`, `hasContextObject`. *The average temperature of
  the room over 24 h* is exactly that: four bricks of degree 1 and one
  composition;
- its roles are **named and ordered** — `hasSource`/`hasTarget`,
  `hasNumerator`/`hasDenominator`. That is a correction to the model, not a
  detail: **a monomial is not a product of dimensions, it is a product of
  dimensions with named roles.** GEMOV therefore lets a pattern
  [name the roles](../model/patterns.md#roles) of its dimensions;
- and `hasApplicableProperty`, `hasApplicableObjectOfInterest`,
  `hasApplicableStatisticalModifier` on a `System` declare **which compositions
  are legitimate** — the question a generator has to answer, already
  standardised.

## Where the metaphor breaks, and why it still holds

The coefficients are not numbers but graph templates, and the addition is graph
union: idempotent, with no inverse. So this is a semiring and not a ring, and
"polynomial" should be read as a **generating series** — it *counts* the
vocabulary, it does not compute it. That is exact, and it is enough: the
counting is what carries the argument.

Recorded as `pilotage/ottr/308`.
