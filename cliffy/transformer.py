import os
from typing import Any, Self, TextIO

import yaml
from jinja2 import BaseLoader, Environment, FileSystemLoader
from pydantic import ValidationError

from cliffy.commander import generate_cli
from cliffy.commanders.click import ClickCommander
from cliffy.commanders.typer import TyperCommander
from cliffy.helper import check_requirement, exit_err, get_installed_package_versions, out
from cliffy.manifest import LATEST_SCHEMA_VERSION, CLIManifest, IncludeManifest
from cliffy.merger import cliffy_merger


class Transformer:
    """Loads command manifest and transforms it into a CLI"""

    __slots__ = ("cli", "command_config", "includes_config", "manifest", "manifest_io", "manifest_version")

    def __init__(
        self,
        manifest_io: TextIO,
        *,
        as_include: bool = False,
        validate_requires: bool = True,
    ) -> None:
        self.manifest_io = manifest_io
        self.command_config = self.load_manifest(manifest_io)
        self.manifest_version = self.command_config.pop("manifestVersion", LATEST_SCHEMA_VERSION)
        if self.command_config.get("includes"):
            self.includes_config = self.resolve_includes()
            cliffy_merger.merge(self.command_config, self.includes_config)

        manifest_cls = IncludeManifest if as_include else CLIManifest
        try:
            self.manifest = manifest_cls(**self.command_config)
        except ValidationError as e:
            out(f"{e}")
            exit_err(f"~ error validating {manifest_io.name}")

        if validate_requires:
            self.validate_cli_requires()

        if isinstance(self.manifest, CLIManifest):
            commander_cls = ClickCommander if self.manifest.use_click else TyperCommander
            self.cli = generate_cli(self.manifest, commander_cls=commander_cls)

    def validate_cli_requires(self) -> None:
        if not self.manifest.requires:
            return

        installed_package_versions = get_installed_package_versions()
        for dep in self.manifest.requires:
            if problem := check_requirement(dep, installed_package_versions):
                exit_err(
                    f"~ missing requirement: `{self.manifest_io.name}` requires `{dep}` to be installed\n    {problem}"
                )

    def resolve_includes(self) -> dict[str, Any]:
        include_transforms = map(self.resolve_include_by_path, set(self.command_config["includes"]))
        merged_config: dict[str, Any] = {}
        for transformed_include in include_transforms:
            cliffy_merger.merge(merged_config, transformed_include.command_config)

        return merged_config

    @classmethod
    def resolve_include_by_path(cls, path: str) -> Self:
        with open(path) as m:
            return cls(m, as_include=True)

    @staticmethod
    def load_manifest(manifest_io: TextIO) -> dict[str, Any]:
        try:
            manifest_path = os.path.realpath(manifest_io.name)
            with open(manifest_path, encoding="utf-8") as manifest_file:
                raw_manifest = yaml.safe_load(manifest_file)
            if not isinstance(raw_manifest, dict):
                exit_err(f"~ error loading manifest: {manifest_io.name} must be a YAML mapping")

            manifest_vars = raw_manifest.get("vars") or {}
            if not isinstance(manifest_vars, dict):
                exit_err(f"~ error loading manifest: vars in {manifest_io.name} must be a mapping")

            # `env` is passed to the templates as-is. Environment values are data: they are never
            # rendered as templates themselves.
            render_context = {**manifest_vars, "env": os.environ}
            var_env = Environment(loader=BaseLoader())
            interpolated_vars: dict[str, Any] = {
                var_env.from_string(str(k)).render(render_context): var_env.from_string(str(v)).render(render_context)
                for k, v in manifest_vars.items()
            }
            interpolated_vars["env"] = os.environ
            manifest_env = Environment(loader=FileSystemLoader(manifest_path)).get_template("")
            manifest = yaml.safe_load(manifest_env.render(interpolated_vars))
            if not isinstance(manifest, dict):
                exit_err(f"~ error loading manifest: {manifest_io.name} must be a YAML mapping")
            return manifest
        except yaml.YAMLError as e:
            out(f"{e}")
            exit_err("~ error loading manifest")
