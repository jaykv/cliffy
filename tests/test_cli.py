from click.testing import CliRunner
from cliffy.cli import cli, render, init
from cliffy.homer import Homer

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0

def test_cli_init():
    runner = CliRunner()
    result = runner.invoke(init, ['hello', '--render'])
    assert result.exit_code == 0

def test_cli_render():
    runner = CliRunner()
    result = runner.invoke(render, ['examples/town.yaml'])
    assert result.exit_code == 0
    assert Homer.get_cli_metadata("town") is None