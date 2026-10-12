"""Write the code cliffy generates for each manifest in ``examples/`` to ``examples/generated/``.

Usage (from the repository root)::

    uv run python scripts/examples.py

The files are exactly what ``cli render`` prints for the manifest. ``tests/test_examples.py`` fails when
one of them is stale or has no manifest.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

from cliffy.loader import Loader
from cliffy.transformer import Transformer

EXAMPLES = "examples"
GENERATED = "examples/generated"


def render_examples() -> dict[str, str]:
    """Generated code for every example manifest, keyed by the path of its file in examples/generated.

    The manifests are rendered with an empty environment, so that ``{{ env[...] }}`` placeholders resolve
    to their defaults on every machine. The packages an example lists under ``requires`` do not have to be
    installed: nothing is imported or run.
    """
    rendered: dict[str, str] = {}
    with mock.patch.dict(os.environ, clear=True):
        for manifest_path in sorted(Path(EXAMPLES).glob("*.yaml")):
            with open(manifest_path, encoding="utf-8") as manifest_io:
                cli = Transformer(manifest_io, validate_requires=False).cli
            rendered[f"{GENERATED}/{Path(Loader.get_cli_path(cli.name)).name}"] = cli.code
    return rendered


def main() -> int:
    rendered = render_examples()
    for stale in sorted(set(Path(GENERATED).glob("*.py")) - {Path(path) for path in rendered}):
        stale.unlink()
        print(f"removed {stale}")
    for path, code in rendered.items():
        Path(path).write_text(code, encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
