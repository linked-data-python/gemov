"""Loads `queries.ldpy` — the graph patterns a documentation page needs.

The queries are written in Linked-Data Python, so they read as what they are.
This module is the seam: it installs ldpy's import hook and re-exports them,
so that the rest of gemov imports plain Python names and never has to know.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import ldpy
except ImportError as exc:                                   # pragma: no cover
    raise ImportError(
        "the documentation queries are written in Linked-Data Python: "
        "pip install 'gemov[docs]'") from exc

ldpy.install()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from _queries import (describe, module_contents,             # noqa: E402,F401
                      ontology_header)

__all__ = ["describe", "module_contents", "ontology_header"]
