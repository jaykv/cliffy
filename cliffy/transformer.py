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

    __slots__ = (
        "cli",
        "command_config",
        "include_chain",
        "includes_config",
        "manifest",
        "manifest_io",
        "manifest_path",
        "manifest_version",
    )

    def __init__(
        self,
        manifest_io: TextIO,
        *,
        as_include: bool = False,
        validate_requires: bool = True,
        include_chain: tuple[str, ...] = (),
    ) -> None:
        self.manifest_io = manifest_io
        self.manifest_path = os.path.realpath(manifest_io.name)
        # manifests that are being resolved right now, outermost first: used to detect include cycles
        self.include_chain = (*include_chain, self.manifest_path)
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
        includes = self.command_config["includes"]
        if not isinstance(includes, list):
            exit_err(f"~ error validating {self.manifest_io.name}: includes must be a list of manifest paths")

        merged_config: dict[str, Any] = {}
        # merged in the order given. dict.fromkeys drops duplicates and, unlike a set, keeps that order
        for include_path in dict.fromkeys(str(include) for include in includes):
            transformed_include = self.resolve_include(include_path)
            cliffy_merger.merge(merged_config, transformed_include.command_config)

        return merged_config

    def resolve_include(self, path: str) -> Self:
        """Loads an included manifest.

        A relative path is looked up next to the including manifest first, then in the working directory.
        """
        candidates = [os.path.join(os.path.dirname(self.manifest_path), path), path]
        include_path = next((candidate for candidate in candidates if os.path.isfile(candidate)), None)
        if include_path is None:
            exit_err(f"~ error loading manifest: `{self.manifest_io.name}` includes `{path}`, which does not exist")

        if os.path.realpath(include_path) in self.include_chain:
            cycle = " -> ".join([*self.include_chain, os.path.realpath(include_path)])
            exit_err(f"~ error loading manifest: circular include {cycle}")

        with open(include_path, encoding="utf-8") as m:
            return type(self)(m, as_include=True, include_chain=self.include_chain)

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
