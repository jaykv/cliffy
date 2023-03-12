from . import v1

__all__ = ['Manifest', 'v1', 'get_cli_manifest']

Manifest = v1.CLIManifest


def get_cli_manifest(manifestVersion: str):
    if manifestVersion == "v1":
        Manifest = v1.CLIManifest

    return Manifest
