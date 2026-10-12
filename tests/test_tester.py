import glob
import re
import tempfile

import pytest
from click.testing import CliRunner
from pybash.transformer import transform as transform_bash

from cliffy.cli import test_command as manifest_test_command
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
    # the run has a temporary directory of its own: neither the file nor the directory is left behind
    assert list(temp_dir.iterdir()) == []


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


RAISING_MANIFEST = """\
name: raising
version: '1'
use_click: {use_click}
functions:
  - |
    def parse(text):
        import json
        return json.loads(text)
commands:
  boom:
    help: Raises on its second line
    pre_run: prepared = True
    run: |

      value = 1
      raise RuntimeError("the user's own problem")
  deep:
    run: |
      print("before")
      parse("{{")
  quit: raise SystemExit(3)
tests:
{tests}
"""


def run_manifest_tests(tmp_path, tests: str, *args: str, use_click: bool = False, manifest: str = RAISING_MANIFEST):
    manifest_path = tmp_path / "raising.yaml"
    manifest_path.write_text(manifest.format(use_click=str(use_click).lower(), tests=tests))
    return CliRunner().invoke(manifest_test_command, [str(manifest_path), *args])


def assert_no_traceback(output: str) -> None:
    """Nothing of cliffy itself and nothing of the generated module is shown: SOUL principle 3"""
    assert "Traceback" not in output, output
    assert 'File "' not in output, output
    for internal in ("tester.py", "cli.py", "helper.py", "_test.py", "site-packages", "<Result"):
        assert internal not in output, output


@pytest.mark.parametrize("use_click", [False, True], ids=["typer", "click"])
def test_command_that_raises_is_reported_in_manifest_terms(tmp_path, use_click):
    # it was shown as `<Result RuntimeError(...)>`: nothing said where in the manifest it came from
    result = run_manifest_tests(tmp_path, "  - boom: assert result.exit_code == 0\n", use_click=use_click)

    assert result.exit_code == 1
    assert "command `boom` raised RuntimeError: the user's own problem" in result.output
    # line 3 of the run block as it is written in the manifest: the blank first line counts
    assert 'run, line 3: raise RuntimeError("the user\'s own problem")' in result.output
    assert "AssertionError: (line 1) > assert result.exit_code == 0" in result.output
    assert_no_traceback(result.output)


@pytest.mark.parametrize("use_click", [False, True], ids=["typer", "click"])
def test_exception_from_a_helper_names_the_command_and_the_helper(tmp_path, use_click):
    result = run_manifest_tests(tmp_path, "  - deep: assert result.exit_code == 0\n", use_click=use_click)

    assert result.exit_code == 1
    assert "command `deep` raised JSONDecodeError: " in result.output
    assert 'run, line 2: parse("{")' in result.output
    assert "in `parse` (functions): return json.loads(text)" in result.output
    assert_no_traceback(result.output)


def test_expected_exception_can_still_be_asserted_on(tmp_path):
    tests = "  - boom: assert isinstance(result.exception, RuntimeError)\n  - quit: assert result.exit_code == 3\n"

    result = run_manifest_tests(tmp_path, tests)

    assert result.exit_code == 0, result.output
    assert "All tests passed" in result.output
    assert "command `boom` raised RuntimeError" in result.output
    # an exit code is not an exception of the command
    assert "command `quit` raised" not in result.output
    assert_no_traceback(result.output)


def test_traceback_flag_shows_the_traceback_of_the_command(tmp_path):
    result = run_manifest_tests(tmp_path, "  - boom: assert result.exit_code == 0\n", "--traceback")

    assert result.exit_code == 1
    assert "command `boom` raised RuntimeError: the user's own problem" in result.output
    assert "Traceback (most recent call last)" in result.output
    # with the lines of the generated code, although its file is gone
    assert 'raise RuntimeError("the user\'s own problem")' in result.output.split("Traceback")[1]


@pytest.mark.parametrize(
    "assertion, problem",
    [
        ("assert undefined_name", "NameError: name 'undefined_name' is not defined (line 1) > assert undefined_name"),
        ("assert result.output.nope()", "AttributeError: 'str' object has no attribute 'nope' (line 1) > assert"),
        ("assert (", "the assertion is not valid Python, line 1, column 8: '(' was never closed"),
    ],
    ids=["name_error", "attribute_error", "syntax_error"],
)
def test_broken_assertion_is_reported_without_a_traceback(tmp_path, assertion, problem):
    # these printed a traceback through cliffy/cli.py and cliffy/tester.py
    tests = f"  - quit: {assertion}\n  - quit: assert result.exit_code == 3\n"

    result = run_manifest_tests(tmp_path, tests)

    assert result.exit_code == 1
    assert problem in result.output
    assert "2 of 2" in result.output
    assert_no_traceback(result.output)


def test_assertion_error_on_a_later_line_is_located(tmp_path):
    tests = "  - quit: |\n      assert result.exit_code == 3\n      assert 'nothing' in result.output\n"

    result = run_manifest_tests(tmp_path, tests)

    assert result.exit_code == 1
    assert "AssertionError: (line 2) > assert 'nothing' in result.output" in result.output
    assert_no_traceback(result.output)


def test_manifest_that_does_not_import_is_reported_against_the_manifest(tmp_path):
    # `cli test` ended with a traceback through cliffy/helper.py that named a deleted temp file
    manifest_path = tmp_path / "broken.yaml"
    manifest_path.write_text(BROKEN_MANIFEST + "tests:\n  - a: assert result.exit_code == 0\n")

    result = CliRunner().invoke(manifest_test_command, [str(manifest_path)])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "module level code (`imports`, `vars`, `types` or `functions`)" in result.output
    assert "ModuleNotFoundError: No module named 'no_such_module_for_cliffy'" in result.output
    assert "import no_such_module_for_cliffy" in result.output
    assert_no_traceback(result.output)


def test_shell_step_that_cannot_start_ends_the_run_without_a_traceback(tmp_path):
    tests = "  - $ no-such-program-for-cliffy --flag\n  - quit: assert result.exit_code == 3\n"

    result = run_manifest_tests(tmp_path, tests)

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "test step `$ no-such-program-for-cliffy --flag` could not be run: FileNotFoundError" in result.output
    assert_no_traceback(result.output)
