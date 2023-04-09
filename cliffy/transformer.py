from typing import TextIO

import yaml
from typing_extensions import Self

from .commander import build_cli
from .commanders.typer import TyperCommander
from .manifests import IncludeManifest, Manifest, set_manifest_version
from .merger import cliffy_merger


class Transformer:
    """Loads command manifest and transforms it into a CLI"""

    def __init__(self, manifest_io: TextIO, as_include: bool = False) -> None:
        self.manifest_io = manifest_io
        self.command_config = self.load_manifest(manifest_io)
        self.manifest_version = self.command_config.pop('manifestVersion', 'v1')

        if self.command_config.get("includes"):
            self.includes_config = self.resolve_includes()
            cliffy_merger.merge(self.command_config, self.includes_config)

        set_manifest_version(self.manifest_version)
        if as_include:
            self.manifest = IncludeManifest(**self.command_config)
        else:
            self.manifest = Manifest(**self.command_config)
            self.cli = build_cli(self.manifest, commander_cls=TyperCommander)

    def resolve_includes(self) -> dict:
        include_transforms = map(self.resolve_include_by_path, set(self.command_config['includes']))
        merged_config = {}
        for transformed_include in include_transforms:
            cliffy_merger.merge(merged_config, transformed_include.command_config)

        return merged_config

    @classmethod
    def resolve_include_by_path(cls, path) -> Self:
        with open(path, "r") as m:
            return cls(m, as_include=True)

    @staticmethod
    def load_manifest(manifest_io: TextIO) -> dict:
        try:
            return yaml.safe_load(manifest_io)
        except yaml.YAMLError as e:
            print("load_manifest", e)
            raise
