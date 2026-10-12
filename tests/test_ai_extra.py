"""What cliffy does when the optional ``ai`` extra (pydantic-ai) is not installed.

These tests do not need pydantic-ai, so unlike tests/test_ai.py they also run in an install without extras.
"""

import subprocess
import sys

import pytest
from click.testing import CliRunner

from cliffy.ai import ai
from cliffy.cli import cli

WITHOUT_PYDANTIC_AI = "import sys\nsys.modules['pydantic_ai'] = None\n"


def test_cliffy_imports_without_pydantic_ai():
    code = WITHOUT_PYDANTIC_AI + "import cliffy, cliffy.ai, cliffy.cli, cliffy.run\n"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_ai_commands_are_listed_without_the_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "pydantic_ai", None)  # makes `import pydantic_ai` fail
    result = CliRunner().invoke(cli, ["ai", "--help"])
    assert result.exit_code == 0
    assert "generate" in result.output and "ask" in result.output


@pytest.mark.parametrize("args", [["ask", "What is cliffy?"], ["generate", "greeter", "Greets people"]])
def test_ai_commands_explain_how_to_install_the_extra(monkeypatch, isolated_fs, args):
    monkeypatch.setitem(sys.modules, "pydantic_ai", None)
    result = CliRunner().invoke(ai, args)

    assert result.exit_code == 1
    assert "cliffy[ai]" in result.output
    assert isinstance(result.exception, SystemExit)
    assert not (isolated_fs / "greeter.yaml").exists()


def test_llms_txt_is_printed_without_the_extra(monkeypatch):
    # the bundled documentation needs no model, so it must work in an install without the `ai` extra
    monkeypatch.setitem(sys.modules, "pydantic_ai", None)
    result = CliRunner().invoke(ai, ["llms-txt"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("# cliffy\n")
    assert "use_click" in result.output
    assert "--8<--" not in result.output  # snippet includes are resolved
