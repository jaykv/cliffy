import os
import re
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cliffy.cli import (
    build_command,
    cli,
    docs_command,
    init_command,
    load_command,
    remove_command,
    render_command,
    run_command,
    update_command,
    validate_command,
)
from cliffy.cli import (
    test_command as manifest_test_command,
)
from cliffy.homer import get_metadata
from cliffy.loader import Loader
from cliffy.manifest import CLIMetadata

ANSI_RE = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")


def escape_ansi(line: str) -> str:
    return ANSI_RE.sub("", line)


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])  # type: ignore
    assert result.exit_code == 0
    assert "Usage: cli" in escape_ansi(result.output)


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])  # type: ignore
    assert result.exit_code == 0
    # with the rich extra installed this used to print the version of rich-click
    assert result.output.strip() == f"cli, version {metadata.version('cliffy')}"


def test_cli_init():
    runner = CliRunner()
    result = runner.invoke(init_command, ["hello", "--render"])
    assert result.exit_code == 0
    assert "name: hello" in escape_ansi(result.output)


def test_cli_render():
    runner = CliRunner()
    result = runner.invoke(render_command, ["examples/town.yaml"])
    assert result.exit_code == 0
    assert "cli = typer.Typer" in escape_ansi(result.output)


def test_cli_run():
    runner = CliRunner()
    result = runner.invoke(run_command, ["examples/hello.yaml", "--", "-h"])
    assert result.exit_code == 0
    assert "Hello world!" in escape_ansi(result.output)


def test_show_aliases():
    runner = CliRunner()
    result = runner.invoke(cli, ["--aliases"])
    assert result.exit_code == 0
    assert "Aliases:" in result.output
    assert "ls" in result.output
    assert "list" in result.output


def test_load_valid_manifest(isolated_fs):
    runner = CliRunner()
    manifest_content = """
    name: test-cli
    version: 1.0.0
    commands:
        hello:
            help: Say hello
            run: echo "Hello"
    """
    with open("test.yaml", "w") as f:
        f.write(manifest_content)
    with open("test.yaml", "rb") as f:
        result = runner.invoke(load_command, [f.name])
    assert "Generated test-cli CLI" in result.output


def test_update_nonexistent_cli():
    runner = CliRunner()
    result = runner.invoke(update_command, ["nonexistent-cli"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_init_command(isolated_fs):
    runner = CliRunner()
    result = runner.invoke(init_command, ["testcli", "--render"])
    assert result.exit_code == 0
    assert "name: testcli" in result.output


def test_remove_command():
    runner = CliRunner()
    result = runner.invoke(remove_command, ["nonexistent-cli"])
    assert result.exit_code == 1
    assert "not loaded" in result.output


def test_validate_invalid_manifest(isolated_fs):
    runner = CliRunner()
    invalid_manifest = "invalid: yaml: content"
    with open("invalid.yaml", "w") as f:
        f.write(invalid_manifest)
    with open("invalid.yaml", "rb") as f:
        result = runner.invoke(validate_command, [f.name])
    assert result.exit_code == 1
    assert "invalid" in result.output.lower()


def test_build_command(isolated_fs):
    runner = CliRunner()
    result = runner.invoke(build_command, ["nonexistent-cli"])
    assert result.exit_code == 1
    assert "not loaded" in result.output


def test_manifest_or_cli_converter(isolated_fs):
    runner = CliRunner()
    result = runner.invoke(build_command, ["test.yaml"])
    assert result.exit_code == 2


def test_init_with_json_schema(isolated_fs):
    runner = CliRunner()
    result = runner.invoke(init_command, ["testcli", "--json-schema"])
    assert result.exit_code == 0
    assert "cliffy_schema.json" in result.output
    assert "testcli.yaml" in os.listdir()
    assert "cliffy_schema.json" in os.listdir()


@patch("cliffy.cli.get_clis")
def test_list_command(mock_get_clis):
    mock_get_clis.return_value = [
        CLIMetadata(
            cli_name="test",
            runner_path="test.yaml",
            version="1.0.0",
            loaded=datetime.now(),
            manifest="",
            requires=["blabla"],
        )
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "test.yaml" in result.output
    assert "1.0.0" in result.output


@patch("cliffy.cli.get_metadata")
def test_info_command_success(mock_get_metadata):
    mock_metadata = CLIMetadata(
        cli_name="test-info",
        runner_path="test.yaml",
        version="2.0.0",
        loaded=datetime.now(),
        manifest="name: test-info\nversion: 2.0.0",
        requires=["dep1", "dep2"],
    )
    mock_get_metadata.return_value = mock_metadata

    runner = CliRunner()
    result = runner.invoke(cli, ["info", "test-info"])

    assert result.exit_code == 0
    assert "test-info" in result.output
    assert "2.0.0" in result.output
    assert "dep1" in result.output
    assert "dep2" in result.output
    assert mock_metadata.loaded.ctime() in result.output


@patch("cliffy.cli.get_metadata")
def test_info_command_not_loaded(mock_get_metadata):
    mock_get_metadata.return_value = None

    runner = CliRunner()
    result = runner.invoke(cli, ["info", "nonexistent-cli"])

    assert result.exit_code == 1
    assert "not loaded" in result.output


@patch("cliffy.cli.get_metadata")
def test_info_command_empty_requires(mock_get_metadata):
    mock_metadata = CLIMetadata(
        cli_name="test-info",
        runner_path="test.yaml",
        version="1.0.0",
        loaded=datetime.now(),
        manifest="name: test-info\nversion: 1.0.0",
        requires=[],
    )
    mock_get_metadata.return_value = mock_metadata

    runner = CliRunner()
    result = runner.invoke(cli, ["info", "test-info"])

    assert result.exit_code == 0
    assert "[]" in result.output


@patch("cliffy.cli.get_metadata")
def test_info_command_multiline_manifest(mock_get_metadata):
    manifest = """name: test-info
version: 1.0.0
commands:
    hello:
        help: Test command
        script: echo "Hello"
"""
    mock_metadata = CLIMetadata(
        cli_name="test-info",
        runner_path="test.yaml",
        version="1.0.0",
        loaded=datetime.now(),
        manifest=manifest,
        requires=["dep1"],
    )
    mock_get_metadata.return_value = mock_metadata

    runner = CliRunner()
    result = runner.invoke(cli, ["info", "test-info"])

    assert result.exit_code == 0
    assert "commands:" in result.output
    assert "hello:" in result.output
    assert "Test command" in result.output


@patch("cliffy.cli.Reloader")
def test_dev_command_basic(mock_reloader):
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "examples/hello.yaml"])
    assert result.exit_code == 0
    assert "Watching examples/hello.yaml for changes" in result.output
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", False, ())


@patch("cliffy.cli.Reloader")
def test_dev_command_with_run_cli(mock_reloader):
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "examples/hello.yaml", "--run-cli"])
    assert result.exit_code == 0
    assert "Watching examples/hello.yaml for changes" in result.output
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", True, ())


@patch("cliffy.cli.Reloader")
def test_dev_command_with_run_cli_and_args(mock_reloader):
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "examples/hello.yaml", "--run-cli", "--", "-h", "test"])
    assert result.exit_code == 0
    assert "Watching examples/hello.yaml for changes" in result.output
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", True, ("-h", "test"))


def test_dev_command_nonexistent_file():
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "nonexistent.yaml"])
    assert result.exit_code == 2
    assert "does not exist" in result.output.lower()


@patch("cliffy.cli.Reloader")
def test_dev_command_with_empty_args(mock_reloader):
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "examples/hello.yaml", "--run-cli", "--"])
    assert result.exit_code == 0
    assert "Watching examples/hello.yaml for changes" in result.output
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", True, ())


def test_dev_command_invalid_file_permissions(isolated_fs):
    runner = CliRunner()
    with open("test.yaml", "w") as f:
        f.write("test")
    os.chmod("test.yaml", 0o000)
    result = runner.invoke(cli, ["dev", "test.yaml"])
    assert result.exit_code == 2
    assert "usage" in result.output.lower()


def test_update_command(isolated_fs):
    runner = CliRunner()
    manifest_content = """
    name: test-cli-update
    version: 5.0.1
    commands:
        hello:
            help: Say hello
            run: echo "Hello"
    """

    manifest_content_update = """
    name: test-cli-update
    version: 5.0.2
    commands:
        world:
            help: Say world
            run: echo "World"
    """
    with open("test.yaml", "w") as f:
        f.write(manifest_content)

    result = runner.invoke(load_command, ["test.yaml"])
    assert result.exit_code == 0

    cli_metadata = get_metadata("test-cli-update")
    assert cli_metadata and cli_metadata.version == "5.0.1"

    with open("test.yaml", "w") as f:
        f.write(manifest_content_update)

    result = runner.invoke(update_command, ["test-cli-update"])
    assert result.exit_code == 0

    cli_metadata = get_metadata("test-cli-update")
    assert cli_metadata and cli_metadata.version == "5.0.2"


def test_validate_reports_generation_errors_with_exit_code(isolated_fs):
    # the manifest is well-formed, but no code can be generated for the command name
    with open("invalid.yaml", "w") as f:
        f.write("name: t\nversion: '1'\ncommands:\n  'a b': print(1)\n")

    result = CliRunner().invoke(validate_command, ["invalid.yaml"])

    assert "is invalid: commands.a b: Invalid command name: a b" in result.output
    assert result.exit_code == 1


def test_validate_valid_manifest(isolated_fs):
    with open("valid.yaml", "w") as f:
        f.write("name: t\nversion: '1'\ncommands:\n  a: print(1)\n")

    result = CliRunner().invoke(validate_command, ["valid.yaml"])

    assert "is valid" in result.output
    assert result.exit_code == 0


def test_init_invalid_name(isolated_fs):
    # `--raw` wrote a manifest that `cli load` could never accept
    result = CliRunner().invoke(init_command, ["my cli", "--raw"])

    assert result.exit_code == 1
    assert "invalid CLI name" in result.output
    assert os.listdir(".") == []


def test_init_template_name_error_is_not_a_traceback(isolated_fs):
    result = CliRunner().invoke(init_command, ["my-cli"])

    assert result.exit_code == 1
    assert "CLI name must be a valid Python identifier" in result.output
    assert isinstance(result.exception, SystemExit)
    assert os.listdir(".") == []


def test_init_template_is_a_loadable_name(isolated_fs):
    # every name `init` accepts has to be accepted by `load` too
    result = CliRunner().invoke(init_command, ["my-cli", "--raw"])

    assert result.exit_code == 0
    assert "name: my-cli" in Path("my-cli.yaml").read_text()


def test_docs_for_loaded_cli(isolated_fs):
    runner = CliRunner()
    with open("docs-cli.yaml", "w") as f:
        f.write(
            "name: test-cli-docs\nversion: 1.2.3\nhelp: Documented\n"
            "vars:\n  greeting: hello\ncommands:\n  greet:\n    help: Says {{ greeting }}\n    run: print(1)\n"
        )
    assert runner.invoke(load_command, ["docs-cli.yaml"]).exit_code == 0

    try:
        result = runner.invoke(docs_command, ["test-cli-docs"])
    finally:
        runner.invoke(remove_command, ["test-cli-docs"])

    assert result.exit_code == 0, result.output
    assert "+ test-cli-docs.md" in result.output
    content = Path("test-cli-docs.md").read_text()
    assert "# test-cli-docs v1.2.3" in content
    assert "Says hello" in content


def test_docs_for_unknown_cli(isolated_fs):
    result = CliRunner().invoke(docs_command, ["nonexistent-cli"])

    assert result.exit_code == 1
    assert "not loaded" in result.output


def test_build_loaded_cli_with_dashed_name(isolated_fs):
    runner = CliRunner()
    with open("dashed.yaml", "w") as f:
        f.write("name: test-cli-dashed\nversion: '1'\ncommands:\n  a: print(1)\n")
    assert runner.invoke(load_command, ["dashed.yaml"]).exit_code == 0

    try:
        # the module of a loaded CLI is stored as test_cli_dashed.py: the build looked for test-cli-dashed.py
        with patch("cliffy.cli.build_cli") as mock_build_cli:
            mock_build_cli.return_value.exit_code = 0
            result = runner.invoke(build_command, ["test-cli-dashed"])
        script_path = mock_build_cli.call_args.kwargs["script_path"]
        assert script_path == Loader.get_cli_path("test-cli-dashed")
        assert os.path.isfile(script_path)
    finally:
        runner.invoke(remove_command, ["test-cli-dashed"])

    assert result.exit_code == 0, result.output


def test_build_failure_exit_code(isolated_fs):
    with open("fails.yaml", "w") as f:
        f.write("name: fails\nversion: '1'\ncommands:\n  a: print(1)\n")

    built_cli = MagicMock()
    built_cli.name = "fails"
    build_result = MagicMock(exit_code=1, output="pip said no", exception=None)
    with patch("cliffy.cli.build_cli_from_manifest", return_value=(built_cli, build_result)):
        result = CliRunner().invoke(build_command, ["fails.yaml"])

    assert "fails build failed" in result.output
    assert result.exit_code == 1


@pytest.mark.parametrize("flags", [[], ["--raw"]], ids=["commented", "raw"])
def test_init_template_loads_runs_and_passes_its_own_tests(isolated_fs, flags):
    # the commented template used to fail with "parameter without a default follows parameter with a
    # default", and the raw template had nothing to run or test
    runner = CliRunner()
    assert runner.invoke(init_command, ["mycli", *flags]).exit_code == 0

    validated = runner.invoke(validate_command, ["mycli.yaml"])
    assert validated.exit_code == 0, validated.output

    ran = subprocess.run(
        [sys.executable, "-m", "cliffy", "run", "mycli.yaml", "--", "hello"], capture_output=True, text=True
    )
    assert ran.returncode == 0, ran.stderr
    assert "Hello" in ran.stdout

    tested = runner.invoke(manifest_test_command, ["mycli.yaml"])
    assert "All tests passed" in tested.output
    assert tested.exit_code == 0
