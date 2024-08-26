import contextlib
import operator
import os
import platform
import subprocess
import sys
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from tempfile import _TemporaryFileWrapper
from typing import Any, NoReturn, Optional

from click import secho
from packaging import version
from pydantic import BaseModel
from types import ModuleType
from importlib.util import spec_from_file_location, module_from_spec


CLIFFY_CLI_DIR = files("cliffy").joinpath("clis")
CLIFFY_METADATA_DIR = files("cliffy").joinpath("metadata")
PYTHON_BIN = (
    f"{os.path.join(sys.exec_prefix, 'Scripts')}"
    if platform.system() == "Windows"
    else f"{os.path.join(sys.exec_prefix, 'bin')}"
)
PYTHON_EXECUTABLE = sys.executable
OPERATOR_MAP = {
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    "<": operator.lt,
    ">": operator.gt,
}
TEMP_FILES: list[_TemporaryFileWrapper] = []


class RequirementSpec(BaseModel):
    name: str
    operator: Optional[str]
    version: Optional[str]


def write_to_file(path: str, text: str, executable: bool = False) -> None:
    output_file = Path(path)
    output_file.parent.mkdir(exist_ok=True, parents=True)
    output_file.write_text(text)

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
        raise ImportError(f"Failed to import module from {filepath}: {e}")


def make_executable(path: str) -> None:
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)


def delete_temp_files() -> None:
    for file in TEMP_FILES:
        with contextlib.suppress(Exception):
            file.close()
            os.unlink(file.name)


def indent_block(block: str, spaces=4) -> str:
    return "\n".join([" " * spaces + line for line in block.splitlines()])


def wrap_as_comment(text: str, split_on: Optional[str] = None) -> str:
    if split_on:
        joiner = "\n# "
        return f"# {joiner.join(text.split(split_on))}"

    return f"# {text}"


def wrap_as_var(text: str) -> str:
    return "{{" + text + "}}"


def get_installed_package_versions() -> dict[str, str]:
    reqs = subprocess.check_output([sys.executable, "-m", "pip", "freeze"])
    installed_packages = {}
    for r in reqs.split():
        r_spec = r.decode().lower().split("==")
        if len(r_spec) > 1:
            installed_packages[r_spec[0]] = r_spec[1]
    return installed_packages


def parse_requirement(requirement: str) -> RequirementSpec:
    for op in OPERATOR_MAP:
        if op in requirement:
            parts = requirement.replace(" ", "").split(op)
            return RequirementSpec(name=parts[0], operator=op, version=parts[1])

    return RequirementSpec(name=requirement.strip(), operator=None, version=None)


def compare_versions(version1: str, version2: str, op: Optional[str] = "=") -> bool:
    v1 = version.parse(version1)
    v2 = version.parse(version2)

    return OPERATOR_MAP[op](v1, v2) if op else v1 == v2


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
