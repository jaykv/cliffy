import re

from click.testing import CliRunner
from cliffy.cli import cli, render, init, run_cli
from cliffy.homer import get_metadata

ANSI_RE = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')

def escape_ansi(line: str) -> str:
    return ANSI_RE.sub('', line)


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])  # type: ignore
    assert result.exit_code == 0
    assert 'Usage: cli' in escape_ansi(result.output)


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])  # type: ignore
    assert result.exit_code == 0


def test_cli_init():
    runner = CliRunner()
    result = runner.invoke(init, ['hello', '--render'])
    assert result.exit_code == 0
    assert 'name: hello' in escape_ansi(result.output)


def test_cli_render():
    runner = CliRunner()
    result = runner.invoke(render, ['examples/town.yaml'])
    assert result.exit_code == 0
    assert 'cli = typer.Typer' in escape_ansi(result.output)
    assert get_metadata("town") is None


def test_cli_run():
    runner = CliRunner()
    result = runner.invoke(run_cli, ['examples/hello.yaml', '--', '-h'])
    assert result.exit_code == 0
    assert 'Usage: hello_' in escape_ansi(result.output)
    assert get_metadata('hello') is None
