"""Documentation of a vocabulary, generated from the graph.

`saref-pypeline` generates https://saref.etsi.org/ by rewriting pyLODE's output
in its own HTML. This does the same for a gemov vocabulary, and asks the graph
its questions in Linked-Data Python (`queries.ldpy`) — what a documentation
page needs from an ontology is a handful of graph patterns.

Three kinds of page, and the third is the one a generator can offer that a
hand-written ontology cannot:

* a **term** page — its definition, what it subsumes, what points at it;
* a **module** page — its metadata and the terms it defines;
* a **pattern** page — the function that minted a family of terms, its degree,
  the roles of its dimensions, and what it produced. Documentation of the
  *rule*, next to documentation of its results.
"""

from .brand import Brand
from .cache import Cache
from .render import (render_index, render_module, render_pattern,
                     render_patterns_index, render_term, write_site)
from .queries import describe, module_contents, ontology_header

__all__ = ["Brand", "Cache", "describe", "module_contents", "ontology_header",
           "render_index", "render_module", "render_pattern",
           "render_patterns_index", "render_term", "write_site"]
