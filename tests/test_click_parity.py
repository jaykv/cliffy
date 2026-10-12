"""The Click backend accepts what the manifest reference documents, with the meaning it has for Typer."""

import subprocess
import sys
import textwrap

import pytest
from click.testing import CliRunner as ClickCliRunner
from typer.testing import CliRunner as TyperCliRunner

from cliffy.helper import import_module_from_path
from cliffy.transformer import Transformer

BACKENDS = pytest.mark.parametrize("use_click", [False, True], ids=["typer", "click"])


@pytest.fixture
def run(tmp_path):
    """Generates a CLI from a manifest body for one backend, imports it and invokes it with args"""
    counter = iter(range(1000))

    def _run(body: str, args: list[str], use_click: bool = True):
        number = next(counter)
        manifest_path = tmp_path / f"manifest{number}.yaml"
        header = f"name: t\nversion: '1'\nuse_click: {str(use_click).lower()}\n"
        manifest_path.write_text(header + textwrap.dedent(body), encoding="utf-8")
        with open(manifest_path, encoding="utf-8") as manifest_io:
            T = Transformer(manifest_io, validate_requires=False)
        module_path = tmp_path / f"generated{number}.py"
        module_path.write_text(T.cli.code, encoding="utf-8")
        module = import_module_from_path(str(module_path))
        runner = ClickCliRunner() if use_click else TyperCliRunner()
        return runner.invoke(module.cli, args, env={"COLUMNS": "200", "NO_COLOR": "1", "TERM": "dumb"})

    return _run


EXPLICIT_ARGUMENT = """
    commands:
      a:
        params:
          - name: who
            type: str
            help: Person to greet
            required: true
          - name: greeting
            type: str
            default: hello
          - name: suffix
            type: str
        run: print(greeting, who, suffix)
"""


@BACKENDS
@pytest.mark.parametrize(
    "args, expected_output",
    [(["Ada"], "hello Ada None"), (["Ada", "hi"], "hi Ada None"), (["Ada", "hi", "!"], "hi Ada !")],
)
def test_explicit_param_without_dashes_is_a_positional_argument(run, use_click, args, expected_output):
    # the Click backend used to turn `name: who` into the option `--who`
    result = run(EXPLICIT_ARGUMENT, ["a", *args], use_click)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected_output


@BACKENDS
def test_required_explicit_argument_is_required(run, use_click):
    result = run(EXPLICIT_ARGUMENT, ["a"], use_click)

    assert result.exit_code == 2
    assert "who" in result.output.lower()


@BACKENDS
def test_explicit_argument_help_is_shown(run, use_click):
    result = run(EXPLICIT_ARGUMENT, ["a", "-h"], use_click)

    assert "Person to greet" in result.output
    assert "--who" not in result.output


@BACKENDS
@pytest.mark.parametrize("args, expected_output", [([], "None"), (["x"], "x")])
def test_shorthand_argument_without_bang_is_optional(run, use_click, args, expected_output):
    result = run("commands:\n  a:\n    params: [label: str]\n    run: print(label)\n", ["a", *args], use_click)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected_output


@BACKENDS
def test_explicit_option_with_short_help_and_required(run, use_click):
    body = """
        commands:
          a:
            params:
              - name: --width
                type: int
                short: -w
                help: Target width
                required: true
            run: print(width + 1)
    """
    assert run(body, ["a", "-w", "2"], use_click).output.strip() == "3"
    assert run(body, ["a"], use_click).exit_code == 2
    assert "Target width" in run(body, ["a", "-h"], use_click).output


@BACKENDS
@pytest.mark.parametrize(
    "types, param, args, expected_output",
    [
        ("N: int", "- --n: N", ["--n", "2"], "3"),
        ("N: int = 5", "- --n: N", [], "6"),
        ("N: int = 5", "- --n|-x: N", ["-x", "1"], "2"),
        ("N: int", "- --n: N = 7", [], "8"),
        ("N: int", "- n: N!", ["4"], "5"),
        ("N: int", "- name: --n\n        type: N\n        default: 9", [], "10"),
    ],
    ids=["option", "type_default", "short", "param_default", "argument", "explicit"],
)
def test_types_section_names_a_type(run, use_click, types, param, args, expected_output):
    # `--n: N` with `types: {N: int}` was a NameError with the Click backend
    body = f"types:\n  {types}\ncommands:\n  a:\n    params:\n      {param}\n    run: print(n + 1)\n"
    result = run(body, ["a", *args], use_click)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected_output


def test_types_section_can_hold_a_click_decorator(run):
    body = """
        types:
          Loud: "@click.option('--loud', '-l', is_flag=True, help='Shout')"
        global_params:
          - loud: Loud
        commands:
          a: print(loud)
          b:
            params: [word: str!]
            run: print(word.upper() if loud else word)
    """
    assert run(body, ["a", "-l"]).output.strip() == "True"
    assert run(body, ["b", "hi", "--loud"]).output.strip() == "HI"
    assert "Shout" in run(body, ["b", "-h"]).output


@pytest.mark.parametrize(
    "body, expected_error",
    [
        (
            "types:\n  Level: int = typer.Option(1, '--level')\n"
            "commands:\n  pack:\n    params: [level: Level]\n    run: print(level)\n",
            r"commands\.pack: .*types\.Level.*Typer definition.*@click\.option",
        ),
        (
            "commands:\n  pack:\n    params:\n      - level: int = typer.Option(1, '--level')\n    run: print(level)\n",
            r"commands\.pack: .*param `level`.*Typer definition.*@click\.option",
        ),
        (
            "commands:\n  pack:\n    params: ['level: int = 1']\n    run: print(level)\n",
            r"commands\.pack: .*`level: int = 1`.*Click decorator",
        ),
    ],
    ids=["types", "shorthand", "generic_signature"],
)
def test_typer_definitions_are_rejected_with_a_manifest_error(run, body, expected_error):
    # these used to be copied into the Click code and fail when the CLI was run
    with pytest.raises(ValueError, match=expected_error):
        run(body, ["pack"])


@BACKENDS
@pytest.mark.parametrize(
    "param, args, expected_output",
    [
        ("--tag: list[str]", ["--tag", "a", "--tag", "b"], "['a', 'b']"),
        ("names: list[str]", ["a", "b"], "['a', 'b']"),
        ("--n: Optional[int]", ["--n", "2"], "[2]"),
        ("--n: int | None", ["--n", "2"], "[2]"),
    ],
    ids=["list_option", "list_argument", "optional", "union_none"],
)
def test_optional_and_list_types(run, use_click, param, args, expected_output):
    name = param.split(":")[0].lstrip("-")
    body = f"commands:\n  a:\n    params:\n      - '{param.split(':')[0]}': {param.split(': ')[1]}\n"
    body += f"    run: print(list({name}) if isinstance({name}, (list, tuple)) else [{name}])\n"
    result = run(body, ["a", *args], use_click)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected_output


CONFIG = """
    command_templates:
      admin:
        config:
          epilog: from the template
    commands:
      visible: print(1)
      secret:
        config:
          hidden: true
        run: print(2)
      old:
        help: Old command
        config:
          deprecated: true
          epilog: See the new command
          short_help: Short text
        run: print(3)
      reset:
        template: admin
        config:
          no_args_is_help: true
          context_settings:
            max_content_width: 60
        params: [target: str]
        run: print(target)
"""


@BACKENDS
def test_command_config_is_applied(run, use_click):
    # `config` was ignored by the Click backend
    overview = run(CONFIG, ["-h"], use_click).output
    assert "visible" in overview
    assert "secret" not in overview
    assert "Short text" in overview

    assert run(CONFIG, ["secret"], use_click).output.strip() == "2"
    assert "See the new command" in run(CONFIG, ["old", "-h"], use_click).output
    assert "deprecated" in run(CONFIG, ["old", "-h"], use_click).output.lower()

    no_args = run(CONFIG, ["reset"], use_click)
    assert "Usage:" in no_args.output
    assert "from the template" in no_args.output
    assert run(CONFIG, ["reset", "db"], use_click).output.strip() == "db"


HELP_PANEL = "commands:\n  a:\n    config:\n      rich_help_panel: Admin\n    run: print(1)\n  b: print(2)\n"


def test_rich_help_panel_with_typer(run):
    assert "Admin" in run(HELP_PANEL, ["-h"], use_click=False).output


def test_rich_help_panel_with_click_needs_rich_click(run):
    # panels are a rich-click feature: the generated code then imports rich_click without a fallback
    try:
        import rich_click  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError, match="rich_click"):
            run(HELP_PANEL, ["-h"])
    else:
        assert "Admin" in run(HELP_PANEL, ["-h"]).output


@BACKENDS
def test_help_only_subcommand_sets_the_help_of_a_nested_group(run, use_click):
    body = "commands:\n  a.b:\n    help: Nested group help\n  a.b.c: print(1)\n"

    assert run(body, ["a", "b", "c"], use_click).output.strip() == "1"
    assert "Nested group help" in run(body, ["a", "-h"], use_click).output


@BACKENDS
def test_type_alias_keeps_the_help_of_an_explicit_param(run, use_click):
    # a plain type in `types` used to replace the whole definition for Typer: the option became an argument
    body = """
        types:
          Token: str
        commands:
          a:
            params:
              - name: --token
                type: Token
                default: abc
                help: Access token
            run: print(token)
    """
    assert run(body, ["a"], use_click).output.strip() == "abc"
    assert run(body, ["a", "--token", "x"], use_click).output.strip() == "x"
    assert "Access token" in run(body, ["a", "-h"], use_click).output


BLOCK_RICH_CLICK = """
import importlib.abc
import runpy
import sys


class NoRichClick(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] == "rich_click":
            raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
        return None


sys.meta_path.insert(0, NoRichClick())
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
"""


def generate_click_cli(tmp_path, body: str) -> str:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text("name: t\nversion: '1'\nuse_click: true\n" + textwrap.dedent(body), encoding="utf-8")
    with open(manifest_path, encoding="utf-8") as manifest_io:
        code = Transformer(manifest_io, validate_requires=False).cli.code
    (tmp_path / "generated.py").write_text(code, encoding="utf-8")
    (tmp_path / "without_rich_click.py").write_text(BLOCK_RICH_CLICK, encoding="utf-8")
    return code


def run_without_rich_click(tmp_path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(tmp_path / "without_rich_click.py"), str(tmp_path / "generated.py"), *args],
        capture_output=True,
        text=True,
    )


def test_click_cli_runs_without_rich_click(tmp_path):
    # the generated code imported rich_click unconditionally: without the `rich` extra no Click CLI could start
    body = """
        commands:
          greet:
            help: Greet someone
            params:
              - name: who
                type: str
                help: Person to greet
                required: true
              - --times|-t: int = 1
            run: print(f"hello {who} " * times)
    """
    code = generate_click_cli(tmp_path, body)
    assert "import rich_click as click" in code

    ran = run_without_rich_click(tmp_path, "greet", "Ada", "-t", "2")
    assert ran.returncode == 0, ran.stderr
    assert ran.stdout.strip() == "hello Ada hello Ada"

    helped = run_without_rich_click(tmp_path, "greet", "--help")
    assert helped.returncode == 0, helped.stderr
    assert "Greet someone" in helped.stdout
    assert "╭" not in helped.stdout  # plain click output, no rich panels


def test_click_cli_that_uses_a_rich_feature_requires_rich_click(tmp_path):
    body = """
        commands:
          a:
            config:
              rich_help_panel: Admin
            run: print(1)
    """
    code = generate_click_cli(tmp_path, body)
    assert "except ImportError" not in code

    ran = run_without_rich_click(tmp_path, "a")
    assert ran.returncode != 0
    assert "No module named 'rich_click'" in ran.stderr
