import os
from typing import Any, TextIO

import yaml
from jinja2 import BaseLoader, Environment, FileSystemLoader
from pydantic import ValidationError
from typing_extensions import Self

from .commander import build_cli
from .commanders.typer import TyperCommander
from .helper import compare_versions, exit_err, get_installed_pip_packages, out, parse_requirement
from .manifests import IncludeManifest, Manifest, set_manifest_version
from .merger import cliffy_merger


class Transformer:
    """Loads command manifest and transforms it into a CLI"""

    __slots__ = ("manifest_io", "command_config", "manifest_version", "includes_config", "manifest", "cli")

    def __init__(self, manifest_io: TextIO, *, as_include: bool = False, validate_requires: bool = True) -> None:
        self.manifest_io = manifest_io
        self.command_config = self.load_manifest(manifest_io)
        self.manifest_version = self.command_config.pop("manifestVersion", "v1")
        if self.command_config.get("includes"):
            self.includes_config = self.resolve_includes()
            cliffy_merger.merge(self.command_config, self.includes_config)

        set_manifest_version(self.manifest_version)
        if as_include:
            try:
                self.manifest = IncludeManifest(**self.command_config)
            except ValidationError as e:
                out(f"{e}")
                exit_err(f"~ error validating {manifest_io.name}")
        else:
            try:
                self.manifest = Manifest(**self.command_config)
            except ValidationError as e:
                out(f"{e}")
                exit_err(f"~ error validating {manifest_io.name}")

            if validate_requires:
                self.validate_cli_requires()
            self.cli = build_cli(self.manifest, commander_cls=TyperCommander)

    def validate_cli_requires(self) -> None:
        if not self.manifest.requires:
            return

        installed_pip_packages = get_installed_pip_packages()
        for dep in self.manifest.requires:
            dep_spec = parse_requirement(dep)
            if dep_spec.name not in installed_pip_packages:
                exit_err(f"~ missing requirement: `{self.manifest_io.name}` requires `{dep}` to be installed")

            if (
                dep_spec.version
                and dep_spec.operator
                and not compare_versions(
                    installed_pip_packages[dep_spec.name],
                    dep_spec.version,
                    dep_spec.operator,
                )
            ):
                exit_err(
                    f"~ missing requirement: `{self.manifest_io.name}` requires `{dep}` to be installed"
                    f"    found version `{installed_pip_packages[dep_spec.name]}`"
                )

    def resolve_includes(self) -> dict:
        include_transforms = map(self.resolve_include_by_path, set(self.command_config["includes"]))
        merged_config: dict[str, Any] = {}
        for transformed_include in include_transforms:
            cliffy_merger.merge(merged_config, transformed_include.command_config)

        return merged_config

    @classmethod
    def resolve_include_by_path(cls, path) -> Self:
        with open(path, "r") as m:
            return cls(m, as_include=True)

    @staticmethod
    def load_manifest(manifest_io: TextIO) -> dict[str, Any]:
        try:
            manifest_path = os.path.realpath(manifest_io.name)
            all_vars = yaml.safe_load(open(manifest_path, "r")).get("vars", {})
            all_vars["env"] = os.environ
            var_env = Environment(loader=BaseLoader())
            interpolated_vars = {
                var_env.from_string(str(k)).render(all_vars): var_env.from_string(str(v)).render(all_vars)
                for k, v in all_vars.items()
            }
            manifest_env = Environment(loader=FileSystemLoader(manifest_path)).get_template("")
            return yaml.safe_load(manifest_env.render(interpolated_vars))
        except yaml.YAMLError as e:
            out(f"{e}")
            exit_err("~ error loading manifest")
