from click.testing import CliRunner
from commandeer.cli import cli, generate

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0

def test_cli_generate():
    runner = CliRunner()
    result = runner.invoke(generate, ['examples/hello.yaml'])
    assert result.exit_code == 0
