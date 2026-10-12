import ast
import inspect
import linecache
import os
import traceback
from collections.abc import Generator
from typing import cast

import pybash
from click import unstyle
from click.testing import CliRunner as ClickCliRunner
from click.testing import Result
from pydantic import BaseModel, field_validator
from typer.testing import CliRunner

from cliffy.checker import describe
from cliffy.helper import import_generated_code
from cliffy.manifest import CLIManifest, Command, RunBlock
from cliffy.parser import Parser, transform_script
from cliffy.transformer import Transformer

# File name of the assertions of a test case in tracebacks
ASSERTION_FILE = "<test assertion>"


class GeneratedImportError(ImportError):
    """The code generated for the manifest fails while it is imported.

    The message names the part of the manifest the failing code was generated from.
    """


class TestCase(BaseModel):
    command: str
    assert_script: str


class ShellScript(BaseModel):
    command: str

    @field_validator("command", mode="after")
    @classmethod
    def is_shelled(cls, value: str) -> str:
        if value.startswith((">", "$")):
            return value

        raise ValueError(
            "A shell step in tests must start with $ or >. "
            "Use $ to run the command directly, without a shell. "
            "Use > to run it through a shell (pipes into shell builtins, globs). WARNING: this can be dangerous."
        )


class Tester:
    def __init__(self, manifest_path: str, blueprint: str | None = None) -> None:
        with open(manifest_path, encoding="utf-8") as manifest_io:
            self.T = Transformer(manifest_io, blueprint=blueprint)

        # module_path is the file name of the generated code in tracebacks. The file itself is gone
        module_name = f"{self.T.cli.name.replace('-', '_')}_test"
        try:
            self.module, self.module_path = import_generated_code(self.T.cli.code, module_name)
        except ImportError as e:
            raise GeneratedImportError(self.describe_import_error(e, f"{module_name}.py")) from e
        # the lines of a traceback are read from here (`cli test --traceback`)
        code_lines = self.T.cli.code.splitlines(keepends=True)
        linecache.cache[self.module_path] = (len(self.T.cli.code), None, code_lines, self.module_path)

        self.module_funcs = inspect.getmembers(self.module, inspect.isfunction)

        manifest = cast(CLIManifest, self.T.manifest)
        # typer vendors its own click and its runner only accepts typer apps: a CLI generated with
        # `use_click` is a plain click group and needs click's own runner
        self.runner: CliRunner | ClickCliRunner = ClickCliRunner() if manifest.use_click else CliRunner()
        self.parser = Parser(manifest)

        self.test_pipeline: list[ShellScript | TestCase] = []
        self.total_cases = 0

        for t in self.T.manifest.tests:
            if isinstance(t, str):
                # assume it's a shell command
                self.test_pipeline.append(ShellScript(command=t))
            elif isinstance(t, dict):
                test_cases = [TestCase(command=command, assert_script=script) for command, script in t.items()]
                self.total_cases += len(test_cases)
                self.test_pipeline.extend(test_cases)

    def invoke_shell(self, script: ShellScript) -> None:
        py_code = pybash.transform(script.command, runtime=pybash.RUNTIME_NAME)
        exec(pybash.header() + py_code)

    def invoke_test(self, command: str, script: str) -> Generator[Result, None, None]:
        result = self.runner.invoke(self.module.cli, command)
        # Assertions compare text. rich styles help output when it thinks it runs on a CI system, so the
        # same test would see `--name` on one machine and escape codes inside it on another.
        for stream in ("stdout_bytes", "stderr_bytes", "output_bytes"):
            captured = getattr(result, stream, None)
            if isinstance(captured, bytes):
                setattr(
                    result, stream, unstyle(captured.decode(self.runner.charset, "replace")).encode(self.runner.charset)
                )
        yield result
        code = compile(script, ASSERTION_FILE, "exec")
        exec(code, {}, {"result": result, "result_text": result.output.strip()})

    def describe_import_error(self, error: ImportError, file_name: str) -> str:
        """Why the generated code does not import, against the part of the manifest it comes from."""
        cause = error.__cause__ or error
        if isinstance(cause, SyntaxError):
            line_number = cause.lineno
        else:
            frames = [
                frame
                for frame in traceback.extract_tb(cause.__traceback__)
                if os.path.basename(frame.filename) == file_name
            ]
            line_number = frames[-1].lineno if frames else None
        return describe(self.T.cli, cause, line_number)

    def describe_exception(self, command: str, result: Result) -> str | None:
        """An exception a command ended with, in the manifest's terms. None when it did not raise.

        `command `db.create` raised ValueError: no such table`, then the line of the script it was
        raised on as it is written in the manifest. No frame of cliffy, of the framework or of the
        generated module is shown.
        """
        error = result.exception
        if error is None or isinstance(error, SystemExit):
            # an exit code is a result of the command, not a failure of it
            return None

        trace = result.exc_info[2] if result.exc_info else error.__traceback__
        frames = [frame for frame in traceback.extract_tb(trace) if frame.filename == self.module_path and frame.lineno]
        functions = self.T.cli.functions
        owner = next((frame for frame in reversed(frames) if frame.name in functions), None)
        who = functions[owner.name] if owner else f"`{self.T.cli.name} {command}`"
        message = f"💥 {who} raised {type(error).__name__}: {error}"

        code_lines = self.T.cli.code.splitlines()
        if owner and owner.lineno:
            message += f"\n    {self.locate_line(owner.name, owner.lineno)}"
        if frames and frames[-1] is not owner and (line_number := frames[-1].lineno):
            # raised further in: in a function of the `functions` section, or in a function defined in the script
            located = self.locate_line(owner.name, line_number, or_none=True) if owner else None
            source = code_lines[line_number - 1].strip() if line_number <= len(code_lines) else ""
            message += f"\n    {located or f'in `{frames[-1].name}` (functions): {source}'}"
        return message

    def locate_line(self, function_name: str, line_number: int, or_none: bool = False) -> str | None:
        """Line `line_number` of the generated code as `run, line 2: <that line of the manifest>`.

        Falls back to the generated line itself when it is not part of a script of the function, i.e.
        when a blueprint changed the code after it was generated.
        """
        code_lines = self.T.cli.code.splitlines()
        fallback = None if or_none else code_lines[line_number - 1].strip()
        function = next(
            (
                node
                for node in ast.parse(self.T.cli.code).body
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function_name
            ),
            None,
        )
        if function is None or not function.lineno <= line_number <= (function.end_lineno or 0):
            return fallback

        # the scripts follow each other in the body, each as `Parser.parse_run_block` wrote it
        blocks = []
        for key, script in self.T.cli.blocks.get(function_name, []):
            transformed = transform_script(script, key)
            skipped = (len(transformed) - len(transformed.lstrip())) and transformed[
                : len(transformed) - len(transformed.lstrip())
            ].count("\n")
            blocks.append((key, script, skipped, [" " * 4 + line for line in transformed.strip().split("\n")]))

        body = [line for _, _, _, generated in blocks for line in generated]
        last = function.end_lineno or function.lineno
        start = next(
            (first for first in range(function.lineno + 1, last + 1) if code_lines[first - 1 : last] == body), None
        )
        if start is None:
            return fallback

        for key, script, skipped, generated in blocks:
            if line_number < start + len(generated):
                script_line = line_number - start + skipped + 1
                return f"{key}, line {script_line}: {script.split(chr(10))[script_line - 1].strip()}"
            start += len(generated)
        return fallback

    def is_valid_command(self, command: str) -> bool:
        command_name = command.split(" ")[0]
        cmd = Command(name=command_name, run=RunBlock(""))
        command_func_name = self.parser.get_command_func_name(cmd)
        matching_command_func = [func for fname, func in self.module_funcs if fname == command_func_name]
        return bool(matching_command_func)
