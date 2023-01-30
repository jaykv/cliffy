## Transformer

import os
import pathlib
import sys
from typing import TextIO

import yaml

from .commander import build_cli

PYTHON_BIN = f"{sys.exec_prefix}/bin"
PYTHON_EXECUTABLE = sys.executable
COMMANDEER_CLI_DIR = f"{pathlib.Path(__file__).parent.resolve()}/clis"


class Transformer:
    """Loads command manifest and transforms it into a CLI"""

    def __init__(self, manifest: TextIO) -> None:
        self.manifest = manifest
        self.command_config = self.load_manifest()

    def generate(self):
        self.cli = build_cli(self.command_config)
        self.deploy_script()
        self.deploy_cli()
        return self.cli

    def load_manifest(self) -> dict:
        try:
            return yaml.safe_load(self.manifest)
        except yaml.YAMLError as e:
            print("load_manifest", e)

    def deploy_cli(self) -> bool:
        cli_path = f"{COMMANDEER_CLI_DIR}/{self.command_config['name']}.py"
        write_to_file(cli_path, self.cli.code)

    def deploy_script(self) -> bool:
        script_path = f"{PYTHON_BIN}/{self.command_config['name']}"
        write_to_file(script_path, self.get_cli_script(), executable=True)

    def get_cli_script(self):
        return f"""#!{PYTHON_EXECUTABLE}
import sys
from commandeer.clis.{self.command_config['name']} import cli

if __name__ == '__main__':
    sys.exit(cli())"""


def write_to_file(path, text, executable=False):
    try:
        with open(path, "w") as s:
            s.write(text)
    except Exception as e:
        print("write_to_file", e)
        return False

    if executable:
        make_executable(path)

    return True


def make_executable(path):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)
