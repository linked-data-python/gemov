"""``gemov`` on the command line.

    gemov build   vocabulary.yml [-o out/] [--format turtle]
    gemov profile vocabulary.yml quantity=Temperature aggregation=Average
    gemov check   vocabulary.yml
"""

import argparse
import os
import sys

from .config import Config
from . import check as _check
from . import profile as _profile


def _selection(pairs):
    selection = {}
    for pair in pairs:
        name, sep, keys = pair.partition("=")
        if not sep:
            raise SystemExit("a selection is dimension=Item[,Item]; got %r"
                             % pair)
        selection.setdefault(name, []).extend(keys.split(","))
    return selection


def main(argv=None):
    parser = argparse.ArgumentParser(prog="gemov", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="generate every module")
    build.add_argument("config")
    build.add_argument("-o", "--out", help="one file per module in this "
                       "directory (default: print everything)")
    build.add_argument("--format", default="turtle")

    prof = sub.add_parser("profile", help="generate a part, closed")
    prof.add_argument("config")
    prof.add_argument("selection", nargs="+", metavar="dimension=Item,Item")
    prof.add_argument("-o", "--out")
    prof.add_argument("--format", default="turtle")
    prof.add_argument("--explain", action="store_true")

    chk = sub.add_parser("check", help="report the coherence findings")
    chk.add_argument("config")

    args = parser.parse_args(argv)
    config = Config.load(args.config)

    if args.command == "build":
        context = config.generate()
        if not args.out:
            sys.stdout.write(context.all_triples().serialize(
                format=args.format))
            return 0
        os.makedirs(args.out, exist_ok=True)
        for name, graph in sorted(context.modules.items()):
            path = os.path.join(args.out, "%s.ttl" % name)
            graph.serialize(destination=path, format=args.format)
            print("%-40s %5d triples" % (path, len(graph)))
        return 0

    if args.command == "profile":
        result = _profile.build(config, _selection(args.selection))
        if args.explain:
            print(result.explain(), file=sys.stderr)
        text = result.graph.serialize(format=args.format)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(text)
            print("%s  %d triples" % (args.out, len(result.graph)))
        else:
            sys.stdout.write(text)
        return 0

    findings = _check.check(config.generate())
    for finding in findings:
        print(finding)
    print("%d finding(s)" % len(findings), file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
