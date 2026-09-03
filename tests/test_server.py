"""The access contract, the views and the cache — as tests.

    python -m pytest server/test_server.py

Every assertion below is a clause of the contract written in app.py's
docstring. If one of them fails, the contract has changed and the docstring
is wrong.
"""

import os

import pytest

flask = pytest.importorskip("flask")

from gemov import Config                                          # noqa: E402
from gemov.server import from_config, from_files                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEAS_NS = "https://w3id.org/seas/"
#: the published SEAS 1.0, next to this repository — a source that is files
SOURCES = os.path.normpath(os.path.join(ROOT, "..", "seas", "src", "main",
                                        "ontop", "1.0"))
EXAMPLE = os.path.join(ROOT, "examples", "seas", "vocabulary.yml")

pytestmark = pytest.mark.skipif(not os.path.isdir(SOURCES),
                                reason="the SEAS sources are not next door")


@pytest.fixture(scope="module")
def client():
    application = from_files([SOURCES], SEAS_NS, "seas")
    application.config["TESTING"] = True
    return application.test_client()


def cache_of(client):
    return client.application.config["CACHE"]


@pytest.fixture(scope="module")
def generated():
    """The other kind of source: a vocabulary generated from patterns."""
    application = from_config(Config.load(EXAMPLE), "seas")
    application.config["TESTING"] = True
    return application.test_client()


# ------------------------------------------------------- the four IRI kinds

def test_the_index_lists_the_modules(client):
    page = client.get("/")
    assert page.status_code == 200
    assert b"GenericPropertyOntology" in page.data


def test_an_unversioned_module_serves_the_latest_and_says_which(client):
    page = client.get("/GenericPropertyOntology")
    assert page.status_code == 200
    assert page.headers["Content-Location"] == "/GenericPropertyOntology-1.0"
    assert page.headers["Vary"] == "Accept"


def test_a_versioned_module_is_canonical(client):
    page = client.get("/GenericPropertyOntology-1.0")
    assert page.status_code == 200
    assert "Content-Location" not in page.headers


def test_a_partial_version_redirects_to_the_full_one(client):
    page = client.get("/GenericPropertyOntology-1")
    assert page.status_code == 302
    assert page.headers["Location"].endswith("/GenericPropertyOntology-1.0")


def test_a_term_is_served_from_the_module_that_claims_it(client):
    page = client.get("/TemperatureProperty.ttl")
    assert page.status_code == 200
    assert b"TemperatureProperty" in page.data
    assert page.headers["Content-Location"].startswith("/GenericPropertyOntology")


def test_an_unknown_iri_is_404(client):
    assert client.get("/NoSuchTerm").status_code == 404


# ----------------------------------------------------------- negotiation

@pytest.mark.parametrize("accept,expected", [
    ("text/turtle", "text/turtle"),
    ("application/rdf+xml", "application/rdf+xml"),
    ("application/ld+json", "application/ld+json"),
    ("application/n-triples", "application/n-triples"),
    ("text/html", "text/html"),
])
def test_accept_decides_the_representation(client, accept, expected):
    page = client.get("/GenericPropertyOntology", headers={"Accept": accept})
    assert page.status_code == 200
    assert page.headers["Content-Type"].startswith(expected)


@pytest.mark.parametrize("ext,expected", [
    ("ttl", "text/turtle"), ("rdf", "application/rdf+xml"),
    ("jsonld", "application/ld+json"), ("nt", "application/n-triples"),
    ("html", "text/html"),
])
def test_an_extension_wins_over_accept(client, ext, expected):
    """A browser sends `Accept: text/html`; `.ttl` must still give Turtle."""
    page = client.get("/GenericPropertyOntology.%s" % ext,
                      headers={"Accept": "text/html"})
    assert page.headers["Content-Type"].startswith(expected)


def test_every_answer_varies_on_accept(client):
    for url in ("/", "/GenericPropertyOntology", "/TemperatureProperty"):
        assert client.get(url).headers["Vary"] == "Accept"


# ----------------------------------------------------------------- views

def test_a_view_of_one_module(client):
    page = client.get("/view?module=GenericPropertyOntology-1.0&"
                      "closure=0", headers={"Accept": "text/turtle"})
    assert page.status_code == 200
    assert b"TemperatureProperty" in page.data


def test_a_view_of_one_term_is_small(client):
    page = client.get("/view?term=TemperatureProperty",
                      headers={"Accept": "text/turtle"})
    module = client.get("/GenericPropertyOntology.ttl")
    assert 0 < len(page.data) < len(module.data) / 10


def test_a_closed_view_pulls_in_what_it_refers_to(client):
    """`TemperatureProperty` is a sub class of `seas:Property`; a closed view
    must carry the definition of `seas:Property` too."""
    open_ = client.get("/view?term=TemperatureProperty",
                       headers={"Accept": "text/turtle"}).data
    closed = client.get("/view?term=TemperatureProperty&closure=1",
                        headers={"Accept": "text/turtle"}).data
    assert b"seas:Property a" not in open_ and len(closed) > len(open_)
    assert b"Property" in closed


def test_a_view_names_what_it_could_not_find(client):
    page = client.get("/view?term=NotATerm")
    assert page.status_code == 200 and b"Not found" in page.data


def test_a_view_needs_something_to_show(client):
    assert client.get("/view").status_code == 400


# ----------------------------------------------------------------- cache

def test_a_page_is_built_once_and_then_reused(client):
    cache_of(client).clear()
    before = cache_of(client).stats()["misses"]
    first = client.get("/TemperatureProperty")
    after_first = cache_of(client).stats()
    client.get("/TemperatureProperty")
    after_second = cache_of(client).stats()
    assert after_first["misses"] == before + 1
    assert after_second["misses"] == after_first["misses"]
    assert after_second["hits"] == after_first["hits"] + 1
    assert first.headers["ETag"]


def test_a_client_that_already_has_it_gets_304(client):
    first = client.get("/TemperatureProperty")
    again = client.get("/TemperatureProperty",
                       headers={"If-None-Match": first.headers["ETag"]})
    assert again.status_code == 304


def test_a_generated_vocabulary_is_served_the_same_way(generated):
    """The contract does not know whether the modules came from files or from
    patterns."""
    assert generated.get("/").status_code == 200
    page = generated.get("/GenericPropertyOntology")
    assert page.status_code == 200
    assert page.headers["Content-Location"] == "/GenericPropertyOntology-1.0"
    assert generated.get("/TemperatureProperty.ttl").status_code == 200


def test_a_generated_vocabulary_documents_its_patterns(generated):
    """The page a hand-written ontology cannot have: the rule that minted a
    family of terms, its degree and the roles of its dimensions."""
    listing = generated.get("/patterns")
    assert listing.status_code == 200 and b"property_family" in listing.data
    one = generated.get("/pattern-property_family")
    assert one.status_code == 200
    assert b"degree" in one.data and b"quantity" in one.data


def test_a_view_can_select_dimension_items_when_the_source_is_generated(generated):
    """On a generated source a view restricts the product itself: what is not
    asked for is never minted."""
    page = generated.get("/view?dimension=quantity=Temperature&"
                         "dimension=kind=MechanicalQuantity",
                         headers={"Accept": "text/turtle"})
    assert page.status_code == 200
    assert b"TemperatureProperty" in page.data
    assert b"HumidityProperty" not in page.data


def test_dimensions_cannot_be_selected_on_a_source_that_is_files(client):
    page = client.get("/view?dimension=quantity=Temperature")
    assert page.status_code == 400


def test_touching_the_source_invalidates_the_page(client, tmp_path):
    """The rule is one line: a page is keyed by the mtimes of the files it was
    built from."""
    path = os.path.join(SOURCES, "GenericPropertyOntology-1.0.ttl")
    client.get("/GenericPropertyOntology")
    hits = cache_of(client).stats()["hits"]
    stat = os.stat(path)
    try:
        os.utime(path, (stat.st_atime, stat.st_mtime + 10))
        client.get("/GenericPropertyOntology")
        assert cache_of(client).stats()["hits"] == hits      # rebuilt, not served
    finally:
        os.utime(path, (stat.st_atime, stat.st_mtime))


# ---------------------------------------------------- mounted under a path

BRAND = None


@pytest.fixture(scope="module")
def mounted(tmp_path_factory):
    """The same vocabulary, served under `/seas/` with an identity.

    A context path is a deployment decision, not a property of the
    vocabulary: the same files must produce the same pages at the root and
    under `/seas/`.
    """
    from gemov.doc import Brand
    assets = tmp_path_factory.mktemp("assets")
    (assets / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n not really a png")
    brand = Brand(name="SEAS", logo="static/logo.png",
                  home="http://the-smart-energy.com",
                  note="ITEA 2 12004 SEAS", ink="#3479aa")
    application = from_files([SOURCES], SEAS_NS, "seas", mount="/seas",
                             brand=brand, assets=str(assets))
    application.config["TESTING"] = True
    return application.test_client()


def test_nothing_is_served_outside_the_mount(mounted):
    assert mounted.get("/").status_code == 404
    assert mounted.get("/BuildingOntology").status_code == 404


def test_every_kind_of_page_is_served_under_the_mount(mounted):
    for path in ("/seas/", "/seas/BuildingOntology",
                 "/seas/BuildingOntology-1.0", "/seas/static/logo.png"):
        assert mounted.get(path).status_code == 200, path


def test_a_version_redirect_stays_inside_the_mount(mounted):
    """The one place the server builds an absolute path of its own."""
    response = mounted.get("/seas/DeviceOntology-1")
    assert response.status_code == 302
    assert response.headers["Location"] == "/seas/DeviceOntology-1.1"


def test_the_link_to_the_index_is_the_mounted_one(mounted):
    """Every other link on a page is relative, and therefore already right;
    the index is the only one that cannot be."""
    body = mounted.get("/seas/BuildingOntology").get_data(as_text=True)
    assert '<h1><a href="/seas/"' in body
    assert 'href="/BuildingOntology"' not in body


def test_the_content_location_of_a_floating_version_is_mounted(mounted):
    """`…/BuildingOntology` answers with the latest version and says which."""
    response = mounted.get("/seas/BuildingOntology")
    assert response.headers["Content-Location"] == "/seas/BuildingOntology-1.0"


def test_the_pages_wear_the_brand(mounted):
    body = mounted.get("/seas/BuildingOntology").get_data(as_text=True)
    assert 'src="static/logo.png"' in body          # relative: mount-proof
    assert 'href="http://the-smart-energy.com"' in body
    assert "ITEA 2 12004 SEAS" in body
    assert "--brand:#3479aa" in body
    assert "<title>The SEAS Building Ontology · SEAS</title>" in body


def test_an_unbranded_site_is_unchanged(client):
    """The brand is optional, and its absence must not leave holes."""
    body = client.get("/BuildingOntology").get_data(as_text=True)
    header = body[body.index("<header>"):body.index("</header>")]
    assert "<img" not in header and 'class="mark"' not in header
    assert ":root{--brand" not in body           # no colour override
    assert "<title>The SEAS Building Ontology</title>" in body


def test_assets_are_refused_when_no_directory_was_given(client):
    assert client.get("/static/logo.png").status_code == 404
