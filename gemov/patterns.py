"""Patterns: ordinary Python functions that add triples to a graph.

A pattern is a function decorated with ``@pattern``. It receives an execution
context and one ``(key, value)`` pair per dimension it is specialised on, and
it writes into ``context.graph`` with rdflib — nothing more is required of it.

    @pattern
    def property_family(context, quantity):
        key, value = quantity
        context.mint(key + "Property", RDFS.subClassOf, context.term("Property"))

Two things the decorator adds. A pattern called from another pattern goes
through the context, so the same specialisation never runs twice (a diamond in
the pattern graph produces one copy of the triples, not two). And a pattern may
carry a name of its own, used in configurations instead of its dotted path.
"""

import importlib
import os
import sys

_REGISTRY = {}


def pattern(param=None):
    """Declare a pattern. Usable bare (``@pattern``) or named
    (``@pattern("property-family")``)."""

    def decorate(fn):
        def call(context, *args):
            return context.specialise(fn, *args)
        call.gemov_pattern = fn
        call.__name__ = fn.__name__
        call.__doc__ = fn.__doc__
        call.__module__ = fn.__module__
        if isinstance(param, str):
            call.pattern_name = param
            _REGISTRY[param] = call
        return call

    return decorate(param) if callable(param) else decorate


def _install_ldpy_if_available():
    """Patterns may be written in Linked-Data Python — the notation of Turtle
    inside Python. It is a convenience for the pattern's author, never a
    requirement: gemov itself only ever calls rdflib."""
    try:
        import ldpy
    except ImportError:
        return False
    ldpy.install()
    return True


def load(name):
    """Resolve ``module.function``, or a name given to ``@pattern``."""
    if name in _REGISTRY:
        return _REGISTRY[name]
    module_name, _, fn_name = name.rpartition(".")
    if not module_name:
        raise ValueError("a pattern is `module.function`, or a declared name; "
                         "got %r" % name)
    _install_ldpy_if_available()
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ValueError("cannot import the pattern module %r: %s"
                         % (module_name, e))
    fn = getattr(module, fn_name, None)
    if fn is None or not hasattr(fn, "gemov_pattern"):
        raise ValueError("%s is not a @pattern" % name)
    return fn


def add_search_path(directory):
    """Make a directory importable, so that a configuration can name the
    pattern modules that sit next to it."""
    directory = os.path.abspath(directory)
    if directory not in sys.path:
        sys.path.insert(0, directory)
