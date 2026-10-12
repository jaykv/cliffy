"""Blueprints: bring your own YAML vocabulary.

A blueprint is a typed spec. It is a pydantic model that describes a custom YAML schema, plus a
``to_manifest`` method that says how that schema maps onto a cliffy manifest. Everything downstream of the
manifest (both commanders, ``render``, ``test``, ``docs``, ``build``) works unchanged.

A YAML file selects its blueprint with a top-level ``blueprint:`` key or with ``--blueprint`` on the command
line. A blueprint reference is one of:

* a path to a Python file, optionally with a class name: ``./tasks.py`` or ``./tasks.py:Tasks``
* an importable class: ``package.module:Tasks`` (or ``package.module`` when it defines one blueprint)
* the name of an installed plugin, registered under the ``cliffy.blueprints`` entry-point group
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError

from cliffy.manifest import CLIManifest

ENTRY_POINT_GROUP = "cliffy.blueprints"
BLUEPRINT_KEY = "blueprint"


class BlueprintError(Exception):
    """A blueprint could not be found, loaded or applied. The message is meant to be shown to the user."""


class Blueprint(BaseModel, ABC):
    """Base class for a custom YAML spec.

    Subclass it, declare the fields of your spec as pydantic fields, and implement ``to_manifest``.
    Unknown keys are rejected by default so that typos in a spec are reported; set
    ``model_config = ConfigDict(extra="ignore")`` in a subclass to change that.

    Hooks run in this order::

        pre_validate(raw dict) -> validation -> to_manifest() -> post_manifest(manifest) -> post_codegen(code)
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    @classmethod
    def pre_validate(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """Hook: adjust the raw YAML mapping before it is validated against the spec."""
        return raw

    @abstractmethod
    def to_manifest(self) -> CLIManifest | dict[str, Any]:
        """Map the validated spec onto a cliffy manifest (a ``CLIManifest`` or a mapping that validates as one)."""

    def post_manifest(self, manifest: CLIManifest) -> CLIManifest:
        """Hook: adjust the manifest after ``to_manifest`` and before code generation."""
        return manifest

    def post_codegen(self, code: str) -> str:
        """Hook: adjust the generated CLI source code."""
        return code

    @classmethod
    def describe(cls) -> str:
        """One-line description of the blueprint: the first line of the class docstring."""
        doc = inspect.cleandoc(cls.__doc__ or "")
        return doc.splitlines()[0] if doc else ""

    @classmethod
    def spec_json_schema(cls) -> dict[str, Any]:
        """JSON schema for YAML files written in this spec, including the optional ``blueprint`` key."""
        schema = cls.model_json_schema()
        schema.setdefault("properties", {}).setdefault(
            BLUEPRINT_KEY,
            {"type": "string", "title": "Blueprint", "description": "Blueprint that turns this file into a CLI."},
        )
        return schema


@dataclass(frozen=True)
class InstalledBlueprint:
    """A blueprint registered by an installed package under the ``cliffy.blueprints`` entry-point group."""

    name: str
    target: str
    package: str
    entry_point: EntryPoint

    def load(self) -> type[Blueprint]:
        try:
            loaded = self.entry_point.load()
        except Exception as e:
            raise BlueprintError(
                f"could not load blueprint `{self.name}` ({self.target}) from package `{self.package}`: "
                f"{type(e).__name__}: {e}"
            ) from e
        if inspect.ismodule(loaded):
            return _pick_blueprint_class(loaded, None, self.target)
        return _ensure_blueprint_class(loaded, self.target)


def installed_blueprints() -> list[InstalledBlueprint]:
    """All blueprints provided by installed packages, sorted by name."""
    found = [
        InstalledBlueprint(name=ep.name, target=ep.value, package=ep.dist.name if ep.dist else "", entry_point=ep)
        for ep in entry_points(group=ENTRY_POINT_GROUP)
    ]
    return sorted(found, key=lambda bp: (bp.name, bp.package))


def normalize_reference(reference: str, base_dir: str | os.PathLike[str] | None = None) -> str:
    """Make a file reference absolute (relative to ``base_dir``, default: cwd). Other references are unchanged."""
    target, attr = _split_reference(reference.strip())
    if not _is_file_reference(target):
        return reference.strip()
    path = Path(target).expanduser()
    if not path.is_absolute():
        path = Path(base_dir or Path.cwd()) / path
    resolved = str(path.resolve())
    return f"{resolved}:{attr}" if attr else resolved


def resolve_blueprint(reference: str, base_dir: str | os.PathLike[str] | None = None) -> type[Blueprint]:
    """Resolve a blueprint reference to a ``Blueprint`` subclass.

    Raises:
        BlueprintError: the reference does not exist, is ambiguous, or is not a blueprint.
    """
    reference = reference.strip()
    if not reference:
        raise BlueprintError("empty blueprint reference")

    target, attr = _split_reference(reference)
    if _is_file_reference(target):
        path = Path(_split_reference(normalize_reference(reference, base_dir))[0])
        if not path.is_file():
            raise BlueprintError(f"blueprint file not found: {path}")
        return _pick_blueprint_class(_import_file(path), attr, str(path))

    if attr is None:
        plugins = [bp for bp in installed_blueprints() if bp.name == target]
        if len(plugins) > 1:
            providers = ", ".join(f"{bp.package} ({bp.target})" for bp in plugins)
            raise BlueprintError(
                f"blueprint `{target}` is ambiguous, it is provided by: {providers}. "
                "Use a `module:Class` reference to pick one."
            )
        if plugins:
            return plugins[0].load()

    return _pick_blueprint_class(_import_module(target, reference), attr, target)


def build_manifest(
    blueprint_cls: type[Blueprint], raw: dict[str, Any], source: str = "spec"
) -> tuple[Blueprint, CLIManifest]:
    """Validate ``raw`` against the blueprint's spec and transform it into a cliffy manifest.

    Raises:
        BlueprintError: the spec is invalid, or the blueprint produced an invalid manifest.
    """
    name = blueprint_cls.__name__
    data = {key: value for key, value in raw.items() if key != BLUEPRINT_KEY}
    try:
        spec = blueprint_cls.model_validate(blueprint_cls.pre_validate(data))
    except ValidationError as e:
        raise BlueprintError(f"{source} is not a valid {name} spec\n{format_validation_error(e)}") from e
    except Exception as e:
        raise BlueprintError(f"blueprint {name} failed to validate {source}: {type(e).__name__}: {e}") from e

    try:
        produced = spec.to_manifest()
        manifest = produced if isinstance(produced, CLIManifest) else CLIManifest.model_validate(produced)
        manifest = spec.post_manifest(manifest)
    except ValidationError as e:
        raise BlueprintError(
            f"blueprint {name} produced an invalid cliffy manifest for {source}\n{format_validation_error(e)}"
        ) from e
    except Exception as e:
        raise BlueprintError(f"blueprint {name} failed to transform {source}: {type(e).__name__}: {e}") from e

    if not isinstance(manifest, CLIManifest):
        raise BlueprintError(f"blueprint {name}.post_manifest must return a CLIManifest, got {type(manifest).__name__}")
    return spec, manifest


def format_validation_error(error: ValidationError) -> str:
    """Render a pydantic validation error as one ``  path.to.key: message`` line per problem."""
    lines = []
    for problem in error.errors():
        location = ""
        for part in problem["loc"]:
            location += f"[{part}]" if isinstance(part, int) else f".{part}" if location else str(part)
        value = problem.get("input")
        got = "" if isinstance(value, dict | list) or value is None else f" (got {value!r})"
        lines.append(f"  {location or '<root>'}: {problem['msg']}{got}")
    return "\n".join(lines)


def _split_reference(reference: str) -> tuple[str, str | None]:
    """``target:Class`` -> (target, Class). A Windows drive letter is not mistaken for a target."""
    target, sep, attr = reference.rpartition(":")
    if sep and target and attr.isidentifier():
        return target, attr
    return reference, None


def _is_file_reference(target: str) -> bool:
    return target.endswith(".py") or "/" in target or os.sep in target


def _import_file(path: Path) -> ModuleType:
    digest = hashlib.sha256(str(path).encode()).hexdigest()[:12]
    module_name = f"cliffy_blueprint_{digest}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise BlueprintError(f"blueprint file is not a Python module: {path}")

    module = importlib.util.module_from_spec(spec)
    # registered while executing so that pydantic can resolve the module's postponed annotations
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        sys.modules.pop(module_name, None)
        raise BlueprintError(f"could not import blueprint file {path}: {type(e).__name__}: {e}") from e
    return module


def _import_module(module_name: str, reference: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name and (module_name == e.name or module_name.startswith(f"{e.name}.")):
            known = ", ".join(bp.name for bp in installed_blueprints()) or "none"
            raise BlueprintError(
                f"blueprint `{reference}` not found. It is not an installed blueprint (installed: {known}), "
                "not an importable module, and not a path to a .py file."
            ) from e
        raise BlueprintError(f"could not import blueprint `{reference}`: {type(e).__name__}: {e}") from e
    except Exception as e:
        raise BlueprintError(f"could not import blueprint `{reference}`: {type(e).__name__}: {e}") from e


def _is_concrete_blueprint(obj: Any) -> bool:
    return inspect.isclass(obj) and issubclass(obj, Blueprint) and not inspect.isabstract(obj)


def _ensure_blueprint_class(obj: Any, reference: str) -> type[Blueprint]:
    if not _is_concrete_blueprint(obj):
        raise BlueprintError(
            f"`{reference}` is not a blueprint. A blueprint is a subclass of cliffy.blueprint.Blueprint "
            "that implements to_manifest()."
        )
    blueprint_cls: type[Blueprint] = obj
    return blueprint_cls


def _pick_blueprint_class(module: ModuleType, attr: str | None, reference: str) -> type[Blueprint]:
    if attr:
        if not hasattr(module, attr):
            raise BlueprintError(f"`{reference}` has no attribute `{attr}`")
        return _ensure_blueprint_class(getattr(module, attr), f"{reference}:{attr}")

    candidates = [obj for obj in vars(module).values() if _is_concrete_blueprint(obj)]
    # prefer the blueprints defined in the module over the ones it only imports
    defined = [obj for obj in candidates if obj.__module__ == module.__name__]
    candidates = defined or candidates
    if not candidates:
        raise BlueprintError(
            f"no blueprint found in `{reference}`. Define a subclass of cliffy.blueprint.Blueprint "
            "that implements to_manifest()."
        )
    if len(candidates) > 1:
        names = ", ".join(sorted(cls.__name__ for cls in candidates))
        raise BlueprintError(
            f"`{reference}` defines more than one blueprint ({names}). Pick one with `{reference}:ClassName`."
        )
    blueprint_cls: type[Blueprint] = candidates[0]
    return blueprint_cls
