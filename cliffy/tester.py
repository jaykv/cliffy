from typing import Generator
from click.testing import Result
from typer.testing import CliRunner
from cliffy.commander import Command
from cliffy.parser import Parser
from cliffy.transformer import Transformer
from cliffy.helper import import_module_from_path, delete_temp_files, TEMP_FILES
from tempfile import NamedTemporaryFile
import inspect


class Tester:
    def __init__(self, manifest_path: str) -> None:
        with open(manifest_path, "r") as manifest_io:
            self.T = Transformer(manifest_io)

        with NamedTemporaryFile(mode="w", prefix=f"{self.T.cli.name}_test_", suffix=".py", delete=False) as runner_file:
            runner_file.write(self.T.cli.code)
            runner_file.flush()
            self.module = import_module_from_path(runner_file.name)
            TEMP_FILES.append(runner_file)

        self.module_funcs = inspect.getmembers(self.module, inspect.isfunction)
        delete_temp_files()

        self.runner = CliRunner()
        self.parser = Parser(self.T.manifest)

    def invoke_test(self, command: str, script: str) -> Generator[Result, None, None]:
        result = self.runner.invoke(self.module.cli, command)
        yield result
        code = compile(script, f"test_{self.T.cli.name}.py", "exec")
        exec(code, {}, {"result": result, "result_text": result.output.strip()})

    def is_valid_command(self, command: str) -> bool:
        command_name = command.split(" ")[0]
        cmd = Command(name=command_name, script="")
        command_func_name = self.parser.get_command_func_name(cmd)
        matching_command_func = [func for fname, func in self.module_funcs if fname == command_func_name]
        return bool(matching_command_func)
