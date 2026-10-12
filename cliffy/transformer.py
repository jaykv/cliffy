import os
from typing import Any, Self, TextIO

import yaml
from jinja2 import BaseLoader, Environment, FileSystemLoader
from pydantic import ValidationError

from cliffy.blueprint import (
    BLUEPRINT_KEY,
    Blueprint,
    BlueprintError,
    build_manifest,
    normalize_reference,
    resolve_blueprint,
)
from cliffy.commander import generate_cli
from cliffy.commanders.click import ClickCommander
from cliffy.commanders.typer import TyperCommander
from cliffy.helper import compare_versions, exit_err, get_installed_package_versions, out, parse_requirement
from cliffy.manifest import LATEST_SCHEMA_VERSION, CLIManifest, IncludeManifest
from cliffy.merger import cliffy_merger


class Transformer:
    """Loads command manifest and transforms it into a CLI"""

    __slots__ = (
        "blueprint",
        "blueprint_ref",
        "cli",
        "command_config",
        "includes_config",
        "manifest",
        "manifest_io",
        "manifest_version",
    )

    def __init__(
        self,
        manifest_io: TextIO,
        *,
        as_include: bool = False,
        validate_requires: bool = True,
        blueprint: str | None = None,
    ) -> None:
        self.manifest_io = manifest_io
        self.command_config = self.load_manifest(manifest_io)
        self.manifest_version = self.command_config.pop("manifestVersion", LATEST_SCHEMA_VERSION)
        self.blueprint: Blueprint | None = None
        self.blueprint_ref = None if as_include else self.find_blueprint_reference(blueprint)
        if not self.blueprint_ref and self.command_config.get("includes"):
            self.includes_config = self.resolve_includes()
            cliffy_merger.merge(self.command_config, self.includes_config)

        manifest_cls = IncludeManifest if as_include else CLIManifest
        try:
            self.manifest = self.apply_blueprint() if self.blueprint_ref else manifest_cls(**self.command_config)
        except ValidationError as e:
            out(f"{e}")
            exit_err(f"~ error validating {manifest_io.name}")

        if validate_requires:
            self.validate_cli_requires()

        if isinstance(self.manifest, CLIManifest):
            commander_cls = ClickCommander if self.manifest.use_click else TyperCommander
            self.cli = generate_cli(self.manifest, commander_cls=commander_cls)
            if self.blueprint:
                self.cli.code = self.blueprint.post_codegen(self.cli.code)
                self.cli.blueprint = self.blueprint_ref

    def find_blueprint_reference(self, blueprint: str | None) -> str | None:
        """Blueprint for this file: the `--blueprint` option wins over the file's own `blueprint:` key.

        A path given on the command line is relative to the working directory, a path in the file is
        relative to the file.
        """
        in_file = self.command_config.pop(BLUEPRINT_KEY, None)
        if blueprint:
            return normalize_reference(blueprint)
        if in_file is None:
            return None
        if not isinstance(in_file, str) or not in_file.strip():
            exit_err(f"~ error loading {self.manifest_io.name}: `{BLUEPRINT_KEY}` must be a blueprint reference")
        return normalize_reference(in_file, os.path.dirname(os.path.realpath(self.manifest_io.name)))

    def apply_blueprint(self) -> CLIManifest:
        """Validate the file against its blueprint's spec and transform it into a manifest"""
        try:
            blueprint_cls = resolve_blueprint(str(self.blueprint_ref))
            self.blueprint, manifest = build_manifest(blueprint_cls, self.command_config, source=self.manifest_io.name)
        except BlueprintError as e:
            exit_err(f"~ {e}")
        return manifest

    def validate_cli_requires(self) -> None:
        if not self.manifest.requires:
            return

        installed_package_versions = get_installed_package_versions()
        for dep in self.manifest.requires:
            dep_spec = parse_requirement(dep)
            if dep_spec.name.lower() not in installed_package_versions:
                exit_err(f"~ missing requirement: `{self.manifest_io.name}` requires `{dep}` to be installed")

            if dep_spec.version and not compare_versions(
                installed_package_versions[dep_spec.name], dep_spec.version, dep_spec.operator
            ):
                exit_err(
                    f"~ missing requirement: `{self.manifest_io.name}` requires `{dep}` to be installed"
                    f"    found version `{installed_package_versions[dep_spec.name]}`"
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
            with open(manifest_path) as manifest_file:
                all_vars = yaml.safe_load(manifest_file).get("vars", {})
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
