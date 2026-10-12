import builtins
import contextlib
import json
import keyword
import os
import platform
import re
import secrets
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, distributions, version
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


def cli_name_problem(name: object) -> str | None:
    """Why `name` cannot be the name of a CLI, or None when it can.

    A name becomes a file name in three directories (launcher, module, metadata record). Whatever a
    command is given as the name of a loaded CLI goes through this first, so that `..` or a path
    separator cannot make it point at a file outside of them.
    """
    if isinstance(name, str) and CLI_NAME_PATTERN.fullmatch(name):
        return None
    return (
        f"{name!r} is not a valid CLI name: a name has letters, digits, `_` and `-` only "
        "and starts with a letter or `_`"
    )


def validate_cli_name(name: str) -> str:
    if problem := cli_name_problem(name):
        raise ValueError(problem)
    return name


def write_to_file(path: str, text: str, executable: bool = False) -> None:
    output_file = Path(path)
    output_file.parent.mkdir(exist_ok=True, parents=True)
    # generated code and manifests are always UTF-8, whatever the locale encoding is
    output_file.write_text(text, encoding="utf-8")

    if executable:
        make_executable(path)


def write_atomically(path: str, text: str, executable: bool = False, replace: bool = True) -> None:
    """Write a file so that `path` is never seen half-written and a symbolic link at `path` is never followed.

    The text goes to a new file in the same directory, which is then moved onto `path`: whatever is
    at `path`, a link included, is replaced as a directory entry, not written through.

    Args:
        replace: With False the file is only created. FileExistsError is raised when something is at
            `path` already, also when it appeared a moment ago, and that file is left alone.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    temp_path = os.path.join(directory, f".{os.path.basename(path)}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    # the mode is reduced by the umask, like that of any new file
    mode = 0o777 if executable else 0o666

    def create(target: str) -> None:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow, mode)
        # generated code and manifests are always UTF-8, whatever the locale encoding is
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(text)

    try:
        create(temp_path)
        if replace:
            os.replace(temp_path, path)
            return
        try:
            # a hard link is only made when nothing has the name
            os.link(temp_path, path)
        except FileExistsError:
            raise
        except (OSError, NotImplementedError):
            # a file system without hard links: created exclusively instead
            create(path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_path)


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


def clean_help(text: str) -> str:
    """Help text as one line per paragraph: a line break becomes a space, a blank line stays a paragraph break.

    Typer and Click reflow the lines of a paragraph and keep paragraphs apart, and both use the first
    paragraph as the summary of a command in the command list.
    """
    paragraphs = (" ".join(paragraph.split()) for paragraph in re.split(r"\n\s*\n", text or ""))
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


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


def cliffy_version() -> str:
    """Version of the installed cliffy package"""
    try:
        return version("cliffy")
    except PackageNotFoundError:  # pragma: no cover - cliffy is run from a source tree that is not installed
        return "unknown"


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
