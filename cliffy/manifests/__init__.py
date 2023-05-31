from . import v1

Manifest = v1.CLIManifest
IncludeManifest = v1.IncludeManifest
COMMAND_BLOCK = v1.COMMAND_BLOCK


def set_manifest_version(manifestVersion: str) -> None:
    global Manifest
    global IncludeManifest
    global COMMAND_BLOCK
    if manifestVersion == "v1":
        Manifest = v1.CLIManifest
        IncludeManifest = v1.IncludeManifest
        COMMAND_BLOCK = v1.COMMAND_BLOCK
