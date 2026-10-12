import builtins
import contextlib
import json
import keyword
import os
import platform
import re
import sys
from datetime import datetime
from importlib.metadata import distributions
from importlib.resources import files
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import _TemporaryFileWrapper
from types import ModuleType
from typing import IO, Any, NoReturn

from click import File, secho
from click.core import Context, Parameter
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

CLIFFY_CLI_DIR = files("cliffy").joinpath("clis")
CLIFFY_METADATA_DIR = files("cliffy").joinpath("metadata")
PYTHON_BIN = (
    f"{os.path.join(sys.exec_prefix, 'Scripts')}"
    if platform.system() == "Windows"
    else f"{os.path.join(sys.exec_prefix, 'bin')}"
)
PYTHON_EXECUTABLE = sys.executable
# Names the generated module defines or imports itself. A command function with one of these names
# would replace the object the rest of the generated code relies on.
GENERATED_NAMES = frozenset(
    {
        "Any",
        "CONTEXT_SETTINGS",
        "Optional",
        "_pybash",
        "aliases_callback",
        "cli",
        "click",
        "main",
        "show_aliases",
        "subprocess",
        "typer",
        "version_callback",
    }
)
CLI_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
TEMP_FILES: list[_TemporaryFileWrapper] = []


class ManifestOrCLI(File):
    def convert(  # type: ignore[override]
        self, value: str | os.PathLike[str] | IO[Any], param: Parameter | None, ctx: Context | None
    ) -> str | IO[Any]:
        if isinstance(value, str):
            # a manifest path is opened, anything else is treated as the name of a loaded CLI
            return super().convert(value, param, ctx) if value.endswith("yaml") else value

        if isinstance(value, os.PathLike):
            return super().convert(value, param, ctx)

        # already a file-like object
        return value


def write_to_file(path: str, text: str, executable: bool = False) -> None:
    output_file = Path(path)
    output_file.parent.mkdir(exist_ok=True, parents=True)
    # generated code and manifests are always UTF-8, whatever the locale encoding is
    output_file.write_text(text, encoding="utf-8")

    if executable:
        make_executable(path)


def import_module_from_path(filepath: str) -> ModuleType:
    try:
        path = Path(filepath)
        module_name = path.stem
        spec = spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load module from {filepath}")

        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        raise ImportError(f"Failed to import module from {filepath}: {e}") from e


def make_executable(path: str) -> None:
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)


def delete_temp_files() -> None:
    for file in TEMP_FILES:
        with contextlib.suppress(Exception):
            file.close()
            os.unlink(file.name)
    TEMP_FILES.clear()


def indent_block(block: str, spaces: int = 4) -> str:
    return "\n".join([" " * spaces + line for line in block.splitlines()])


def wrap_as_comment(text: str, split_on: str | None = None) -> str:
    if split_on:
        joiner = "\n# "
        return f"# {joiner.join(text.split(split_on))}"

    return f"# {text}"


def wrap_as_var(text: str) -> str:
    return "{{" + text + "}}"


def py_str(value: object) -> str:
    """Returns a double-quoted Python string literal for value.

    Manifest text (help, defaults, versions, ...) must go through this (or `repr`) before it is
    placed in generated source, so quotes, backslashes and newlines cannot break out of the literal.
    """
    return json.dumps(str(value), ensure_ascii=False)


def to_identifier(name: str) -> str:
    """Turns name into a Python identifier that does not hide a keyword, a builtin or a generated name.

    a-b -> a_b, 2fa -> _2fa, import -> import_, list -> list_, cli -> cli_
    """
    identifier = re.sub(r"\W", "_", name)
    if not identifier or identifier[0].isdigit():
        identifier = f"_{identifier}"
    if keyword.iskeyword(identifier) or identifier in GENERATED_NAMES or hasattr(builtins, identifier):
        identifier += "_"
    if not identifier.isidentifier():
        raise ValueError(f"Cannot turn {name!r} into a Python identifier")
    return identifier


def get_installed_package_versions() -> dict[str, str]:
    """Installed distributions of the running interpreter, keyed by normalized (PEP 503) name."""
    installed_packages: dict[str, str] = {}
    for dist in distributions():
        if name := dist.metadata["Name"]:
            # the first match on sys.path is the one that gets imported
            installed_packages.setdefault(canonicalize_name(name), dist.version)
    return installed_packages


def check_requirement(requirement: str, installed_packages: dict[str, str]) -> str | None:
    """Checks a PEP 508 requirement against the installed packages.

    Returns:
        None when the requirement is met (or its environment marker does not apply),
        otherwise a description of what is wrong.
    """
    try:
        req = Requirement(requirement)
    except InvalidRequirement as e:
        return f"invalid requirement: {e}"

    if req.marker and not req.marker.evaluate():
        return None

    installed_version = installed_packages.get(canonicalize_name(req.name))
    if installed_version is None:
        return "not installed"

    if not req.specifier.contains(installed_version, prereleases=True):
        return f"found version `{installed_version}`"

    return None


def out(text: str, **echo_kwargs: Any) -> None:
    secho(text, **echo_kwargs)


def out_err(text: str) -> None:
    secho(f"{text} 💔", fg="red", err=True)


def exit_err(text: str) -> NoReturn:
    secho(f"{text} 💔", fg="red", err=True)
    raise SystemExit(1)


def age_datetime(date: datetime) -> str:
    delta = datetime.now() - date
    if delta.days > 0:
        return f"{delta.days}d"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600}h"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60}m"
    return f"{delta.seconds}s"
