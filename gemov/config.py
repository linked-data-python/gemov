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


class Config:
    def __init__(self, path=None):
        self.path = os.path.abspath(path) if path else None
        self.base = "https://example.org/"
        self.prefixes = {}
        self.dimensions = {}
        self.modules = {}                 # name -> {"title":…, "patterns": {}}
        self.default_module = "Ontology"

    # ------------------------------------------------------------ loading

    @classmethod
    def load(cls, path):
        config = cls(path)
        config._merge_file(config.path, seen=set())
        return config

    def _merge_file(self, path, seen):
        path = os.path.abspath(path)
        if path in seen:                  # a cycle in `import` is not an error
            return
        seen.add(path)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        unknown = set(data) - KEYS
        if unknown:
            raise ValueError("%s: unknown key(s) %s"
                             % (path, ", ".join(sorted(unknown))))
        here = os.path.dirname(path)
        imports = data.get("import") or []
        for other in ([imports] if isinstance(imports, str) else imports):
            self._merge_file(os.path.join(here, other), seen)

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
