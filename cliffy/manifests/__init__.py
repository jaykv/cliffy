from . import v1

Manifest = v1.CLIManifest
IncludeManifest = v1.IncludeManifest


def set_manifest_version(manifestVersion: str) -> None:
    global Manifest
    global IncludeManifest
    if manifestVersion == "v1":
        Manifest = v1.CLIManifest
        IncludeManifest = v1.IncludeManifest
