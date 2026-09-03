"""The configuration: a YAML file that says what to generate.

    base: https://w3id.org/seas/
    prefixes:
      seas: https://w3id.org/seas/

    import: [ quantities.yml ]        # dimensions and modules of another file

    dimensions:
      quantity:
        Temperature: { label: temperature }
        Humidity:    { label: humidity }

    modules:
      GenericPropertyOntology:
        title: The SEAS generic property ontology
        patterns:
          seas_patterns.property_family: [ quantity ]

A pattern's dimensions are written as a list, and the pattern receives them
as positional arguments; or as a mapping *role -> dimension*, and it receives
one keyword argument per role:

    patterns:
      seas_patterns.aggregated_evaluation:
        statisticalModifier: aggregation
        property: quantity

Record ottr/308 argues for the second form: a monomial is a product of
dimensions **with named roles**, and the role is what an I-ADOPT description
needs in order to say which term plays which part.

`import` merges another configuration first, so a vocabulary of dimensions can
be shared and a module can be added without touching it. Keys already present
win over the imported ones, which is what lets an importer refine.
"""

import os

import yaml

from . import patterns as _patterns
from .context import ExecutionContext

#: Accepted at the top level. `specialize` is the spelling of the first
#: prototype: a flat mapping of patterns, generated into one default module.
KEYS = {"base", "prefixes", "import", "dimensions", "with dimensions",
        "modules", "specialize", "default module"}


#: A file whose keys belong to the mapping that CONTAINS it, rather than to a
#: key of its own name. `config.yaml` at the root of a vocabulary is where
#: `base` and `prefixes` go.
INLINE = ("config.yaml", "config.yml")
SUFFIXES = (".yaml", ".yml")


def read_tree(directory):
    """A configuration written as a directory tree.

    One rule, applied recursively: **a directory is a mapping**, a file is
    one of its entries, and a sub-directory is a nested mapping.

        vocabulary/
          config.yaml                 base, prefixes — merged in place
          dimensions/
            quantity/
              Acceleration.yaml       dimensions.quantity.Acceleration
              Temperature.yaml
          modules/
            FeatureOfInterestOntology.yml   modules.FeatureOfInterestOntology

    is exactly the file this would otherwise be, and means the same thing.
    The point is not the syntax, it is that a vocabulary of ninety-eight
    quantities stops being one file that nobody can review: a change to one
    quantity is a change to one file, a pull request reads as what it does,
    and two people editing two quantities do not conflict.

    `config.yaml` is the one name with a meaning — its keys belong to the
    mapping that contains it. Everything else takes its key from its name,
    without the extension. Hidden files and anything that is not YAML are
    ignored, so a `README.md` or a `patterns.py` can live in the tree — and
    so can the `__pycache__` that importing it leaves behind, since a
    directory with no YAML at any depth is not a key.
    """
    out = {}
    for entry in sorted(os.listdir(directory)):
        if entry.startswith("."):
            continue
        path = os.path.join(directory, entry)
        if os.path.isdir(path):
            nested = read_tree(path)
            # A directory holding no YAML at any depth is not part of the
            # configuration: `__pycache__` appears next to the `patterns.py`
            # the vocabulary names, and it is not a key.
            if nested:
                out[entry] = nested
        elif entry in INLINE:
            with open(path, encoding="utf-8") as f:
                inline = yaml.safe_load(f) or {}
            if not isinstance(inline, dict):
                raise ValueError("%s: %s must be a mapping — its keys belong "
                                 "to the directory that holds it"
                                 % (path, entry))
            out.update(inline)
        elif entry.endswith(SUFFIXES):
            with open(path, encoding="utf-8") as f:
                out[entry.rsplit(".", 1)[0]] = yaml.safe_load(f)
    return out


def tree_files(directory):
    """Every YAML file a directory configuration is read from."""
    out = []
    for root, dirs, names in os.walk(directory):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        out.extend(os.path.join(root, n) for n in sorted(names)
                   if n.endswith(SUFFIXES) and not n.startswith("."))
    return out


class Config:
    def __init__(self, path=None):
        self.path = os.path.abspath(path) if path else None
        self.base = "https://example.org/"
        self.prefixes = {}
        self.dimensions = {}
        self.modules = {}                 # name -> {"title":…, "patterns": {}}
        self.default_module = "Ontology"
        #: every file the configuration was actually read from, imports and
        #: the files of a directory tree included. It is what a cache keys on:
        #: a directory's own mtime does not move when a quantity inside it is
        #: edited, and the page would then be served stale.
        self.sources = []

    # ------------------------------------------------------------ loading

    @classmethod
    def load(cls, path):
        """A configuration, from a file **or a directory**.

        See `read_tree` for what a directory means: the same configuration,
        with each level of the mapping as a level of the file system."""
        config = cls(path)
        config._merge_source(config.path, seen=set())
        return config

    def _merge_source(self, path, seen):
        path = os.path.abspath(path)
        if path in seen:                  # a cycle in `import` is not an error
            return
        seen.add(path)
        if os.path.isdir(path):
            data, here = read_tree(path), path
            self.sources.extend(tree_files(path))
        else:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            here = os.path.dirname(path)
            self.sources.append(path)
        if not isinstance(data, dict):
            raise ValueError("%s: a configuration is a mapping" % path)
        unknown = set(data) - KEYS
        if unknown:
            raise ValueError("%s: unknown key(s) %s"
                             % (path, ", ".join(sorted(unknown))))
        imports = data.get("import") or []
        for other in ([imports] if isinstance(imports, str) else imports):
            self._merge_source(os.path.join(here, other), seen)

        self.base = data.get("base", self.base)
        self.default_module = data.get("default module", self.default_module)
        self.prefixes.update(data.get("prefixes") or {})
        self.prefixes.setdefault("dcterms", "http://purl.org/dc/terms/")
        for name, items in (data.get("dimensions")
                            or data.get("with dimensions") or {}).items():
            self.dimensions.setdefault(name, {}).update(_as_mapping(items))
        for name, body in (data.get("modules") or {}).items():
            module = self.modules.setdefault(name, {"title": None,
                                                    "patterns": {}})
            module["title"] = body.get("title", module["title"])
            module["patterns"].update(body.get("patterns") or {})
        for pattern_name, dims in _flatten(data.get("specialize") or {}):
            module = self.modules.setdefault(self.default_module,
                                             {"title": None, "patterns": {}})
            module["patterns"][pattern_name] = dims
        _patterns.add_search_path(here)

    # ---------------------------------------------------------- execution

    def context(self):
        return ExecutionContext(base=self.base, prefixes=self.prefixes)

    def generate(self, selection=None, context=None):
        """Run every pattern of every module. `selection` restricts dimensions
        to some of their items — see gemov.profile."""
        context = context or self.context()
        context.dimensions = self.dimensions
        # a pattern's module is decided here, before anything runs, so that
        # generation does not depend on the order the modules are visited
        for name, body in self.modules.items():
            for pattern_name in body["patterns"]:
                fn = _patterns.load(pattern_name)
                held = context.home.get(fn.gemov_pattern)
                if held is not None and held != name:
                    raise ValueError(
                        "pattern %s is assigned to modules %s and %s — a "
                        "pattern mints into one module" % (pattern_name, held,
                                                           name))
                context.home[fn.gemov_pattern] = name
        for name, body in self.modules.items():
            context.declare_module(name, body.get("title"))
            for pattern_name, dimension_names in body["patterns"].items():
                fn = _patterns.load(pattern_name)
                context.run(name, fn, dimension_names or [], selection)
        return context


def _as_mapping(items):
    """A dimension is written as a mapping of key -> value, or as a plain list
    of keys when the items carry nothing but their name."""
    if isinstance(items, dict):
        return items
    if isinstance(items, list):
        return {item: {} if not isinstance(item, dict) else item
                for item in items}
    raise ValueError("a dimension is a mapping or a list, got %r" % type(items))


def _flatten(spec, prefix=None):
    """`specialize` may be nested by module path, as the prototype allowed."""
    if isinstance(spec, dict):
        for key, value in spec.items():
            name = "%s.%s" % (prefix, key) if prefix else key
            yield from _flatten(value, name)
    elif isinstance(spec, list):
        yield prefix, spec
