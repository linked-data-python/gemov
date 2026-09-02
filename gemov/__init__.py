"""GEMOV — Generating Modular Ontologies and Vocabularies.

An ontology whose terms are a cartesian product should be generated, not typed.
GEMOV takes a YAML description of *dimensions*, *modules* and *patterns*, and
runs the patterns over the product to produce the modules.

A pattern is an ordinary Python function writing into an rdflib graph, so the
whole of rdflib is available and nothing new has to be learnt. Authors who
prefer to write the triples in Turtle's own notation may write their pattern
module in Linked-Data Python; gemov installs its import hook when it is
present. That is a convenience for the pattern's author — gemov itself calls
only rdflib.

    from gemov import Config, pattern, profile

    config = Config.load("vocabulary.yml")
    context = config.generate()              # every module
    part = profile.build(config, {"quantity": ["Temperature"]})

Record pilotage ottr/302.
"""

from .config import Config
from .context import ExecutionContext, Item, OwnershipError
from .patterns import pattern
from . import check, profile

__version__ = "0.1.0"
__all__ = ["Config", "ExecutionContext", "Item", "OwnershipError",
           "pattern", "check", "profile", "__version__"]
