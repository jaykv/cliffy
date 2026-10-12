import glob
import os
import tempfile
from unittest.mock import patch

import pytest

from cliffy.builder import build_cli, build_cli_from_manifest, run_cli
from cliffy.helper import TEMP_FILES

TYPER_MANIFEST = "name: buildme\nversion: '1'\ncommands:\n  a: print(1)\n"
CLICK_MANIFEST = "name: buildme\nversion: '1'\nuse_click: true\ncommands:\n  a: print(1)\n"


@pytest.fixture
def temp_dir(monkeypatch, tmp_path):
    """Makes the tempfile module create its files in an empty directory"""
    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))
    return temp_dir


def test_run_cli_removes_temp_file_when_import_fails(temp_dir):
    with pytest.raises(ImportError):
        run_cli("broken", "import no_such_module_for_cliffy", ())

    assert glob.glob(f"{temp_dir}/broken_*") == []
    assert TEMP_FILES == []


def test_build_removes_temp_file_when_build_fails(temp_dir, tmp_path):
    manifest_path = tmp_path / "buildme.yaml"
    manifest_path.write_text(TYPER_MANIFEST)

    with (
        patch("cliffy.builder.build_cli", side_effect=RuntimeError("pip failed")),
        open(manifest_path) as manifest,
        pytest.raises(RuntimeError),
    ):
        build_cli_from_manifest(manifest)  # type: ignore[arg-type]

    assert glob.glob(f"{temp_dir}/buildme_*") == []
    assert TEMP_FILES == []


@pytest.mark.parametrize(
    "manifest, expected_requirements",
    [(TYPER_MANIFEST, ["typer"]), (CLICK_MANIFEST, ["rich-click"])],
    ids=["typer", "click"],
)
def test_build_installs_the_framework_the_cli_imports(tmp_path, manifest, expected_requirements):
    manifest_path = tmp_path / "buildme.yaml"
    manifest_path.write_text(manifest)
    output_dir = tmp_path / "out"

    # pip is not run: the zipapp is built from the script alone
    with patch("cliffy.builder.pip.install") as mock_pip_install, open(manifest_path) as manifest_io:
        cli, result = build_cli_from_manifest(manifest_io, output_dir=str(output_dir))  # type: ignore[arg-type]

    assert result.exit_code == 0, result.output
    assert os.path.exists(output_dir / cli.name)
    pip_args = mock_pip_install.call_args.args[0]
    assert pip_args[0] == "--target"
    assert pip_args[2:] == expected_requirements


def test_framework_requirements_and_deps_are_combined(tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text("import rich_click as click\n")

    with patch("cliffy.builder.pip.install") as mock_pip_install:
        build_cli("script", str(script_path), deps=["requests>=2,<3"], output_dir=str(tmp_path / "out"))

    assert mock_pip_install.call_args.args[0][2:] == ["rich-click", "requests>=2,<3"]


def test_build_creates_nested_output_dir(tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text("import typer\n")
    output_dir = tmp_path / "dist" / "bin"

    with patch("cliffy.builder.pip.install"):
        result = build_cli("script", str(script_path), output_dir=str(output_dir))

    assert result.exit_code == 0, result.output
    assert (output_dir / "script").exists()
