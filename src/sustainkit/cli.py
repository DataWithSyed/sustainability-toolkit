"""Umbrella command line: ``sustainkit <module> ...``."""

from __future__ import annotations

import argparse
import sys

from sustainkit import __version__
from sustainkit.modules import MODULES


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # materiality keeps its own parser (also installed as the `materiality` command)
    if argv and argv[0] == "materiality":
        from sustainkit.materiality.cli import main as mat_main

        return mat_main(argv[1:])

    from sustainkit.ghg.cli import InventoryError, add_parser as add_ghg

    p = argparse.ArgumentParser(prog="sustainkit", description="Sustainability management toolkit.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("materiality", help="double materiality (run `sustainkit materiality -h`)")
    add_ghg(sub)
    m = sub.add_parser("modules", help="list toolkit modules and their status")
    m.set_defaults(func=lambda a: _modules())
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except InventoryError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _modules() -> int:
    w = max(len(n) for n, _, _ in MODULES)
    for name, status, summary in MODULES:
        print(f"{name:<{w}}  {status:<9}  {summary}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
