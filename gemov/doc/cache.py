"""The documentation cache.

One rule, and it is the only one: **a page is keyed by what it was built
from**. For a source that is files, that is their mtimes; for a generated
source, the configuration's. A cache whose invalidation rule you cannot
state in one line is a cache you cannot trust.
"""

import hashlib


class Cache:
    """A dict, not a library."""

    def __init__(self):
        self._entries = {}
        self.hits = 0
        self.misses = 0

    def get_or_build(self, key, stamp, build):
        """`stamp` is whatever says the sources changed — see
        `ModuleVersion.stamp()`."""
        entry = self._entries.get(key)
        if entry is not None and entry[0] == stamp:
            self.hits += 1
            return entry[1], entry[2]
        self.misses += 1
        body = build()
        etag = 'W/"%s"' % hashlib.sha256(
            (str(stamp) + str(key)).encode()).hexdigest()[:16]
        self._entries[key] = (stamp, body, etag)
        return body, etag

    def clear(self):
        self._entries.clear()

    def stats(self):
        return {"entries": len(self._entries), "hits": self.hits,
                "misses": self.misses}


def short(iri, namespace, prefix=""):
    """The compact form inside our namespace, the bare IRI outside it."""
    return (prefix + ":" if prefix else "") + iri[len(namespace):] \
        if iri.startswith(namespace) else iri


def local(iri, namespace):
    return iri[len(namespace):] if iri.startswith(namespace) else iri
