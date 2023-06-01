import contextlib
import os

from .commander import CLI
from .helper import CLIFFY_CLI_DIR, PYTHON_BIN, PYTHON_EXECUTABLE, write_to_file


class Loader:
    __slots__ = ("cli",)

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
    def load_from_cli(cls, cli: CLI) -> None:
        L = cls(cli)
        L.deploy_script()
        L.deploy_cli()

    @classmethod
    def unload_cli(cls, cli_name) -> None:
        with contextlib.suppress(FileNotFoundError):
            os.remove(cls.get_cli_script_path(cli_name))
            os.remove(cls.get_cli_path(cli_name))

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
