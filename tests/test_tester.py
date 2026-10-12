import glob
import re
import tempfile

import pytest
from click.testing import CliRunner
from pybash.transformer import transform as transform_bash

from cliffy.cli import test_command as manifest_test_command
from cliffy.helper import TEMP_FILES
from cliffy.tester import ShellScript
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


def test_progress_counter_only_counts_test_cases(tmp_path):
    # shell steps were numbered too, so two cases after a shell step were reported as "2 of 2" and "3 of 2"
    manifest_path = write_manifest(
        tmp_path,
        "  - $ echo setup\n  - hello: assert 'hi' in result.output\n  - $ echo between\n"
        "  - hello: assert 'hi' in result.output\n",
    )

    result = CliRunner().invoke(manifest_test_command, [manifest_path])

    assert result.exit_code == 0
    assert re.findall(r"\d+ of \d+", result.output) == ["1 of 2", "2 of 2"]


def test_progress_counter_numbers_failed_cases_too(tmp_path):
    manifest_path = write_manifest(
        tmp_path, "  - hello: assert 'bye' in result.output\n  - hello: assert 'hi' in result.output\n"
    )

    result = CliRunner().invoke(manifest_test_command, [manifest_path])

    assert result.exit_code == 1
    assert re.findall(r"\d+ of \d+", result.output) == ["2 of 2"]


def test_shell_step_error_describes_the_prefixes_correctly():
    # `$` is the direct subprocess call and `>` goes through a shell: the message had them the other way round
    with pytest.raises(ValueError) as error:
        ShellScript(command="echo hi")

    message = str(error.value)
    assert re.search(r"Use \$ to run the command directly", message)
    assert re.search(r"Use > to run it through a shell", message)
    assert "subprocess.run([" in transform_bash("$ echo hi")
    assert "shell=True" in transform_bash("> echo hi")


def test_assertions_see_output_without_ansi_styles(tmp_path):
    # rich styles help output on a CI runner (GITHUB_ACTIONS), which splits `--name` into styled pieces:
    # a manifest test that passed locally failed there
    manifest_path = tmp_path / "styled.yaml"
    manifest_path.write_text(
        "name: styled\nversion: '1'\ncommands:\n"
        "  show: print('\\x1b[1m--\\x1b[0m\\x1b[36mverbose\\x1b[0m')\n"
        "tests:\n"
        "  - show: |\n"
        "      assert result.output == '--verbose\\n'\n"
        "      assert result.stdout == '--verbose\\n'\n"
        "      assert result_text == '--verbose'\n"
    )

    result = CliRunner().invoke(manifest_test_command, [str(manifest_path)])

    assert "All tests passed" in result.output, result.output
    assert result.exit_code == 0
