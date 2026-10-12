import inspect
from collections.abc import Generator
from tempfile import NamedTemporaryFile
from typing import cast

from click import unstyle
from click.testing import CliRunner as ClickCliRunner
from click.testing import Result
from pybash import transformer
from pydantic import BaseModel, field_validator
from typer.testing import CliRunner

from cliffy.helper import TEMP_FILES, delete_temp_files, import_module_from_path
from cliffy.manifest import CLIManifest, Command, RunBlock
from cliffy.parser import Parser
from cliffy.transformer import Transformer


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

        with NamedTemporaryFile(
            mode="w", prefix=f"{self.T.cli.name}_test_", suffix=".py", delete=False, encoding="utf-8"
        ) as runner_file:
            TEMP_FILES.append(runner_file)
            try:
                runner_file.write(self.T.cli.code)
                runner_file.flush()
                self.module = import_module_from_path(runner_file.name)
            finally:
                # also when the generated code fails to import
                delete_temp_files()

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
        py_code = transformer.transform(script.command)
        exec("import subprocess\n" + py_code)

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
        code = compile(script, f"test_{self.T.cli.name}.py", "exec")
        exec(code, {}, {"result": result, "result_text": result.output.strip()})

    def is_valid_command(self, command: str) -> bool:
        command_name = command.split(" ")[0]
        cmd = Command(name=command_name, run=RunBlock(""))
        command_func_name = self.parser.get_command_func_name(cmd)
        matching_command_func = [func for fname, func in self.module_funcs if fname == command_func_name]
        return bool(matching_command_func)
