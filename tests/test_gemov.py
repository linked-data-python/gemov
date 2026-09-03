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
    """Asked for the way gemov asks: a pattern module is imported under a
    name of its own, so `import patterns` is not the same object."""
    from gemov.patterns import load
    context = config().generate()
    assert context.degree(load("patterns.upper").gemov_pattern) == 0
    assert context.degree(load("patterns.property_family").gemov_pattern) == 1
    assert context.degree(
        load("patterns.aggregated_evaluation").gemov_pattern) == 2


def test_two_vocabularies_may_each_have_a_patterns_module(tmp_path):
    """gemov serves two vocabularies in one process. Importing both pattern
    modules as `patterns` gave the second one the first one's functions, and
    the error pointed at the innocent file."""
    from gemov.patterns import load, add_search_path
    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / "patterns.py").write_text(
        "from gemov import pattern\n\n\n"
        "@pattern\ndef only_here(context):\n    pass\n")
    first = load("patterns.property_family")
    add_search_path(str(other))
    assert load("patterns.only_here").__name__ == "only_here"
    add_search_path(os.path.join(ROOT, "examples", "seas"))
    assert load("patterns.property_family") is first


# ------------------------------------------- a configuration as a directory

def _tree(root):
    """The example vocabulary, written as a directory instead of a file."""
    (root / "dimensions" / "quantity").mkdir(parents=True)
    (root / "dimensions" / "aggregation").mkdir(parents=True)
    (root / "modules").mkdir()
    (root / "config.yaml").write_text(
        "base: https://w3id.org/seas/\n"
        "prefixes:\n  seas: https://w3id.org/seas/\n")
    (root / "dimensions" / "quantity" / "Temperature.yaml").write_text(
        "kind: ThermodynamicQuantity\n")
    (root / "dimensions" / "quantity" / "Pressure.yml").write_text(
        "kind: MechanicalQuantity\n")
    (root / "dimensions" / "aggregation" / "Average.yaml").write_text("{}\n")
    (root / "modules" / "GenericPropertyOntology.yml").write_text(
        "title: The SEAS generic property ontology\n"
        "patterns:\n  patterns.property_family: [ quantity ]\n")
    (root / "README.md").write_text("not a configuration file\n")
    return root


def test_a_directory_is_a_configuration(tmp_path):
    """One rule: a directory is a mapping, a file is one of its entries.

    A vocabulary of ninety-eight quantities stops being one file nobody can
    review — a change to one quantity is a change to one file."""
    from gemov import Config
    config = Config.load(str(_tree(tmp_path / "vocabulary")))
    assert config.base == "https://w3id.org/seas/"
    assert config.prefixes["seas"] == "https://w3id.org/seas/"
    assert sorted(config.dimensions["quantity"]) == ["Pressure", "Temperature"]
    assert config.dimensions["quantity"]["Temperature"] == {
        "kind": "ThermodynamicQuantity"}
    assert sorted(config.dimensions["aggregation"]) == ["Average"]
    assert list(config.modules) == ["GenericPropertyOntology"]


def test_the_tree_and_the_file_mean_the_same_thing(tmp_path):
    from gemov import Config
    tree = Config.load(str(_tree(tmp_path / "vocabulary")))
    flat = tmp_path / "vocabulary.yml"
    flat.write_text(
        "base: https://w3id.org/seas/\n"
        "prefixes:\n  seas: https://w3id.org/seas/\n"
        "dimensions:\n"
        "  quantity:\n"
        "    Temperature: { kind: ThermodynamicQuantity }\n"
        "    Pressure: { kind: MechanicalQuantity }\n"
        "  aggregation:\n    Average: {}\n"
        "modules:\n  GenericPropertyOntology:\n"
        "    title: The SEAS generic property ontology\n"
        "    patterns:\n      patterns.property_family: [ quantity ]\n")
    other = Config.load(str(flat))
    assert tree.base == other.base
    assert tree.dimensions == other.dimensions
    assert tree.modules == other.modules


def test_what_is_not_yaml_is_left_alone(tmp_path):
    """A `README.md` or a `patterns.py` may live in the tree."""
    from gemov.config import read_tree
    root = _tree(tmp_path / "vocabulary")
    assert "README" not in read_tree(str(root))


def test_the_cache_sees_every_file_of_the_tree(tmp_path):
    """A directory's own mtime does not move when a quantity inside it is
    edited; a cache keyed on it would serve a stale page."""
    from gemov import Config
    root = _tree(tmp_path / "vocabulary")
    config = Config.load(str(root))
    names = {os.path.basename(p) for p in config.sources}
    assert {"config.yaml", "Temperature.yaml", "Pressure.yml",
            "GenericPropertyOntology.yml"} <= names


def test_config_yaml_must_be_a_mapping(tmp_path):
    from gemov.config import read_tree
    root = tmp_path / "vocabulary"
    root.mkdir()
    (root / "config.yaml").write_text("- a list\n")
    with pytest.raises(ValueError) as exc:
        read_tree(str(root))
    assert "belong to the directory" in str(exc.value)


def test_a_directory_with_no_yaml_is_not_a_key(tmp_path):
    """Importing the `patterns.py` a vocabulary names leaves a `__pycache__`
    next to it, and it is not part of the configuration."""
    from gemov.config import read_tree
    root = _tree(tmp_path / "vocabulary")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "patterns.cpython-312.pyc").write_bytes(b"\x00")
    (root / "empty").mkdir()
    tree = read_tree(str(root))
    assert "__pycache__" not in tree and "empty" not in tree
    assert "dimensions" in tree and "modules" in tree


def test_a_module_may_carry_its_own_metadata(tmp_path):
    """A generated module that says nothing about itself is visibly poorer
    than a hand-written one on its own page, and a vocabulary that is partly
    generated should not be readable as two halves."""
    from gemov import Config
    from rdflib import Literal, URIRef
    from rdflib.namespace import DCTERMS
    root = tmp_path / "vocabulary"
    (root / "modules").mkdir(parents=True)
    (root / "config.yaml").write_text(
        "base: https://w3id.org/seas/\n"
        "prefixes:\n  dcterms: http://purl.org/dc/terms/\n")
    (root / "modules" / "ZoneOntology.yml").write_text(
        "title: The SEAS Zone ontology\n"
        "dcterms:description: A zone is a part of space.\n"
        "dcterms:license: https://www.apache.org/licenses/LICENSE-2.0\n")
    context = Config.load(str(root)).generate()
    iri = URIRef("https://w3id.org/seas/ZoneOntology")
    graph = context.modules["ZoneOntology"]
    assert (iri, DCTERMS.description,
            Literal("A zone is a part of space.", lang="en")) in graph
    assert (iri, DCTERMS.license,
            URIRef("https://www.apache.org/licenses/LICENSE-2.0")) in graph
    assert (iri, DCTERMS.title,
            Literal("The SEAS Zone ontology", lang="en")) in graph
