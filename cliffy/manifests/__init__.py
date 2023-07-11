from . import v1

Manifest = v1.CLIManifest
IncludeManifest = v1.IncludeManifest
CommandBlock = v1.CommandBlock


def set_manifest_version(manifestVersion: str) -> None:
    global Manifest
    global IncludeManifest
    global CommandBlock
    if manifestVersion == "v1":
        Manifest = v1.CLIManifest
        IncludeManifest = v1.IncludeManifest
        CommandBlock = v1.CommandBlock
