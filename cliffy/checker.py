"""Checks the code generated for a manifest and reports problems in the manifest's terms."""

from __future__ import annotations

import re
import traceback

import typer

from cliffy.commander import CLI

GENERATED_FILE = "<generated CLI>"
FUNCTION_DEFINITION = re.compile(r"(?:async\s+)?def (\w+)\(")
MODULE_LEVEL = "module level code (`imports`, `vars`, `types` or `functions`)"


class GeneratedCodeError(Exception):
    """The code generated for a manifest does not compile or does not import.

    The message names the part of the manifest the failing code was generated from.
    """


def locate(cli: CLI, line_number: int) -> str:
    """Part of the manifest that line `line_number` (1-based) of the generated code was generated from."""
    lines = cli.code.splitlines()
    index = min(max(line_number, 1), len(lines)) - 1

    # a decorator belongs to the function below it
    while index < len(lines) - 1 and lines[index].startswith("@"):
        index += 1

    for line in reversed(lines[: index + 1]):
        if match := FUNCTION_DEFINITION.match(line):
            return cli.functions.get(match.group(1), MODULE_LEVEL)
    return MODULE_LEVEL


def describe(cli: CLI, error: BaseException, line_number: int | None) -> str:
    where = locate(cli, line_number) if line_number else MODULE_LEVEL
    message = f"{where}: {type(error).__name__}: {error.msg if isinstance(error, SyntaxError) else error}"
    lines = cli.code.splitlines()
    if line_number and 0 < line_number <= len(lines):
        message += f"\n    {lines[line_number - 1].strip()}"
    return message


def check_generated_code(cli: CLI) -> None:
    """Compiles and imports the generated code, and builds the command tree of a Typer CLI.

    Importing defines the commands, it does not run them.

    Raises:
        GeneratedCodeError: the code is not valid Python, or fails while it is imported.
    """
    try:
        # dont_inherit: this module's own `from __future__ import annotations` must not apply to the generated code
        compiled = compile(cli.code, GENERATED_FILE, "exec", dont_inherit=True)
    except SyntaxError as e:
        raise GeneratedCodeError(describe(cli, e, e.lineno)) from e

    try:
        namespace: dict[str, object] = {"__name__": f"cliffy_check_{cli.name.replace('-', '_')}"}
        exec(compiled, namespace)
        app = namespace.get("cli")
        if isinstance(app, typer.Typer):
            # Typer reads the signature of a command when the CLI starts. From Python 3.14 on annotations
            # are evaluated lazily, so a param with an unknown type only fails here
            typer.main.get_command(app)
    except (Exception, SystemExit) as e:
        generated_frames = [
            frame for frame in traceback.extract_tb(e.__traceback__) if frame.filename == GENERATED_FILE
        ]
        line_number = generated_frames[-1].lineno if generated_frames else None
        raise GeneratedCodeError(describe(cli, e, line_number)) from e
