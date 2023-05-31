import operator
import os
import platform
import subprocess
import sys
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Any, NoReturn, Optional

from click import secho
from packaging import version
from pydantic import BaseModel

try:
    from rich.console import Console  # type: ignore
    from rich.table import Table  # type: ignore
except ImportError:
    from .rich import Console, Table

HOME_PATH = str(Path.home())
PYTHON_BIN = f"{sys.exec_prefix}/Scripts" if platform.system() == "Windows" else f"{sys.exec_prefix}/bin"
PYTHON_EXECUTABLE = sys.executable
CLIFFY_CLI_DIR = files("cliffy.clis")
CLIFFY_HOME_PATH = f"{HOME_PATH}/.cliffy"
OPERATOR_MAP = {
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    "<": operator.lt,
    ">": operator.gt,
}


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


def make_executable(path: str) -> None:
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)


def indent_block(block: str, spaces=4) -> str:
    blocklines = block.splitlines()
    return "\n".join([" " * spaces + line for line in blocklines])


def wrap_as_comment(text: str, split_on: Optional[str] = None) -> str:
    if split_on:
        joiner = "\n# "
        return f"# {joiner.join(text.split(split_on))}"

    return f"# {text}"


def wrap_as_var(text: str) -> str:
    return "{{" + text + "}}"


def print_rich_table(cols: list[str], rows: list[list[str]], styles: list[str]) -> None:
    table = Table()
    for style, col in zip(styles, cols):
        table.add_column(col, style=style)
    for row in rows:
        table.add_row(*row)

    console = Console()
    console.print(table)


def get_installed_pip_packages() -> dict[str, str]:
    reqs = subprocess.check_output([sys.executable, "-m", "pip", "freeze"])
    installed_packages = {}
    for r in reqs.split():
        r_spec = r.decode().split("==")
        if len(r_spec) > 1:
            installed_packages[r_spec[0]] = r_spec[1]
    return installed_packages


def parse_requirement(requirement: str) -> RequirementSpec:
    for op in OPERATOR_MAP:
        if op in requirement:
            parts = requirement.replace(" ", "").split(op)
            return RequirementSpec(name=parts[0], operator=op, version=parts[1])

    return RequirementSpec(name=requirement.strip(), operator=None, version=None)


def compare_versions(version1: str, version2: str, op: str) -> bool:
    v1 = version.parse(version1)
    v2 = version.parse(version2)
    return OPERATOR_MAP[op](v1, v2)


def out(text: str, **echo_kwargs: Any) -> None:
    secho(text, **echo_kwargs)


def out_err(text: str) -> None:
    secho(f"{text} 💔", fg="red", err=True)


def exit_err(text: str) -> NoReturn:
    secho(f"{text} 💔", fg="red", err=True)
    raise SystemExit(1)


def age_datetime(date: datetime) -> str:
    delta = datetime.now() - date
    if delta.seconds > 86400:
        return f"{delta.days}d"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600}h"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60}m"
    return f"{delta.seconds}s"
