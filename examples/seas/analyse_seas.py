"""What the published SEAS 1.0 is made of — the case for generating it.

    python examples/seas/analyse_seas.py ../seas/src/main/ontop/1.0

Every number record ottr/302 relies on comes from here, so none of them has to
be trusted. Three questions:

* how much of the vocabulary is a cartesian product written by hand?
* what defects does writing it by hand leave behind?
* which external vocabularies does it align to, and are they still there?
"""

import collections
import os
import re
import sys

from rdflib import Graph, RDFS, URIRef
from rdflib.namespace import OWL, RDF

SEAS = "https://w3id.org/seas/"
VS = URIRef("http://www.w3.org/2003/06/sw-vocab-status/ns#term_status")

#: Namespaces SEAS 1.0 refers to, and what they should be in a v2. Measured
#: against the live web on 2026-09-02.
STALE = {
    "https://www.w3.org/ns/ssn/": "http://www.w3.org/ns/ssn/ (the W3C recommendation)",
    "https://www.w3.org/ns/sosa/": "http://www.w3.org/ns/sosa/ (the W3C recommendation)",
    "http://qudt.org/1.1/schema/qudt#": "http://qudt.org/schema/qudt/ (QUDT 2; the 1.1 IRI is a 404)",
    "http://ontology.tno.nl/saref#": "https://saref.etsi.org/core/ (SAREF v4.1.1)",
    "https://w3id.org/saref#": "https://saref.etsi.org/core/ (SAREF v4.1.1)",
}


def load(directory):
    graph, files = Graph(), []
    for name in sorted(os.listdir(directory)):
        if name.endswith(".ttl"):
            graph.parse(os.path.join(directory, name), format="turtle")
            files.append(os.path.join(directory, name))
    return graph, files


def words(camel):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", camel)


def main(argv=None):
    directory = (argv or sys.argv[1:] or ["."])[0]
    graph, files = load(directory)
    local = lambda u: str(u)[len(SEAS):]
    classes = {local(s) for s in graph.subjects(RDF.type, OWL.Class)
               if str(s).startswith(SEAS)}
    objprops = {local(s) for s in graph.subjects(RDF.type, OWL.ObjectProperty)
                if str(s).startswith(SEAS)}

    print("%d files, %d triples, %d classes, %d object properties"
          % (len(files), len(graph), len(classes), len(objprops)))

    print("\n-- the product, written by hand")
    suffixes = collections.Counter()
    for name in classes:
        m = re.search(r"([A-Z][a-z]+)$", name)
        if m:
            suffixes[m.group(1)] += 1
    for suffix, count in suffixes.most_common(4):
        print("   %-12s %3d classes end in it" % (suffix, count))
    props = {n[: -len("Property")] for n in classes if n.endswith("Property")}
    evals = {n[: -len("Evaluation")] for n in classes if n.endswith("Evaluation")}
    print("   %d quantities have a *Property class, %d have a *Evaluation one"
          % (len(props), len(evals)))
    print("   asymmetric: %d Property with no Evaluation, %d the other way"
          % (len(props - evals), len(evals - props)))

    print("\n-- what hand-writing left behind")
    stray = [(local(s), str(o)) for s, o in graph.subject_objects(RDFS.label)
             if str(s).startswith(SEAS) and str(o) != str(o).strip()]
    print("   %d labels carry a stray space, e.g. %s"
          % (len(stray), ", ".join("%r" % l for _, l in sorted(stray)[:2])))
    status = collections.Counter(str(o) for s, o in graph.subject_objects(VS)
                                 if str(s).startswith(SEAS))
    print("   vs:term_status values: %s"
          % ", ".join("%s×%d" % kv for kv in status.most_common()))
    no_label = [local(s) for s in graph.subjects(RDF.type, OWL.Class)
                if str(s).startswith(SEAS) and (s, RDFS.label, None) not in graph]
    print("   %d classes with no rdfs:label" % len(no_label))

    print("\n-- alignment targets that moved")
    text = "".join(open(f, encoding="utf-8", errors="replace").read()
                   for f in files)
    for stale, replacement in sorted(STALE.items()):
        used = sum(1 for f in files
                   if stale in open(f, encoding="utf-8", errors="replace").read())
        if used:
            print("   %-34s in %2d files -> %s" % (stale, used, replacement))
    both = [ns for ns in ("http://www.w3.org/ns/ssn/",
                          "https://www.w3.org/ns/ssn/") if ns in text]
    if len(both) > 1:
        print("   the SSN namespace is written BOTH ways in the same "
              "vocabulary: %s" % ", ".join(both))
    return 0


if __name__ == "__main__":
    sys.exit(main())
