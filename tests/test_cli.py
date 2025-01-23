from datetime import datetime
import re

from click.testing import CliRunner

from cliffy.cli import (
    cli,
    init_command,
    run_command,
    render_command,
    remove_command,
    build_command,
    validate_command,
    load_command,
    update_command,
)
import os
from unittest.mock import patch

from cliffy.homer import get_metadata
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


def test_load_valid_manifest():
    runner = CliRunner()
    manifest_content = """
    name: test-cli
    version: 1.0.0
    commands:
        hello:
            help: Say hello
            run: echo "Hello"
    """
    with runner.isolated_filesystem():
        with open("test.yaml", "w") as f:
            f.write(manifest_content)
        with open("test.yaml", "rb") as f:
            result = runner.invoke(load_command, [f.name])
        assert "Generated test-cli CLI" in result.output


def test_update_nonexistent_cli():
    runner = CliRunner()
    result = runner.invoke(update_command, ["nonexistent-cli"])
    assert result.exit_code == 0
    assert "not found" in result.output


def test_init_command():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(init_command, ["testcli", "--render"])
        assert result.exit_code == 0
        assert "name: testcli" in result.output


def test_remove_command():
    runner = CliRunner()
    result = runner.invoke(remove_command, ["nonexistent-cli"])
    assert result.exit_code == 0
    assert "not loaded" in result.output


def test_validate_invalid_manifest():
    runner = CliRunner()
    invalid_manifest = "invalid: yaml: content"
    with runner.isolated_filesystem():
        with open("invalid.yaml", "w") as f:
            f.write(invalid_manifest)
        with open("invalid.yaml", "rb") as f:
            result = runner.invoke(validate_command, [f.name])
        assert result.exit_code == 1
        assert "invalid" in result.output.lower()


def test_build_command():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(build_command, ["nonexistent-cli"])
        assert result.exit_code == 0
        assert "not loaded" in result.output


def test_manifest_or_cli_converter():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(build_command, ["test.yaml"])
        assert result.exit_code == 2


def test_init_with_json_schema():
    runner = CliRunner()
    with runner.isolated_filesystem():
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
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", None, ())


@patch("cliffy.cli.Reloader")
def test_dev_command_with_run_cli(mock_reloader):
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "examples/hello.yaml", "--run-cli"])
    assert result.exit_code == 0
    assert "Watching examples/hello.yaml for changes" in result.output
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", "True", ())


@patch("cliffy.cli.Reloader")
def test_dev_command_with_run_cli_and_args(mock_reloader):
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "examples/hello.yaml", "--run-cli", "--", "-h", "test"])
    assert result.exit_code == 0
    assert "Watching examples/hello.yaml for changes" in result.output
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", "True", ("-h", "test"))


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
    mock_reloader.watch.assert_called_once_with("examples/hello.yaml", "True", ())


def test_dev_command_invalid_file_permissions():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("test.yaml", "w") as f:
            f.write("test")
        os.chmod("test.yaml", 0o000)
        result = runner.invoke(cli, ["dev", "test.yaml"])
        assert result.exit_code == 2
        assert "usage" in result.output.lower()


def test_update_command():
    runner = CliRunner()
    manifest_content = """
    name: test-cli
    version: 5.0.1
    commands:
        hello:
            help: Say hello
            run: echo "Hello"
    """

    manifest_content_update = """
    name: test-cli
    version: 5.0.2
    commands:
        world:
            help: Say world
            run: echo "World"
    """
    with runner.isolated_filesystem():
        with open("test.yaml", "w") as f:
            f.write(manifest_content)

        result = runner.invoke(load_command, ["test.yaml"])
        assert result.exit_code == 0

        cli_metadata = get_metadata("test-cli")
        assert cli_metadata and cli_metadata.version == "5.0.1"

        with open("test.yaml", "w") as f:
            f.write(manifest_content_update)

        result = runner.invoke(update_command, ["test-cli"])
        assert result.exit_code == 0

        cli_metadata = get_metadata("test-cli")
        assert cli_metadata and cli_metadata.version == "5.0.2"
