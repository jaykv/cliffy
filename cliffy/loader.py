import contextlib
import os

from cliffy.commander import CLI
from cliffy.helper import CLIFFY_CLI_DIR, PYTHON_BIN, PYTHON_EXECUTABLE, exit_err, write_to_file


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
        if os.path.lexists(script_path) and not Loader.is_cli_script(script_path):
            # i.e. a manifest named `python` or `pip`: the script would replace that executable
            exit_err(
                f"~ cannot load {self.cli.name}: {script_path} already exists and was not created by cliffy. "
                "Rename the CLI in the manifest"
            )
        write_to_file(script_path, Loader.get_cli_script(self.cli.name), executable=True)
        return script_path

    @classmethod
    def load_from_cli(cls, cli: CLI) -> None:
        L = cls(cli)
        L.deploy_script()
        L.deploy_cli()

    @classmethod
    def unload_cli(cls, cli_name: str) -> None:
        script_path = cls.get_cli_script_path(cli_name)
        if cls.is_cli_script(script_path):
            with contextlib.suppress(FileNotFoundError):
                os.remove(script_path)
        with contextlib.suppress(FileNotFoundError):
            os.remove(cls.get_cli_path(cli_name))

    @staticmethod
    def is_cli_script(script_path: str) -> bool:
        """Whether the file is an entry script written by `deploy_script`"""
        try:
            with open(script_path, encoding="utf-8") as script:
                return "from cliffy.clis." in script.read(4096)
        except (OSError, UnicodeDecodeError):
            return False

    @staticmethod
    def get_cli_path(cli_name: str) -> str:
        return f"{CLIFFY_CLI_DIR}/{cli_name.replace('-', '_')}.py"

    @staticmethod
    def get_cli_script_path(cli_name: str) -> str:
        return f"{PYTHON_BIN}/{cli_name}"

    @staticmethod
    def get_cli_script(cli_name: str) -> str:
        return f"""#!{PYTHON_EXECUTABLE}
import sys
from cliffy.clis.{cli_name.replace("-", "_")} import cli

if __name__ == '__main__':
    sys.exit(cli())"""
