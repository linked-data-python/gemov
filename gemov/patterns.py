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
import importlib.util
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


def load(name, search=()):
    """Resolve ``module.function``, or a name given to ``@pattern``.

    A pattern module is looked for **next to the configuration that names
    it**, before anywhere else, and is imported under a name of its own.
    Two vocabularies may each have a `patterns.py`, and gemov serves two
    vocabularies in one process: importing both as `patterns` would give the
    second one the first one's functions, and the error — *`patterns.Foo` is
    not a @pattern* — would point at the innocent file.
    """
    if name in _REGISTRY:
        return _REGISTRY[name]
    module_name, _, fn_name = name.rpartition(".")
    if not module_name:
        raise ValueError("a pattern is `module.function`, or a declared name; "
                         "got %r" % name)
    _install_ldpy_if_available()
    module = _import(module_name, list(search) + _SEARCH)
    fn = getattr(module, fn_name, None)
    if fn is None or not hasattr(fn, "gemov_pattern"):
        raise ValueError("%s is not a @pattern (from %s)"
                         % (name, getattr(module, "__file__", module_name)))
    return fn


def _import(module_name, directories):
    """The pattern module, from a search directory if one has it."""
    stem = os.path.join(*module_name.split("."))
    for directory in directories:
        path = os.path.join(directory, stem + ".py")
        if os.path.isfile(path):
            return _import_file(module_name, directory, path)
        if os.path.isfile(os.path.join(directory, stem + ".ldpy")):
            # Written in Linked-Data Python: its import hook resolves it from
            # `sys.path`, so the directory goes there for the length of the
            # import and no longer.
            return _import_named(module_name, directory)
    return _import_named(module_name, None)


def _import_file(module_name, directory, path):
    """Import a file under a name of its own, so two `patterns.py` do not
    become one."""
    unique = "gemov._loaded.%x.%s" % (abs(hash(directory)) & 0xffffffff,
                                      module_name)
    if unique in sys.modules:
        return sys.modules[unique]
    spec = importlib.util.spec_from_file_location(unique, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[unique]
        raise
    return module


def _import_named(module_name, directory):
    if directory and directory not in sys.path:
        sys.path.insert(0, directory)
        added = True
    else:
        added = False
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        raise ValueError("cannot import the pattern module %r: %s"
                         % (module_name, e))
    finally:
        if added:
            sys.path.remove(directory)


#: Directories a configuration has said its patterns live in, most recent
#: first. They are consulted before the ordinary import path.
_SEARCH = []


def add_search_path(directory):
    """Say that a configuration's pattern modules sit in this directory."""
    directory = os.path.abspath(directory)
    if directory in _SEARCH:
        _SEARCH.remove(directory)
    _SEARCH.insert(0, directory)
