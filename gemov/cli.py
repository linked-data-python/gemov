"""``gemov`` on the command line.

    gemov build   vocabulary.yml [-o out/] [--format turtle]
    gemov profile vocabulary.yml quantity=Temperature aggregation=Average
    gemov check   vocabulary.yml
    gemov docs    vocabulary.yml -o site/        # needs [docs]
    gemov serve   vocabulary.yml                 # needs [server]
"""

import argparse
import os
import sys

from .config import Config
from . import check as _check
from . import profile as _profile


def _brand(path):
    """The brand, if one was named."""
    if not path:
        return None
    from .doc.brand import Brand
    return Brand.load(path)


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

    docs = sub.add_parser("docs", help="write the documentation site")
    docs.add_argument("config")
    docs.add_argument("-o", "--out", default="site")
    docs.add_argument("--prefix", default="")
    docs.add_argument("--brand", help="a YAML file: logo, name, project link, "
                      "footer note (see gemov.doc.brand)")
    docs.add_argument("--order", default="kind", choices=("kind", "source"))

    serve = sub.add_parser("serve", help="serve the vocabulary over HTTP")
    serve.add_argument("config", nargs="?")
    serve.add_argument("--files", nargs="+")
    serve.add_argument("--namespace")
    serve.add_argument("--prefix", default="",
                       help="prefix for compact IRIs, e.g. seas")
    serve.add_argument("--mount", default="",
                       help="the path the site is served under, e.g. /seas "
                            "(default: the root)")
    serve.add_argument("--brand", help="a YAML file: logo, name, project "
                       "link, footer note (see gemov.doc.brand)")
    serve.add_argument("--assets", help="a directory served under "
                       "<mount>/static/ — where the logo lives")
    serve.add_argument("--order", default="kind", choices=("kind", "source"),
                       help="how a module lays out its terms: grouped by "
                            "kind and alphabetical (default, what the 2016 "
                            "SEAS site did), or in the order they were "
                            "written")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=5000)

    args = parser.parse_args(argv)

    if args.command == "serve":
        try:
            from .server import from_config, from_files
        except ImportError:
            raise SystemExit("the server is optional: pip install 'gemov[server]'")
        brand = _brand(args.brand)
        common = dict(mount=args.mount, brand=brand, assets=args.assets,
                      order=args.order)
        if args.config:
            application = from_config(Config.load(args.config), args.prefix,
                                      **common)
        elif args.files:
            if not args.namespace:
                raise SystemExit("--files needs --namespace")
            application = from_files(args.files, args.namespace, args.prefix,
                                     **common)
        else:
            raise SystemExit("give a configuration, or --files with --namespace")
        source = application.config["SOURCE"]
        print("%d modules in %s under %s"
              % (len(source.modules()), source.namespace,
                 "/" + args.mount.strip("/") + "/" if args.mount.strip("/")
                 else "/"))
        application.run(host=args.host, port=args.port)
        return 0

    config = Config.load(args.config)

    if args.command == "docs":
        try:
            from .doc import write_site
            from .server.source import Generated
        except ImportError as exc:
            raise SystemExit("the documentation needs Linked-Data Python: "
                             "pip install 'gemov[docs]' (%s)" % exc)
        written = write_site(Generated(config), args.out, args.prefix, config,
                             brand=_brand(args.brand), order=args.order)
        print("%d pages in %s" % (len(written), args.out))
        return 0

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
