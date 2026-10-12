"""Shell lines in scripts: what pybash generates for them, and how its errors are reported."""

import pytest
from click.testing import CliRunner
from typer.testing import CliRunner as TyperCliRunner

from cliffy.cli import cli as cliffy_cli
from cliffy.commander import generate_cli
from cliffy.commanders.click import ClickCommander
from cliffy.commanders.typer import TyperCommander
from cliffy.manifest import CLIManifest, RunBlock

SHELL_RUNTIME_IMPORT = "import pybash.runtime as _pybash\n"


def shell_manifest(run: str, **fields: object) -> CLIManifest:
    return CLIManifest(name="sh", version="1", help="", commands={"go": RunBlock(run)}, **fields)  # type: ignore[arg-type]


@pytest.mark.parametrize("commander_cls", [TyperCommander, ClickCommander], ids=["typer", "click"])
def test_plain_shell_lines_only_need_subprocess(commander_cls):
    code = generate_cli(shell_manifest("$ ls -la\nout = $ echo hi\n> ls *.txt"), commander_cls).code

    assert 'subprocess.run(["ls", "-la"])' in code
    assert 'out = subprocess.check_output(["echo", "hi"])' in code
    assert 'subprocess.run("ls *.txt", shell=True)' in code
    assert "pybash" not in code


@pytest.mark.parametrize("commander_cls", [TyperCommander, ClickCommander], ids=["typer", "click"])
@pytest.mark.parametrize(
    ("run", "expected"),
    [
        ("$ ls | wc -l", '_pybash.run([["ls"], "|", ["wc", "-l"]])'),
        ("$ make && echo ok || echo failed", '"&&", ["echo", "ok"], "||", ["echo", "failed"]'),
        ("$ ls nope 2> err.txt", '_pybash.run([["ls", "nope"], "2>", "err.txt"])'),
        ("x = 'a b'\n> echo f{x}", '_pybash.quote(f"""{x}""")'),
    ],
    ids=["pipe", "chain", "redirect", "shell-value"],
)
def test_shell_operators_import_the_runtime_once(commander_cls, run, expected):
    code = generate_cli(shell_manifest(run), commander_cls).code

    assert expected in code
    assert code.count(SHELL_RUNTIME_IMPORT) == 1
    # with the other imports, before any code of the CLI
    assert code.index(SHELL_RUNTIME_IMPORT) < code.index("CONTEXT_SETTINGS")
    # the default of pybash, an import in place on every line, is not used
    assert "__import__" not in code
    compile(code, "sh.py", "exec")


def test_runtime_is_imported_for_functions_and_callbacks():
    in_function = shell_manifest("print(1)", functions=["def count():\n    return $ ls | wc -l"])
    assert SHELL_RUNTIME_IMPORT in generate_cli(in_function, TyperCommander).code

    in_callback = shell_manifest("print(1)", callbacks=[{"run": "$ true && echo ready"}])
    assert SHELL_RUNTIME_IMPORT in generate_cli(in_callback, TyperCommander).code


def test_generated_shell_operators_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest = shell_manifest(
        "out = $ printf 'b\\na\\n' | sort > sorted.txt && cat sorted.txt  # a comment\nprint(out.decode().split())"
    )
    namespace: dict = {"__name__": "sh"}
    exec(generate_cli(manifest, TyperCommander).code, namespace)

    result = TyperCliRunner().invoke(namespace["cli"], ["go"])

    assert result.exit_code == 0, result.output
    assert result.output == "['a', 'b']\n"
    assert (tmp_path / "sorted.txt").read_text() == "a\nb\n"


def test_a_command_cannot_replace_the_shell_runtime():
    code = generate_cli(
        CLIManifest(name="sh", version="1", help="", commands={"_pybash": RunBlock("$ ls | wc")}), TyperCommander
    ).code

    assert "def _pybash_(" in code
    assert "def _pybash(" not in code


SCRIPT_ERRORS = [
    pytest.param(
        "commands:\n  deploy:\n    run: |\n      print(1)\n      if True:\n          $ sleep 5 &\n",
        [
            "command `deploy`, run, line 3, column 11: running in the background with & is not supported",
            "\n    $ sleep 5 &\n              ^",
        ],
        id="shell-line",
    ),
    pytest.param(
        'commands:\n  deploy:\n    pre_run: $ echo "never closed\n    run: print(1)\n',
        ['command `deploy`, pre_run, line 1, column 20: unterminated " quote', '\n    $ echo "never closed\n'],
        id="pre-run",
    ),
    pytest.param(
        "commands:\n  db.migrate|m:\n    run: |\n      x = ($ ls\n",
        ["command `db.migrate`, run, line 1, column 6: Missing end parentheses", "\n    x = ($ ls\n         ^"],
        id="capture-in-group-command",
    ),
    pytest.param(
        "commands:\n  ok: print(1)\ncallbacks:\n  - run: $ ls |\n",
        ["callback of the CLI, run, line 1, column 6: missing command after '|'", "\n    $ ls |\n         ^"],
        id="callback",
    ),
    pytest.param(
        "commands:\n  db.ok: print(1)\ncallbacks:\n  - group: db\n    run: $ ls > \n",
        ["callback of group `db`, run, line 1, column 6: missing file name after '>'"],
        id="group-callback",
    ),
    pytest.param(
        "functions:\n  - |\n    def helper():\n        $ cat << EOF\ncommands:\n  ok: print(1)\n",
        ["functions, entry 1, line 2, column 7: a here-document (<<) is not supported", "\n    $ cat << EOF\n"],
        id="function",
    ),
    pytest.param(
        "commands:\n  deploy:\n    run: |\n      print('one')\n      total = (1 +\n",
        ["command `deploy`, run, line 2, column 9: not valid Python: '(' was never closed", "\n    total = (1 +\n"],
        id="python",
    ),
]


@pytest.mark.parametrize("use_click", [False, True], ids=["typer", "click"])
@pytest.mark.parametrize(("body", "expected"), SCRIPT_ERRORS)
def test_script_errors_point_at_the_manifest(tmp_path, body, expected, use_click):
    manifest = tmp_path / "broken.yaml"
    manifest.write_text(f"name: broken\nversion: '1'\nuse_click: {str(use_click).lower()}\n{body}")

    for command in ("load", "render", "run", "validate", "build", "test"):
        result = CliRunner().invoke(cliffy_cli, [command, str(manifest)])

        assert result.exit_code == 1, command
        assert result.exception is None or isinstance(result.exception, SystemExit), command
        assert f"~ error in {manifest}: " in result.output, command
        for text in expected:
            assert text in result.output, command
        assert "Traceback" not in result.output


def test_script_error_in_a_test_step_is_reported_without_a_traceback(tmp_path):
    manifest = tmp_path / "steps.yaml"
    manifest.write_text(
        "name: steps\nversion: '1'\ncommands:\n  ok: print(1)\ntests:\n  - $ ls |\n  - ok: assert True\n"
    )

    result = CliRunner().invoke(cliffy_cli, ["test", str(manifest)])

    assert result.exit_code == 1
    assert f"~ error in {manifest}: test step `$ ls |`, column 6: missing command after '|'" in result.output
    assert "Traceback" not in result.output


def test_shell_test_steps_support_operators(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest = tmp_path / "steps.yaml"
    manifest.write_text(
        "name: steps\nversion: '1'\ncommands:\n  ok: print(open('made.txt').read())\n"
        "tests:\n  - $ echo made | tr a-z A-Z > made.txt\n  - ok: assert result.output == 'MADE\\n\\n'\n"
    )

    result = CliRunner().invoke(cliffy_cli, ["test", str(manifest)])

    assert result.exit_code == 0, result.output
    assert "All tests passed" in result.output
