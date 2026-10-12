import contextlib
import os
import stat
from typing import Literal

from cliffy.commander import CLI
from cliffy.helper import (
    CLIFFY_CLI_DIR,
    PYTHON_BIN,
    PYTHON_EXECUTABLE,
    exit_err,
    validate_cli_name,
    write_atomically,
)

ScriptState = Literal["missing", "owned", "foreign"]
NOT_OURS = "already exists and was not created by cliffy, or was changed since"


class LoaderError(Exception):
    """A loaded CLI could not be removed. The message says what is in the way; nothing was removed."""


class Loader:
    __slots__ = ("cli",)

    def __init__(self, cli: CLI) -> None:
        self.cli = cli

    def deploy_cli(self) -> str:
        cli_path = Loader.get_cli_path(self.cli.name)
        write_atomically(cli_path, self.cli.code)
        return cli_path

    def deploy_script(self) -> str:
        """Write the launcher into the directory of the interpreter's executables.

        A file that is already there is only replaced when it is the launcher cliffy wrote for this
        CLI. Anything else stops the load: a manifest named `python` or `pip` would replace that executable.
        """
        script_path = Loader.get_cli_script_path(self.cli.name)
        refused = f"~ cannot load {self.cli.name}: {script_path} {NOT_OURS}. Rename the CLI in the manifest"
        state = Loader.script_state(script_path, self.cli.name)
        if state == "foreign":
            exit_err(refused)

        try:
            # A new launcher is created exclusively: a file that appeared since the check is kept.
            # An own launcher is replaced by a rename, which never writes through a link.
            write_atomically(
                script_path, Loader.get_cli_script(self.cli.name), executable=True, replace=state == "owned"
            )
        except FileExistsError:
            exit_err(refused)
        return script_path

    @classmethod
    def load_from_cli(cls, cli: CLI) -> None:
        L = cls(cli)
        L.deploy_script()
        L.deploy_cli()

    @classmethod
    def unload_cli(cls, cli_name: str) -> None:
        """Remove the launcher and the module of a loaded CLI: both, or neither.

        Raises:
            ValueError: `cli_name` is not a CLI name.
            LoaderError: the launcher is not the one cliffy wrote (edited, replaced, a link, unreadable),
                or a file could not be deleted. The CLI is left as it was and still runs.
        """
        script_path = cls.get_cli_script_path(cli_name)
        module_path = cls.get_cli_path(cli_name)

        # checked right before the file is deleted
        state = cls.script_state(script_path, cli_name)
        if state == "foreign":
            raise LoaderError(
                f"{script_path} was not created by cliffy, or was changed since. Nothing was removed and "
                f"{cli_name} is still loaded. Move or delete that file, then remove {cli_name} again"
            )
        try:
            if state == "owned":
                os.unlink(script_path)
        except FileNotFoundError:
            state = "missing"
        except OSError as e:
            raise LoaderError(f"could not delete {script_path}: {e}. Nothing was removed") from e

        try:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(module_path)
        except OSError as e:
            if state == "owned":
                # put back, so that the CLI is not left with a module and nothing to start it
                with contextlib.suppress(OSError):
                    write_atomically(script_path, cls.get_cli_script(cli_name), executable=True, replace=False)
            raise LoaderError(f"could not delete {module_path}: {e}. {cli_name} is still loaded") from e

    @staticmethod
    def script_state(script_path: str, cli_name: str) -> ScriptState:
        """Whether the launcher of a CLI is missing, is the file `deploy_script` writes for it, or is anything else.

        "owned" is a regular file, not a link to one, whose text is the launcher of exactly this CLI.
        Only its `#!` line may differ: one environment can be reached through several interpreter paths.
        """
        try:
            if not stat.S_ISREG(os.lstat(script_path).st_mode):
                return "foreign"
            # O_NOFOLLOW: a link put there after the lstat fails to open instead of being followed
            descriptor = os.open(script_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        except FileNotFoundError:
            return "missing"
        except OSError:
            return "foreign"

        expected = Loader.get_cli_script(cli_name)
        try:
            with os.fdopen(descriptor, "rb") as script:
                if not stat.S_ISREG(os.fstat(script.fileno()).st_mode):
                    return "foreign"
                # more than a launcher holds is not a launcher: the rest does not need to be read
                content = script.read(len(expected.encode("utf-8")) + 4096).decode("utf-8")
        except (OSError, UnicodeDecodeError):
            return "foreign"

        interpreter_line, _, body = content.replace("\r\n", "\n").partition("\n")
        owned = interpreter_line.startswith("#!") and body == expected.partition("\n")[2]
        return "owned" if owned else "foreign"

    @staticmethod
    def is_cli_script(script_path: str, cli_name: str) -> bool:
        """Whether the file is the launcher written by `deploy_script` for this CLI"""
        return Loader.script_state(script_path, cli_name) == "owned"

    @staticmethod
    def get_cli_path(cli_name: str) -> str:
        return f"{CLIFFY_CLI_DIR}/{validate_cli_name(cli_name).replace('-', '_')}.py"

    @staticmethod
    def get_cli_script_path(cli_name: str) -> str:
        return f"{PYTHON_BIN}/{validate_cli_name(cli_name)}"

    @staticmethod
    def get_cli_script(cli_name: str) -> str:
        return f"""#!{PYTHON_EXECUTABLE}
import sys
from cliffy.clis.{cli_name.replace("-", "_")} import cli

if __name__ == '__main__':
    sys.exit(cli())"""
