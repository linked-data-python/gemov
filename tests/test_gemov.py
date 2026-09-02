"""The invariants of gemov, on the SEAS example of record ottr/302."""

import os
import subprocess
import sys

import pytest
from rdflib import RDFS, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF

from gemov import Config, ExecutionContext, OwnershipError, check, pattern
from gemov import profile as profile_mod

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEAS = os.path.join(ROOT, "examples", "seas")
NS = "https://w3id.org/seas/"


def config(name="vocabulary.yml"):
    return Config.load(os.path.join(SEAS, name))


def term(local):
    return URIRef(NS + local)


# ------------------------------------------------------- the product itself

def test_the_cartesian_product_is_what_record_302_asks_for():
    context = config().generate()
    graph = context.all_triples()
    for quantity in ("Temperature", "Humidity", "Pressure"):
        assert (term("Average" + quantity + "Evaluation"), RDF.type,
                OWL.Class) in graph
        assert (term("Average" + quantity + "Evaluation"), RDFS.subClassOf,
                term(quantity + "Evaluation")) in graph
        assert (term("Average" + quantity + "Evaluation"), RDFS.subClassOf,
                term("AverageEvaluation")) in graph


def test_a_pattern_with_no_dimension_runs_once():
    context = config().generate()
    assert len(list(context.all_triples().objects(term("Property"),
                                                  RDF.type))) == 1


# ------------------------------------------------------------- ownership

def test_a_term_belongs_to_the_module_its_pattern_is_assigned_to():
    context = config().generate()
    assert context.owner[term("TemperatureProperty")] == "GenericPropertyOntology"
    assert context.owner[term("AverageTemperatureEvaluation")] == "StatisticsOntology"
    assert context.owner[term("ThermodynamicQuantity")] == "QuantityKindVocabulary"


def test_ownership_does_not_depend_on_the_order_of_the_modules():
    """`aggregated_evaluation` calls `property_family`. Whichever module runs
    first, the quantity's terms must land in the module the configuration
    assigns to `property_family` — otherwise two runs disagree."""
    normal = config()
    reversed_ = config()
    reversed_.modules = dict(reversed(list(reversed_.modules.items())))
    a, b = normal.generate(), reversed_.generate()
    assert a.owner == b.owner
    assert isomorphic(a.all_triples(), b.all_triples())


def test_two_modules_minting_the_same_term_is_an_error():
    """Two patterns, two modules, one term: the second mint is refused rather
    than merged, because a term is defined in one place."""
    context = ExecutionContext(base=NS)

    @pattern
    def here(ctx):
        ctx.mint("Clash", (RDF.type, OWL.Class))

    @pattern
    def there(ctx):
        ctx.mint("Clash", (RDF.type, OWL.Class))

    context.run("A", here, [])
    with pytest.raises(OwnershipError, match="belongs to"):
        context.run("B", there, [])


def test_the_same_specialisation_runs_once_across_modules():
    """The dedup is by (pattern, arguments): a pattern reached twice adds its
    triples once. A configuration that assigns it to two modules is caught
    earlier, by `test_a_pattern_assigned_to_two_modules_is_refused`."""
    calls = []
    context = ExecutionContext(base=NS)

    @pattern
    def once(ctx):
        calls.append(ctx.module)
        ctx.mint("Once", (RDF.type, OWL.Class))

    context.run("A", once, [])
    context.run("B", once, [])
    assert calls == ["A"]


def test_a_pattern_assigned_to_two_modules_is_refused():
    conf = config()
    conf.modules["Elsewhere"] = {"title": None,
                                 "patterns": {"patterns.property_family":
                                              ["quantity"]}}
    with pytest.raises(ValueError, match="mints into one module"):
        conf.generate()


# ---------------------------------------------------------------- profile

def test_a_profile_leaves_out_what_was_not_asked_for():
    conf = config()
    result = profile_mod.build(conf, {"quantity": ["Temperature"],
                                      "kind": ["MechanicalQuantity"]})
    subjects = set(result.graph.subjects())
    assert term("TemperatureProperty") in subjects
    assert term("HumidityProperty") not in subjects
    assert term("AverageHumidityEvaluation") not in subjects
    assert len(result.graph) < len(conf.generate().all_triples())


def test_a_profile_is_closed_and_says_why():
    """`TemperatureProperty` points at a quantity kind the selection excluded;
    the profile pulls it in, and names the term that pulled it."""
    result = profile_mod.build(config(), {"quantity": ["Temperature"],
                                          "kind": ["MechanicalQuantity"]})
    assert term("ThermodynamicQuantity") in result.closure
    assert result.why[term("ThermodynamicQuantity")] == term("TemperatureProperty")
    assert (term("ThermodynamicQuantity"), RDF.type, OWL.Class) in result.graph
    assert "because" in result.explain()


def test_a_profile_refuses_an_unknown_selection():
    with pytest.raises(ValueError, match="no item"):
        profile_mod.build(config(), {"quantity": ["Luminance"]})
    with pytest.raises(ValueError, match="no dimension"):
        profile_mod.build(config(), {"colour": ["Red"]})


# ------------------------------------------------------------------ check

def test_the_example_is_coherent():
    assert check.check(config().generate()) == []


def test_the_checks_catch_what_hand_writing_produces():
    """Every rule below is violated by the published SEAS 1.0."""
    from rdflib import Literal
    context = ExecutionContext(base=NS)
    VS = URIRef("http://www.w3.org/2003/06/sw-vocab-status/ns#term_status")

    @pattern
    def sloppy(ctx):
        bad = ctx.mint("Bad", (RDF.type, OWL.Class))
        ctx.graph.add((bad, RDFS.label, Literal(" Bad Class", lang="en")))
        ctx.graph.add((bad, VS, Literal("test")))
        ctx.mint("Untyped")
        ctx.graph.add((ctx.term("Untyped"), RDFS.label, Literal("Untyped")))

    context.run("M", sloppy, [])
    rules = {f.rule for f in check.check(context)}
    assert {"label-space", "term-status", "no-type", "no-defined-by",
            "label-lang"} <= rules


# ------------------------------------------------------------------- ldpy

def test_patterns_written_in_ldpy_give_the_same_graph():
    """gemov calls rdflib; a pattern's author may write the triples in
    Turtle's notation instead. The two must be the same ontology."""
    pytest.importorskip("ldpy")
    a = config("vocabulary.yml").generate().all_triples()
    b = config("vocabulary-ldpy.yml").generate().all_triples()
    assert isomorphic(a, b)


# ------------------------------------------------------------ config & CLI

def test_import_merges_dimensions_and_modules(tmp_path):
    (tmp_path / "base.yml").write_text(
        "base: https://e/\ndimensions:\n  d:\n    A: {}\n", encoding="utf-8")
    (tmp_path / "top.yml").write_text(
        "import: base.yml\ndimensions:\n  d:\n    B: {}\n", encoding="utf-8")
    conf = Config.load(str(tmp_path / "top.yml"))
    assert set(conf.dimensions["d"]) == {"A", "B"}
    assert conf.base == "https://e/"


def test_an_unknown_key_in_the_configuration_is_refused(tmp_path):
    (tmp_path / "c.yml").write_text("dimensionz: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown key"):
        Config.load(str(tmp_path / "c.yml"))


def test_the_command_line_builds_checks_and_profiles(tmp_path):
    env = dict(os.environ, PYTHONPATH=ROOT)
    run = lambda *a: subprocess.run([sys.executable, "-m", "gemov.cli", *a],
                                    capture_output=True, text=True, env=env,
                                    cwd=ROOT)
    built = run("build", os.path.join(SEAS, "vocabulary.yml"),
                "-o", str(tmp_path))
    assert built.returncode == 0 and (tmp_path / "UpperOntology.ttl").exists()
    assert run("check", os.path.join(SEAS, "vocabulary.yml")).returncode == 0
    prof = run("profile", os.path.join(SEAS, "vocabulary.yml"),
               "quantity=Temperature", "--explain")
    assert prof.returncode == 0 and "seas:TemperatureProperty" in prof.stdout
    assert "HumidityProperty" not in prof.stdout


# ------------------------------------------------------------------ roles

def test_a_pattern_can_take_its_dimensions_by_role():
    """Record ottr/308: a monomial is a product of dimensions with named
    roles, so `x·y` and `y·x` are told apart by name and not by position."""
    seen = {}
    context = ExecutionContext(base=NS)

    @pattern
    def variable(context, *, statisticalModifier, property):
        seen[(statisticalModifier.key, property.key)] = True
        context.mint(statisticalModifier.key + property.key,
                     (RDF.type, OWL.Class))

    context.dimensions = {"aggregation": {"Average": {}},
                          "quantity": {"Temperature": {}, "Pressure": {}}}
    context.run("M", variable, {"statisticalModifier": "aggregation",
                                "property": "quantity"})
    assert seen == {("Average", "Temperature"): True,
                    ("Average", "Pressure"): True}
    assert context.roles[variable.gemov_pattern] == {
        "statisticalModifier": "aggregation", "property": "quantity"}
    assert context.degree(variable.gemov_pattern) == 2


def test_the_degree_of_a_pattern_is_its_arity():
    context = config().generate()
    from importlib import import_module
    patterns = import_module("patterns")
    assert context.degree(patterns.upper.gemov_pattern) == 0
    assert context.degree(patterns.property_family.gemov_pattern) == 1
    assert context.degree(patterns.aggregated_evaluation.gemov_pattern) == 2
