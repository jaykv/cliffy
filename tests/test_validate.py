"""`cli validate` checks the code that is generated, not only the YAML."""

import pytest
from click.testing import CliRunner

from cliffy.cli import render_command, validate_command

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


@pytest.mark.parametrize("backend", ["", "use_click: true\n"], ids=["typer", "click"])
@pytest.mark.parametrize(
    "code, column, problem",
    [("x = = 1", 5, "invalid syntax"), ("print((", 7, "was never closed"), ("$ echo 'a", 9, "unterminated ' quote")],
    ids=["invalid_statement", "unclosed_bracket", "shell_unclosed_quote"],
)
def test_validate_reports_script_errors_like_every_other_command(tmp_path, backend, code, column, problem):
    # one message for an error in a run block, whichever command finds it: file, command, block, line, column
    body = backend + f'commands:\n  ok: print(1)\n  db.broken: "{code}"\n  after: print(2)\n'
    result = validate(tmp_path, body)
    rendered = CliRunner().invoke(render_command, [str(tmp_path / "checked.yaml")])

    assert result.exit_code == 1
    assert f"checked.yaml: command `db.broken`, run, line 1, column {column}: " in result.output
    assert problem in result.output
    assert code in result.output
    assert "Traceback" not in result.output
    # said once, and not a second time in the terms of the generated code
    assert result.output.count("db.broken") == 1
    assert "generated code" not in result.output
    assert rendered.exit_code == 1
    assert rendered.output == result.output


def test_validate_reports_params_that_do_not_compile(tmp_path):
    # the error the commented `cli init` template used to have
    params = "    params:\n      - 'loud: bool = False'\n      - 'name: str'\n"
    result = validate(tmp_path, "commands:\n  hello:\n" + params + "    run: print(name)\n")

    assert result.exit_code == 1
    assert "command `hello`: SyntaxError" in result.output
    assert "default" in result.output


@pytest.mark.parametrize("backend", ["", "use_click: true\n"], ids=["typer", "click"])
def test_validate_reports_code_that_does_not_import(tmp_path, backend):
    result = validate(
        tmp_path,
        backend + "commands:\n  first: print(1)\n  count:\n    params:\n      - --n: NoSuchType\n    run: print(n)\n",
    )

    assert result.exit_code == 1
    assert "command `count`: NameError" in result.output
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


def test_validate_warns_when_a_full_typer_type_swallows_param_settings(tmp_path):
    body = (
        "types:\n  Verbose: bool = typer.Option(False, '--verbose')\n"
        "commands:\n  hello:\n    params:\n      - name: --verbose\n        type: Verbose\n        help: Be loud\n"
        "    run: print(1)\n"
    )
    result = validate(tmp_path, body)

    assert result.exit_code == 0, result.output
    assert "command `hello`, param `--verbose`: `types.Verbose` is a complete Typer definition" in result.output
    assert "`help` is ignored" in result.output
    assert "is valid" in result.output
