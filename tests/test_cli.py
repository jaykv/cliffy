from click.testing import CliRunner
from cliffy.cli import cli, load, render


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0


def test_cli_load():
    runner = CliRunner()
    result = runner.invoke(load, ['examples/hello.yaml'])
    assert result.exit_code == 0


def test_cli_render():
    runner = CliRunner()
    result = runner.invoke(render, ['examples/town.yaml'])
    assert result.exit_code == 0
    
def test_cli_pydev():
    runner = CliRunner()
    result = runner.invoke(load, ['examples/pydev.yaml'])
    assert result.exit_code == 0