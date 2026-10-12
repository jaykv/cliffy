"""`cli validate` checks the code that is generated, not only the YAML."""

import pytest
from click.testing import CliRunner

from cliffy.cli import validate_command

HEADER = "name: checked\nversion: '1'\n"


def validate(tmp_path, body: str, header: str = HEADER):
    manifest_path = tmp_path / "checked.yaml"
    manifest_path.write_text(header + body)
    return CliRunner().invoke(validate_command, [str(manifest_path)])


@pytest.mark.parametrize("backend", ["", "use_click: true\n"], ids=["typer", "click"])
def test_validate_accepts_working_manifest(tmp_path, backend):
    result = validate(tmp_path, backend + "commands:\n  hello:\n    params: [name: str!]\n    run: print(name)\n")

    assert result.exit_code == 0, result.output
    assert "is valid" in result.output


@pytest.mark.parametrize(
    "backend, code",
    [
        ("", "x = = 1"),
        ("use_click: true\n", "x = = 1"),
        # pybash returns nothing for code it cannot tokenize, which leaves a function without a body.
        # (With Click the docstring is a body, so there the command silently does nothing.)
        ("", "print(("),
    ],
    ids=["typer", "click", "typer_unclosed_bracket"],
)
def test_validate_reports_syntax_error_against_the_command(tmp_path, backend, code):
    result = validate(tmp_path, backend + f"commands:\n  ok: print(1)\n  db.broken: '{code}'\n  after: print(2)\n")

    assert result.exit_code == 1
    assert "is invalid" in result.output
    assert "commands.db.broken: " in result.output
    assert "commands.after" not in result.output and "commands.ok" not in result.output
    assert "Error: " in result.output
    assert "Traceback" not in result.output


def test_validate_reports_params_that_do_not_compile(tmp_path):
    # the error the commented `cli init` template used to have
    params = "    params:\n      - 'loud: bool = False'\n      - 'name: str'\n"
    result = validate(tmp_path, "commands:\n  hello:\n" + params + "    run: print(name)\n")

    assert result.exit_code == 1
    assert "commands.hello" in result.output
    assert "default" in result.output


@pytest.mark.parametrize("backend", ["", "use_click: true\n"], ids=["typer", "click"])
def test_validate_reports_code_that_does_not_import(tmp_path, backend):
    result = validate(
        tmp_path,
        backend + "commands:\n  first: print(1)\n  count:\n    params:\n      - --n: NoSuchType\n    run: print(n)\n",
    )

    assert result.exit_code == 1
    assert "commands.count" in result.output
    assert "NoSuchType" in result.output
    assert "Traceback" not in result.output


def test_validate_reports_broken_imports_section(tmp_path):
    result = validate(tmp_path, "imports: import no_such_module_for_cliffy\ncommands:\n  a: print(1)\n")

    assert result.exit_code == 1
    assert "imports" in result.output
    assert "no_such_module_for_cliffy" in result.output


def test_validate_does_not_run_commands(tmp_path):
    marker = tmp_path / "ran"
    result = validate(tmp_path, f"commands:\n  touch: open({str(marker)!r}, 'w').close()\n")

    assert result.exit_code == 0, result.output
    assert not marker.exists()
