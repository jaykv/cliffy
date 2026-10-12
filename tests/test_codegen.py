"""Generated code has to stay valid, and say what the manifest says, whatever text the manifest holds."""
# ruff: noqa: E501
# the manifests are one-line strings on purpose: their quoting and escaping is what is being tested

import os
import textwrap

import pytest
from click.testing import CliRunner as ClickCliRunner
from typer.testing import CliRunner as TyperCliRunner

from cliffy.helper import import_module_from_path, py_str, to_identifier
from cliffy.transformer import Transformer

BASE = "name: t\nversion: '1'\n"
CLICK = BASE + "use_click: true\n"


@pytest.fixture
def generate(tmp_path):
    """Writes a manifest, transforms it and returns the Transformer"""
    counter = iter(range(1000))

    def _generate(manifest: str) -> Transformer:
        manifest_path = tmp_path / f"manifest{next(counter)}.yaml"
        manifest_path.write_text(textwrap.dedent(manifest), encoding="utf-8")
        with open(manifest_path, encoding="utf-8") as manifest_io:
            return Transformer(manifest_io, validate_requires=False)

    return _generate


@pytest.fixture
def run(generate, tmp_path):
    """Generates a CLI from a manifest, imports it and invokes it with args"""
    counter = iter(range(1000))

    def _run(manifest: str, args: list[str]):
        T = generate(manifest)
        compile(T.cli.code, "generated", "exec")  # a SyntaxError here is the clearest failure
        module_path = tmp_path / f"generated{next(counter)}.py"
        module_path.write_text(T.cli.code, encoding="utf-8")
        module = import_module_from_path(str(module_path))
        runner = ClickCliRunner() if T.manifest.use_click else TyperCliRunner()
        return runner.invoke(module.cli, args, env={"COLUMNS": "200", "NO_COLOR": "1", "TERM": "dumb"})

    return _run


@pytest.mark.parametrize(
    "manifest, args, expected_output",
    [
        pytest.param(BASE + "help: 'say \"hi\"'\ncommands:\n  a: print(1)\n", ["-h"], 'say "hi"', id="cli_help_quote"),
        pytest.param(
            BASE + "commands:\n  a:\n    help: 'say \"hi\"'\n    run: print(1)\n",
            ["a", "-h"],
            'say "hi"',
            id="help_quote",
        ),
        pytest.param(
            BASE + "commands:\n  a:\n    help: 'in C:\\new\\'\n    run: print(1)\n",
            ["a", "-h"],
            "in C:\\new\\",
            id="help_backslash",
        ),
        pytest.param(
            BASE + "commands:\n  db:\n    help: 'the \"db\"'\n  db.create: print(1)\n",
            ["-h"],
            'the "db"',
            id="group_help_quote",
        ),
        pytest.param(
            BASE + "commands:\n  db:\n    help: |\n      Data\n      base\n  db.create: print(1)\n",
            ["db", "create"],
            "1",
            id="group_help_multiline",
        ),
        pytest.param(
            'name: t\nversion: "1\'x"\ncommands:\n  a: print(1)\n', ["--version"], "t, 1'x", id="version_quote"
        ),
        pytest.param(
            BASE + 'vars:\n  greeting: "it\'s me"\ncommands:\n  a: print(greeting)\n', ["a"], "it's me", id="var_quote"
        ),
        pytest.param(
            BASE + "vars:\n  p: 'C:\\temp\\new'\ncommands:\n  a: print(p)\n", ["a"], "C:\\temp\\new", id="var_backslash"
        ),
        pytest.param(
            BASE + "commands:\n  a:\n    config:\n      epilog: 'see \"docs\"'\n    run: print(1)\n",
            ["a", "-h"],
            'see "docs"',
            id="config_quote",
        ),
        pytest.param(
            BASE + "cli_options:\n  epilog: 'see \"docs\"'\ncommands:\n  a: print(1)\n",
            ["-h"],
            'see "docs"',
            id="cli_options_quote",
        ),
        pytest.param(
            BASE
            + "commands:\n  a:\n    params:\n      - name: --who\n        type: str\n        help: 'the \"who\"'\n    run: print(who)\n",
            ["a", "-h"],
            'the "who"',
            id="param_help_quote",
        ),
        pytest.param(
            BASE
            + "commands:\n  a:\n    params:\n      - name: --who\n        type: str\n        default: 'a\\'\n    run: print(who)\n",
            ["a"],
            "a\\\n",
            id="param_default_backslash",
        ),
        pytest.param(
            BASE
            + 'commands:\n  a:\n    params:\n      - name: --who\n        type: str\n        default: "a\\nb"\n    run: print(who)\n',
            ["a"],
            "a\nb\n",
            id="param_default_newline",
        ),
        pytest.param(
            BASE
            + "commands:\n  a:\n    params:\n      - name: --who\n        type: str\n        default: 5\n    run: print(who + '!')\n",
            ["a"],
            "5!",
            id="param_default_int_for_str",
        ),
        pytest.param(
            BASE + "commands:\n  a:\n    aliases: ['b\"c']\n    run: print(1)\n", ['b"c'], "1", id="alias_quote"
        ),
        pytest.param(
            CLICK + "help: 'say \"hi\"'\ncommands:\n  a: print(1)\n", ["-h"], 'say "hi"', id="click_cli_help_quote"
        ),
        pytest.param(
            CLICK + "commands:\n  a:\n    help: 'ends with \"'\n    run: print(1)\n",
            ["a", "-h"],
            'ends with "',
            id="click_help_quote",
        ),
        pytest.param(
            'name: t\nversion: "1\'x"\nuse_click: true\ncommands:\n  a: print(1)\n',
            ["--version"],
            "version 1'x",
            id="click_version_quote",
        ),
        pytest.param(
            CLICK
            + 'commands:\n  a:\n    params:\n      - name: --who\n        type: str\n        help: "it\'s who"\n    run: print(who)\n',
            ["a", "-h"],
            "it's who",
            id="click_param_help_quote",
        ),
    ],
)
def test_manifest_text_is_escaped(run, manifest, args, expected_output):
    result = run(manifest, args)
    assert result.exit_code == 0, result.output
    assert expected_output in result.output


@pytest.mark.parametrize(
    "manifest",
    [
        pytest.param(
            BASE
            + 'help: \'"""+__import__("os").environ.__setitem__("CLIFFY_PWNED","1")+"""\'\ncommands:\n  a: print(1)\n',
            id="typer_cli_help",
        ),
        pytest.param(
            CLICK
            + 'help: \'"""+__import__("os").environ.__setitem__("CLIFFY_PWNED","1")+"""\'\ncommands:\n  a: print(1)\n',
            id="click_cli_help",
        ),
        pytest.param(
            BASE
            + 'commands:\n  a:\n    help: \'"+__import__("os").environ.__setitem__("CLIFFY_PWNED","1")+"\'\n    run: print(1)\n',
            id="command_help",
        ),
        pytest.param(
            BASE
            + "vars:\n  v: \"'+__import__('os').environ.__setitem__('CLIFFY_PWNED','1')+'\"\ncommands:\n  a: print(1)\n",
            id="var",
        ),
        pytest.param(
            "name: t\nversion: \"'+__import__('os').environ.__setitem__('CLIFFY_PWNED','1')+'\"\ncommands:\n  a: print(1)\n",
            id="version",
        ),
    ],
)
def test_manifest_text_is_not_executed(run, monkeypatch, manifest):
    monkeypatch.delenv("CLIFFY_PWNED", raising=False)
    result = run(manifest, ["a"])
    assert result.exit_code == 0, result.output
    assert "CLIFFY_PWNED" not in os.environ


@pytest.mark.parametrize(
    "manifest, args, expected_output",
    [
        pytest.param(BASE + "commands:\n  import: print(1)\n", ["import"], "1", id="keyword_command"),
        pytest.param(BASE + "commands:\n  2fa: print(1)\n", ["2fa"], "1", id="digit_command"),
        pytest.param(BASE + "commands:\n  cli: print(1)\n  other: print(2)\n", ["other"], "2", id="cli_command"),
        pytest.param(
            BASE + "commands:\n  typer: print(1)\n  other:\n    params: [--x: int = 1]\n    run: print(2)\n",
            ["other"],
            "2",
            id="typer_command",
        ),
        pytest.param(
            BASE + "commands:\n  list: print(1)\n  show: print(list('ab'))\n",
            ["show"],
            "['a', 'b']",
            id="builtin_command",
        ),
        pytest.param(BASE + "commands:\n  print: print('printed')\n", ["--version"], "t, 1", id="print_command"),
        pytest.param(BASE + "commands:\n  my-group.sub: print(1)\n", ["my-group", "sub"], "1", id="dash_group"),
        pytest.param(BASE + "commands:\n  2fa.setup: print(1)\n", ["2fa", "setup"], "1", id="digit_group"),
        pytest.param(
            BASE + "commands:\n  a.b:\n    help: sub help\n  a.b.c: print(1)\n",
            ["a", "b", "c"],
            "1",
            id="nested_group_help",
        ),
        pytest.param(
            CLICK + "commands:\n  remove-all:\n    aliases: [rm-all]\n    run: print(1)\n",
            ["rm-all"],
            "1",
            id="click_dash_alias",
        ),
        pytest.param(
            CLICK + "commands:\n  click: print(1)\n  other:\n    params: [--n: int = 1]\n    run: print(2)\n",
            ["other"],
            "2",
            id="click_command",
        ),
    ],
)
def test_names_become_valid_identifiers(run, manifest, args, expected_output):
    result = run(manifest, args)
    assert result.exit_code == 0, result.output
    assert expected_output in result.output


MULTILINE_HELP = "Greet\\nthe user.\\n\\nSecond\\n  paragraph."


@pytest.mark.parametrize("base", [BASE, CLICK], ids=["typer", "click"])
@pytest.mark.parametrize(
    "commands, args",
    [
        (f'  a:\n    help: "{MULTILINE_HELP}"\n    run: print(1)\n', ["a", "-h"]),
        (f'  g:\n    help: "{MULTILINE_HELP}"\n  g.a: print(1)\n', ["g", "-h"]),
        (f'  g.a:\n    help: "{MULTILINE_HELP}"\n    run: print(1)\n', ["g", "a", "-h"]),
    ],
    ids=["command", "group", "subcommand"],
)
def test_help_line_breaks_become_spaces_and_paragraphs_are_kept(run, base, commands, args):
    result = run(base + "commands:\n" + commands, args)

    assert result.exit_code == 0, result.output
    lines = [line.strip(" │") for line in result.output.splitlines()]
    assert "Greet the user." in lines
    assert "Second paragraph." in lines
    # each paragraph is rendered on its own (Typer puts a blank line in between, rich-click does not)
    assert lines.index("Second paragraph.") > lines.index("Greet the user.")


@pytest.mark.parametrize("base", [BASE, CLICK], ids=["typer", "click"])
def test_help_overview_shows_the_first_paragraph(run, base):
    result = run(base + f'commands:\n  a:\n    help: "{MULTILINE_HELP}"\n    run: print(1)\n', ["-h"])

    assert "Greet the user." in result.output
    assert "Greetthe" not in result.output


COLLIDING_NAMES = [
    # a root command and a group that both used to be the Python name `db_app`
    pytest.param("commands:\n  db-app: print(1)\n  db.x: print(2)\n", ["db-app"], "1", id="command_vs_group_var"),
    pytest.param("commands:\n  db-app: print(1)\n  db.x: print(2)\n", ["db", "x"], "2", id="group_var_vs_command"),
    pytest.param("commands:\n  db.x: print(2)\n  db-app: print(1)\n", ["db", "x"], "2", id="group_var_declared_first"),
    pytest.param("commands:\n  a-b: print(1)\n  a_b: print(2)\n", ["a-b"], "1", id="dash_vs_underscore"),
    pytest.param("commands:\n  a.b: print(1)\n  a_b: print(2)\n", ["a", "b"], "1", id="subcommand_vs_command"),
    pytest.param("commands:\n  a.b.x: print(1)\n  a_b.y: print(2)\n", ["a", "b", "x"], "1", id="group_vs_group"),
    pytest.param("commands:\n  a.b.x: print(1)\n  a_b.y: print(2)\n", ["a_b", "y"], "2", id="group_vs_group_second"),
    pytest.param(
        "imports: import json\ncommands:\n  json: print(1)\n  dump: print(json.dumps([2]))\n",
        ["dump"],
        "[2]",
        id="command_vs_import",
    ),
    pytest.param(
        "vars:\n  status: up\ncommands:\n  status: print(1)\n  show: print(status)\n",
        ["show"],
        "up",
        id="command_vs_var",
    ),
    pytest.param(
        "functions:\n  - |\n    def helper():\n        return 3\ncommands:\n  helper: print(1)\n  show: print(helper())\n",
        ["show"],
        "3",
        id="command_vs_function",
    ),
    pytest.param(
        "commands:\n  rm|rm-x: print(1)\n  rm-rm-x: print(2)\n  rm_rm_x: print(3)\n",
        ["rm-x"],
        "1",
        id="alias_vs_command",
    ),
]


@pytest.mark.parametrize("base", [BASE, CLICK], ids=["typer", "click"])
@pytest.mark.parametrize("manifest, args, expected_output", COLLIDING_NAMES)
def test_names_that_collide_get_distinct_identifiers(run, base, manifest, args, expected_output):
    result = run(base + manifest, args)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected_output


@pytest.mark.parametrize(
    "name, hint",
    [("my-var", "my_var"), ("2nd", ""), ("class", ""), ("cli", ""), ("typer", ""), ("has space", "")],
)
def test_var_name_must_be_a_python_identifier(generate, capsys, name, hint):
    # a var becomes a module-level Python variable: `my-var = "x"` was a SyntaxError in the generated code
    with pytest.raises(SystemExit):
        generate(BASE + f"vars:\n  {name}: x\ncommands:\n  a: print(1)\n")

    error = capsys.readouterr()
    assert f"vars.{name}" in error.out + error.err
    assert hint in error.out + error.err


@pytest.mark.parametrize("use_click", [False, True])
def test_keyword_param_name_is_rejected(generate, use_click):
    manifest = (CLICK if use_click else BASE) + "commands:\n  a:\n    params: [--from: str = 'x']\n    run: print(1)\n"
    with pytest.raises(ValueError, match="Invalid param name: --from"):
        generate(manifest)


@pytest.mark.parametrize(
    "manifest, args, expected_output",
    [
        pytest.param(
            BASE + "global_params:\n  - --verbose: bool = False\ncommands:\n  a: print(verbose)\n",
            ["a", "--verbose"],
            "True",
            id="global_params_without_own_params",
        ),
        pytest.param(
            CLICK + "global_params:\n  - --verbose: bool = False\ncommands:\n  a: print(verbose)\n",
            ["a", "--verbose"],
            "True",
            id="click_global_params_without_own_params",
        ),
        pytest.param(
            CLICK
            + "global_params:\n  - --verbose: bool = False\ncommands:\n  a:\n    params: [--n: int = 1]\n    run: print(verbose, n)\n",
            ["a", "--verbose", "--n", "2"],
            "True 2",
            id="click_global_params",
        ),
        pytest.param(
            BASE + 'commands:\n  a:\n    params:\n      - --who: str = "a=b"\n    run: print(who)\n',
            ["a"],
            "a=b",
            id="simple_default_with_equals",
        ),
        pytest.param(
            BASE
            + 'commands:\n  a:\n    params:\n      - name: str = typer.Option("a=b", "--name")\n    run: print(name)\n',
            ["a"],
            "a=b",
            id="typer_definition_is_passed_through",
        ),
        pytest.param(
            BASE + "commands:\n  a:\n    params: [--dry-run|-d: bool = False]\n    run: print(dry_run)\n",
            ["a", "--dry-run"],
            "True",
            id="dashed_option_with_short",
        ),
        pytest.param(
            CLICK + "commands:\n  a:\n    params: [--name|-n: str]\n    run: print(name)\n",
            ["a", "-n", "x"],
            "x",
            id="click_short",
        ),
        pytest.param(
            CLICK
            + "commands:\n  a:\n    params:\n      - name: --who\n        type: str\n        short: -w\n    run: print(who)\n",
            ["a", "-w", "x"],
            "x",
            id="click_explicit_option",
        ),
        pytest.param(
            CLICK
            + 'commands:\n  a:\n    params:\n      - name: --who\n        type: str\n        default: "it\'s"\n    run: print(who)\n',
            ["a"],
            "it's",
            id="click_explicit_default_quote",
        ),
        pytest.param(
            CLICK + "commands:\n  a:\n    params: [--dry-run: int = 0]\n    run: print(dry_run)\n",
            ["a", "--dry-run", "3"],
            "3",
            id="click_dashed_option",
        ),
        pytest.param(
            CLICK + "commands:\n  a:\n    params: [env-var: str!]\n    run: print(env_var)\n",
            ["a", "x"],
            "x",
            id="click_dashed_argument",
        ),
        pytest.param(
            CLICK + "commands:\n  a:\n    params: [--force: bool = False]\n    run: print(force)\n",
            ["a", "--force"],
            "True",
            id="click_flag",
        ),
        pytest.param(
            CLICK + "commands:\n  a:\n    params: [--force: bool = True]\n    run: print(force)\n",
            ["a", "--no-force"],
            "False",
            id="click_flag_off",
        ),
        pytest.param(
            CLICK + "commands:\n  a:\n    params: [--name: str = World]\n    run: print(name)\n",
            ["a"],
            "World",
            id="click_bare_default",
        ),
        # guard, not a regression: the quoted spelling already worked and has to keep working
        pytest.param(
            CLICK + 'commands:\n  a:\n    params:\n      - --name: str = "World"\n    run: print(name + "!")\n',
            ["a"],
            "World!",
            id="click_quoted_default",
        ),
    ],
)
def test_params(run, manifest, args, expected_output):
    result = run(manifest, args)
    assert result.exit_code == 0, result.output
    assert expected_output in result.output


@pytest.mark.parametrize(
    "manifest, args, expected_output",
    [
        pytest.param(
            BASE
            + "command_templates:\n  t:\n    params: [--x: int = 1]\ncommands:\n  db.create: print(1)\n"
            + "  (*).list:\n    template: t\n    run: print(x)\n",
            ["db", "list", "--x", "3"],
            "3",
            id="template",
        ),
        pytest.param(
            BASE + "commands:\n  db.create: print(1)\n  (*).list|ls: print('l')\n", ["db", "ls"], "l", id="alias"
        ),
        pytest.param(
            BASE + "commands:\n  a.b.c: print(1)\n  (*).list: print('list {(*)}')\n",
            ["a", "b", "list"],
            "list a.b",
            id="nested_group",
        ),
        pytest.param(
            BASE + "commands:\n  a.b.c: print(1)\n  (*).list: print('list {(*)}')\n",
            ["a", "list"],
            "list a\n",
            id="parent_group",
        ),
        pytest.param(
            BASE
            + "commands:\n  db.create: print(1)\n  (*).list:\n    params:\n      - name: --n\n        type: int\n        default: 5\n"
            + "    run: print(n)\n",
            ["db", "list"],
            "5",
            id="non_str_default",
        ),
    ],
)
def test_greedy_commands(run, manifest, args, expected_output):
    result = run(manifest, args)
    assert result.exit_code == 0, result.output
    assert expected_output in result.output


@pytest.mark.parametrize("base", [BASE, CLICK], ids=["typer", "click"])
def test_generated_imports_are_sorted(generate, base):
    code = generate(base + "commands:\n  a: print(1)\n").cli.code
    base_imports = code.splitlines()[1:4]
    assert all(line.startswith(("import ", "from ")) for line in base_imports)
    assert base_imports == sorted(base_imports)


# Tests for py_str: the literal has to evaluate back to the original text
@pytest.mark.parametrize(
    "text",
    [
        "plain",
        'say "hi"',
        "it's",
        "C:\\new\\temp\\",
        "line1\nline2",
        'ends with quote"',
        '"""',
        "{braces} and {{double}}",
        "tab\tand null\x00",
        "héllo ✨ 💔",
        "",
    ],
)
def test_py_str_round_trips(text):
    literal = py_str(text)
    assert literal.startswith('"') and "\n" not in literal
    assert eval(literal) == text


@pytest.mark.parametrize(
    "name, expected_output",
    [
        ("hello", "hello"),
        ("a-b", "a_b"),
        ("a.b", "a_b"),
        ("a|b", "a_b"),
        ("2fa", "_2fa"),
        ("import", "import_"),  # keyword
        ("list", "list_"),  # builtin
        ("print", "print_"),  # builtin
        ("cli", "cli_"),  # the generated app object
        ("typer", "typer_"),  # the generated import
        ("db_app", "db_app"),
    ],
)
def test_to_identifier(name, expected_output):
    assert to_identifier(name) == expected_output
    assert to_identifier(name).isidentifier()
