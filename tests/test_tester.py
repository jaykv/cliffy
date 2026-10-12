import glob
import tempfile

import pytest
from click.testing import CliRunner

from cliffy.cli import test_command as manifest_test_command
from cliffy.helper import TEMP_FILES
from cliffy.tester import Tester as ManifestTester

BROKEN_MANIFEST = "name: broken\nversion: '1'\nimports: import no_such_module_for_cliffy\ncommands:\n  a: print(1)\n"


def write_manifest(tmp_path, tests: str, use_click: bool = False) -> str:
    manifest_path = tmp_path / "tested.yaml"
    manifest_path.write_text(
        f"name: tested\nversion: '1'\nuse_click: {str(use_click).lower()}\n"
        "commands:\n  hello: print('hi')\n  boom: raise RuntimeError('boom')\n"
        f"tests:\n{tests}"
    )
    return str(manifest_path)


def test_tester_removes_temp_file_when_import_fails(monkeypatch, tmp_path):
    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))
    manifest_path = tmp_path / "broken.yaml"
    manifest_path.write_text(BROKEN_MANIFEST)

    with pytest.raises(ImportError):
        ManifestTester(str(manifest_path))

    assert glob.glob(f"{temp_dir}/broken_*") == []
    assert TEMP_FILES == []


def test_manifest_tests_run_for_click_cli(tmp_path):
    # typer's CliRunner cannot invoke a click group: every test of a use_click manifest errored
    manifest_path = write_manifest(tmp_path, "  - hello: assert 'hi' in result.output\n", use_click=True)

    result = CliRunner().invoke(manifest_test_command, [manifest_path])

    assert "All tests passed" in result.output
    assert result.exit_code == 0


def test_manifest_tests_all_pass_exit_code(tmp_path):
    manifest_path = write_manifest(tmp_path, "  - hello: assert 'hi' in result.output\n")

    result = CliRunner().invoke(manifest_test_command, [manifest_path])

    assert "All tests passed" in result.output
    assert result.exit_code == 0


def test_manifest_tests_some_failed_exit_code(tmp_path):
    manifest_path = write_manifest(
        tmp_path, "  - hello: assert 'hi' in result.output\n  - hello: assert 'bye' in result.output\n"
    )

    result = CliRunner().invoke(manifest_test_command, [manifest_path])

    assert "Some tests failed" in result.output
    assert result.exit_code == 1


def test_manifest_tests_exitfirst_exit_code(tmp_path):
    manifest_path = write_manifest(
        tmp_path, "  - hello: assert 'bye' in result.output\n  - hello: assert 'hi' in result.output\n"
    )

    result = CliRunner().invoke(manifest_test_command, [manifest_path, "-x"])

    assert "AssertionError" in result.output
    assert "1 of 2" not in result.output and "2 of 2" not in result.output
    assert result.exit_code == 1
