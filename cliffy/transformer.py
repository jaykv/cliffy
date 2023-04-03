from typing import TextIO

import yaml

from .commander import build_cli
from .commanders.typer import TyperCommander
from .manifests import get_cli_manifest


class Transformer:
    """Loads command manifest and transforms it into a CLI"""

    def __init__(self, manifest_io: TextIO) -> None:
        self.manifest_io = manifest_io
        self.command_config = self.load_manifest()
        self.manifestVersion = self.command_config.pop('manifestVersion', '')
        self.manifest = get_cli_manifest(self.manifestVersion)(**self.command_config)
        self.render_cli()

    def render_cli(self) -> None:
        self.cli = build_cli(self.manifest, commander_cls=TyperCommander)

    def load_manifest(self) -> dict:
        try:
            return yaml.safe_load(self.manifest_io)
        except yaml.YAMLError as e:
            print("load_manifest", e)
            return {}
