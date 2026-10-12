import os
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any, Self, TextIO

import yaml
from jinja2 import BaseLoader, Environment, TemplateSyntaxError, meta
from pydantic import ValidationError

from cliffy.blueprint import (
    BLUEPRINT_KEY,
    Blueprint,
    BlueprintError,
    blueprint_file,
    build_manifest,
    normalize_reference,
    resolve_blueprint,
)
from cliffy.commander import generate_cli
from cliffy.commanders.click import ClickCommander
from cliffy.commanders.typer import TyperCommander
from cliffy.helper import check_requirement, exit_err, get_installed_package_versions, out
from cliffy.manifest import LATEST_SCHEMA_VERSION, CLIManifest, IncludeManifest, manifest_version_problem
from cliffy.merger import cliffy_merger


class Transformer:
    """Loads command manifest and transforms it into a CLI"""

    __slots__ = (
        "blueprint",
        "blueprint_ref",
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
        blueprint: str | None = None,
    ) -> None:
        self.manifest_io = manifest_io
        self.manifest_path = os.path.realpath(manifest_io.name)
        # manifests that are being resolved right now, outermost first: used to detect include cycles
        self.include_chain = (*include_chain, self.manifest_path)
        self.command_config = self.load_manifest(manifest_io)
        # checked here, for every kind of file: an include and a blueprint spec have no model field for it
        self.manifest_version = self.command_config.pop("manifestVersion", LATEST_SCHEMA_VERSION)
        if problem := manifest_version_problem(self.manifest_version):
            exit_err(f"~ error validating {manifest_io.name}: {problem}")
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
            try:
                self.cli = generate_cli(self.manifest, commander_cls=commander_cls)
            except ValueError as e:
                # a script that is not valid (ScriptError), or a name, param or template no code can be
                # generated for: reported the same way by every command, without a traceback
                exit_err(f"~ error in {manifest_io.name}: {e}")
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
        return normalize_reference(in_file, os.path.dirname(self.manifest_path))

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
        include_path = self.find_include(self.manifest_path, path)
        if include_path is None:
            exit_err(f"~ error loading manifest: `{self.manifest_io.name}` includes `{path}`, which does not exist")

        if os.path.realpath(include_path) in self.include_chain:
            cycle = " -> ".join([*self.include_chain, os.path.realpath(include_path)])
            exit_err(f"~ error loading manifest: circular include {cycle}")

        with open(include_path, encoding="utf-8") as m:
            return type(self)(m, as_include=True, include_chain=self.include_chain)

    @staticmethod
    def find_include(manifest_path: str, path: str) -> str | None:
        """Path of an included file: next to the including manifest first, then in the working directory."""
        candidates = [os.path.join(os.path.dirname(manifest_path), path), path]
        return next((candidate for candidate in candidates if os.path.isfile(candidate)), None)

    @staticmethod
    def load_manifest(manifest_io: TextIO) -> dict[str, Any]:
        """Reads a manifest file: it is rendered as a Jinja template with its own `vars`, then parsed as YAML."""
        try:
            manifest_path = os.path.realpath(manifest_io.name)
            with open(manifest_path, encoding="utf-8") as manifest_file:
                source = manifest_file.read()
            raw_manifest = yaml.safe_load(source)
            if not isinstance(raw_manifest, dict):
                exit_err(f"~ error loading manifest: {manifest_io.name} must be a YAML mapping")

            manifest_vars = raw_manifest.get("vars") or {}
            if not isinstance(manifest_vars, dict):
                exit_err(f"~ error loading manifest: vars in {manifest_io.name} must be a mapping")

            context = resolve_vars(manifest_vars, manifest_io.name)
            manifest = yaml.safe_load(render_manifest(source, context, manifest_io.name))
            if not isinstance(manifest, dict):
                exit_err(f"~ error loading manifest: {manifest_io.name} must be a YAML mapping")
            return manifest
        except yaml.YAMLError as e:
            out(f"{e}")
            exit_err("~ error loading manifest")


JINJA = Environment(loader=BaseLoader())
TEMPLATE_FILE = "<template>"


def resolve_vars(manifest_vars: dict[Any, Any], source: str) -> dict[str, Any]:
    """Values of the manifest's `vars` for use in `{{ }}` placeholders, plus `env`.

    A string value is a Jinja template itself and may use other vars, whatever the order they are written
    in. Numbers and booleans keep their type, so `{{ port + 1 }}` works.
    """
    # `env` is passed to the templates as-is. Environment values are data: they are never
    # rendered as templates themselves.
    resolved: dict[Any, Any] = {}

    def render(text: str, name: Any) -> str:
        try:
            return JINJA.from_string(text).render({**resolved, "env": os.environ})
        except Exception as e:
            exit_err(f"~ error loading manifest: {source}, vars.{name}: {jinja_problem(e)}\n    {text}")

    def resolve(name: Any, chain: tuple[Any, ...]) -> None:
        if name in resolved:
            return
        if name in chain:
            circle = " -> ".join(str(link) for link in (*chain[chain.index(name) :], name))
            exit_err(
                f"~ error loading manifest: {source}: vars reference each other in a circle: {circle}. "
                "A var cannot be built from itself."
            )

        value = manifest_vars[name]
        if isinstance(value, bool | int | float):
            resolved[name] = value
            return

        text = str(value)
        try:
            references = meta.find_undeclared_variables(JINJA.parse(text))
        except TemplateSyntaxError as e:
            exit_err(f"~ error loading manifest: {source}, vars.{name}: {jinja_problem(e)}\n    {text}")
        for reference in sorted(references):
            if reference in manifest_vars and reference != "env":
                resolve(reference, (*chain, name))
        resolved[name] = render(text, name)

    for name in manifest_vars:
        resolve(name, ())

    # a key can be a template too
    context: dict[str, Any] = {render(str(name), name): value for name, value in resolved.items()}
    context["env"] = os.environ
    return context


def render_manifest(source: str, context: dict[str, Any], name: str) -> str:
    """Renders the text of a manifest file as a Jinja template.

    The whole file is the template, YAML comments included: a `{% for %}` loop is written in comments so
    that the file stays valid YAML. A Jinja error is reported with the line of the manifest it is on.
    """
    try:
        return JINJA.from_string(source).render(context)
    except Exception as e:
        if isinstance(e, TemplateSyntaxError):
            line_number: int | None = e.lineno
        else:
            frames = [frame for frame in traceback.extract_tb(e.__traceback__) if frame.filename == TEMPLATE_FILE]
            line_number = frames[-1].lineno if frames else None

        lines = source.splitlines()
        where = f"{name}, line {line_number}" if line_number else name
        line = f"\n    {lines[line_number - 1].strip()}" if line_number and 0 < line_number <= len(lines) else ""
        exit_err(
            f"~ error loading manifest: {where}: {jinja_problem(e)}{line}\n"
            "  The whole file is a Jinja template, comments included. "
            "To keep braces as text, wrap them in {% raw %} and {% endraw %}."
        )


def jinja_problem(error: Exception) -> str:
    if isinstance(error, TemplateSyntaxError):
        return f"Jinja syntax error: {error.message}"
    return f"Jinja could not render this: {type(error).__name__}: {error}"


def source_files(manifest_path: str, blueprint: str | None = None) -> set[str]:
    """Real paths of the files a CLI is generated from: the manifest, the manifests it includes and the
    Python file of its blueprint. This is what `cli dev` watches.

    Nothing is validated or generated. A file that cannot be read yet (it is being edited) is still listed,
    without the files it would refer to.
    """
    files: set[str] = set()

    def read(path: str) -> dict[str, Any]:
        try:
            # a problem is reported when the file is transformed, not here
            with open(path, encoding="utf-8") as manifest_io, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return Transformer.load_manifest(manifest_io)
        except (Exception, SystemExit):
            return {}

    def add_manifest(path: str, is_include: bool) -> None:
        real_path = os.path.realpath(path)
        if real_path in files:
            return
        files.add(real_path)
        config = read(real_path)

        if not is_include:
            in_file = config.get(BLUEPRINT_KEY)
            if blueprint:
                reference: str | None = normalize_reference(blueprint)
            elif isinstance(in_file, str) and in_file.strip():
                reference = normalize_reference(in_file, os.path.dirname(real_path))
            else:
                reference = None
            if reference:
                # a blueprint spec is not merged with includes
                if blueprint_path := blueprint_file(reference):
                    files.add(os.path.realpath(blueprint_path))
                return

        includes = config.get("includes")
        for include in includes if isinstance(includes, list) else []:
            if include_path := Transformer.find_include(real_path, str(include)):
                add_manifest(include_path, is_include=True)

    add_manifest(manifest_path, is_include=False)
    return files
