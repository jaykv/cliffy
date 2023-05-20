import contextlib
import os
import sys
import tempfile
from importlib import import_module

from .commander import CLI
from .helper import CLIFFY_CLI_DIR, PYTHON_BIN, PYTHON_EXECUTABLE, write_to_file


class Loader:
    def __init__(self, cli: CLI) -> None:
        self.cli = cli

    def deploy_cli(self) -> str:
        cli_path = Loader.get_cli_path(self.cli.name)
        write_to_file(cli_path, self.cli.code)
        return cli_path

    def deploy_script(self) -> str:
        script_path = Loader.get_cli_script_path(self.cli.name)
        write_to_file(script_path, Loader.get_cli_script(self.cli.name), executable=True)
        return script_path

    @classmethod
    def load_from(cls, cli: CLI) -> None:
        L = cls(cli)
        L.deploy_script()
        L.deploy_cli()

    @classmethod
    def unload_cli(cls, cli_name) -> None:
        with contextlib.suppress(FileNotFoundError):
            os.remove(cls.get_cli_script_path(cli_name))
            os.remove(cls.get_cli_path(cli_name))

    @staticmethod
    def run_cli(cli: CLI, args: tuple) -> None:
        with tempfile.NamedTemporaryFile(mode='w', prefix=f'{cli.name}_', suffix='.py', delete=True) as runner_file:
            runner_file.write(cli.code)
            runner_file.flush()
            module_path, module_filename = os.path.split(runner_file.name)
            sys.path.append(module_path)
            module = import_module(module_filename[:-3])

        runner_argvs = [runner_file.name] + list(args)
        sys.argv = runner_argvs
        module.cli()

    @staticmethod
    def get_cli_path(cli_name) -> str:
        return f"{CLIFFY_CLI_DIR}/{cli_name}.py"

    @staticmethod
    def get_cli_script_path(cli_name) -> str:
        return f"{PYTHON_BIN}/{cli_name}"

    @staticmethod
    def get_cli_script(cli_name) -> str:
        return f"""#!{PYTHON_EXECUTABLE}
import sys
from cliffy.clis.{cli_name} import cli

if __name__ == '__main__':
    sys.exit(cli())"""
