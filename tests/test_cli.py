from click.testing import CliRunner
from cliffy.cli import cli, load, render, init


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


def test_cli_load():
    runner = CliRunner()
    result = runner.invoke(load, ['examples/hello.yaml'])
    assert result.exit_code == 0


def test_cli_render():
    runner = CliRunner()
    result = runner.invoke(render, ['examples/town.yaml'])
    assert result.exit_code == 0


def test_cli_db():
    runner = CliRunner()
    result = runner.invoke(load, ['examples/db.yaml'])
    assert result.exit_code == 0
    
def test_cli_pydev():
    runner = CliRunner()
    result = runner.invoke(load, ['examples/pydev.yaml'])
    assert result.exit_code == 0


def test_cli_requires():
    runner = CliRunner()
    result = runner.invoke(load, ['examples/requires.yaml'])
    assert result.exit_code == 1
