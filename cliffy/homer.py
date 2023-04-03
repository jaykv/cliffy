import glob
import json
import os
from base64 import b32decode, b32encode
from datetime import datetime
from pathlib import Path
from typing import Generator

from .commander import CLI
from .helper import CLIFFY_HOME_PATH, write_to_file


class Homer:
    @staticmethod
    def save_cli_metadata(manifest_path: str, cli: CLI):
        abs_manifest_path = os.path.realpath(manifest_path)
        encoded_runnerpath = b32encode(abs_manifest_path.encode('ascii')).decode('utf-8')
        save_metadata_path = f"{CLIFFY_HOME_PATH}/{encoded_runnerpath}/{cli.name}"
        with open(manifest_path, "r") as manifest:
            write_to_file(
                save_metadata_path,
                json.dumps(
                    {"version": cli.version, "loaded": datetime.now(), "manifest": manifest.read()}, default=str
                ),
            )

    @staticmethod
    def remove_cli_metadata(cli_name: str) -> None:
        metadata_paths = glob.glob(f"{CLIFFY_HOME_PATH}/*/{cli_name}")
        for path in metadata_paths:
            parent_path = Path(path).parent.resolve()
            os.remove(path)
            os.rmdir(parent_path)

    @staticmethod
    def get_cli_metadata_paths() -> Generator[Path, None, None]:
        return Path(CLIFFY_HOME_PATH).glob('*/*')

    @staticmethod
    def get_cli_metadata(path: Path) -> tuple:
        decoded_runnerpath = b32decode(path.parent.name).decode('utf-8')
        return decoded_runnerpath, json.load(path.open("r"))

    @staticmethod
    def is_cliffy_cli(cli_name: str) -> bool:
        if not glob.glob(f"{CLIFFY_HOME_PATH}/*/{cli_name}"):
            return False
        return True
