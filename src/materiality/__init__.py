"""Backwards-compatible alias for :mod:`sustainkit.materiality`.

``import materiality`` keeps working for code written against
materiality-matrix 0.1; new code should use ``sustainkit.materiality``.
"""

import sys as _sys

from sustainkit import materiality as _m
from sustainkit.materiality import *  # noqa: F401,F403
from sustainkit.materiality import __all__, __version__  # noqa: F401
from sustainkit.materiality import cli, io, plot, report, schema, scoring, taxonomy, text

for _name, _mod in {
    "cli": cli, "io": io, "plot": plot, "report": report, "schema": schema,
    "scoring": scoring, "taxonomy": taxonomy, "text": text,
}.items():
    _sys.modules[f"materiality.{_name}"] = _mod

del _m
