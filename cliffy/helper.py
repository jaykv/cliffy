import os
import pathlib
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table

HOME_PATH = str(pathlib.Path.home())
PYTHON_BIN = f"{sys.exec_prefix}/bin"
PYTHON_EXECUTABLE = sys.executable
CLIFFY_CLI_DIR = f"{pathlib.Path(__file__).parent.resolve()}/clis"
CLIFFY_HOME_PATH = f"{HOME_PATH}/.cliffy"


def write_to_file(path: str, text: str, executable: bool = False) -> bool:
    try:
        output_file = pathlib.Path(path)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(text)
    except Exception as e:
        print("write_to_file", e)
        return False

    if executable:
        make_executable(path)

    return True


def make_executable(path: str) -> None:
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)


def wrap_as_comment(text: str, split_on: Optional[str] = None) -> str:
    if split_on:
        joiner = "\n# "
        return "# " + joiner.join(text.split(split_on))

    return f"# {text}"


def print_rich_table(cols: list[str], rows: list[list[str]], styles: list[str]) -> None:
    table = Table()
    for style, col in zip(styles, cols):
        table.add_column(col, style=style)
    for row in rows:
        table.add_row(*row)

    console = Console()
    console.print(table)
