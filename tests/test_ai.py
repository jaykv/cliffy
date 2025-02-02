import pytest
from click.testing import CliRunner
from cliffy.ai import ai


@pytest.fixture
def runner():
    return CliRunner()


def test_generate_command(runner, tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("data")
    result = runner.invoke(ai, ["generate", "test_cli", "This is a test CLI description.", "-m", "test", "-o", tmp_dir])
    assert result.exit_code == 0
    assert "test_cli.yaml" in result.output


def test_ask_command(runner):
    result = runner.invoke(ai, ["ask", "What is cliffy?", "-m", "test"])
    assert result.exit_code == 0
    assert "token usage:" in result.output
