import glob
import json
import os
from base64 import b32encode
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .commander import CLI
from .helper import CLIFFY_METADATA_DIR, write_to_file
from .manifests.v1 import CLIMetadata


def save_metadata(manifest_path: str, cli: CLI) -> None:
    """Stores CLI metadata

    Args:
        manifest_path (str): CLI manifest path
        cli (CLI): CLI
    """
    abs_manifest_path = os.path.realpath(manifest_path)
    encoded_runnerpath = b32encode(cli.name.encode("ascii")).decode("utf-8")
    save_metadata_path = f"{CLIFFY_METADATA_DIR}/{encoded_runnerpath}/{cli.name}.json"
    with open(manifest_path, "r") as manifest:
        write_to_file(
            save_metadata_path,
            json.dumps(
                CLIMetadata(
                    cli_name=cli.name,
                    runner_path=abs_manifest_path,
                    version=cli.version,
                    loaded=datetime.now(),
                    manifest=manifest.read(),
                    requires=cli.requires,
                ).model_dump(),
                default=str,
            ),
        )


def remove_metadata(cli_name: str) -> None:
    """Clears CLI metadata by name

    Args:
        cli_name (str): CLI name
    """
    metadata_paths = glob.glob(f"{CLIFFY_METADATA_DIR}/*/{cli_name}.*")
    for path in metadata_paths:
        parent_path = Path(path).parent.resolve()
        os.remove(path)
        os.rmdir(parent_path)


def get_metadata_bypath(path: Path) -> CLIMetadata:
    """Fetches CLI metadata by metadata path

    Args:
        path (Path): Metadata path

    Returns:
        CLIMetadata: CLI metadata
    """
    try:
        return CLIMetadata(**json.load(path.open("r")))
    except Exception as e:
        return CLIMetadata(
            cli_name=path.name,
            runner_path=path.absolute().name,
            version="error",
            loaded=datetime.now(),
            manifest=f"could not load: {e}",
            requires=[],
        )


def get_metadata(cli_name: str) -> Optional[CLIMetadata]:
    """Fetches CLI metadata by name

    Args:
        cli_name (str): CLI name

    Returns:
        Optional[CLIMetadata]: CLI metadata
    """
    cli_path = get_metadata_path(cli_name)
    return get_metadata_bypath(Path(cli_path)) if cli_path else None


def get_metadata_path(cli_name: str) -> Optional[str]:
    """Fetches CLI metadata path

    Args:
        cli_name (str): CLI name

    Returns:
        Optional[str]: CLI metadata path
    """
    if cli_metadata_path := glob.glob(f"{CLIFFY_METADATA_DIR}/*/{cli_name}.json"):
        return cli_metadata_path[0]
    return None


def get_clis() -> Iterator[CLIMetadata]:
    """Fetches loaded CLIs metadata iteratively

    Yields:
        Iterator[CLIMetadata]: CLI metadata
    """
    metadata_paths = Path(str(CLIFFY_METADATA_DIR)).glob("*/*.json")
    for metadata_path in metadata_paths:
        yield get_metadata_bypath(metadata_path)
