import click
import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from cliffy.cli import cli
from cliffy.cli import test_command as manifest_test_command
from cliffy.commanders.click import ClickCommander
from cliffy.commanders.typer import TyperCommander
from cliffy.manifest import Callback, CLIManifest, CommandParam, RunBlock, SimpleCommandParam
from cliffy.tester import Tester as ManifestTester

CALLBACKS_MANIFEST = """
name: {name}
version: 1.2.3
use_click: {use_click}

callbacks:
  - params:
      - name: --verbose
        type: bool
        default: false
        short: -v
        help: Print what is about to run
      - --profile: str = "dev"
    invoke_without_command: true
    run: |
      ctx.obj = profile
      if ctx.invoked_subcommand is None:
          print("no command")
      elif verbose:
          print(f"running {{ctx.invoked_subcommand}} on {{profile}}")
  - run: print("second root callback")
  - group: db
    run: print("connecting")
  - group: db.tables
    params:
      - --schema: str = "public"
    run: print(f"schema {{schema}}")

commands:
  hello | hi: print("hello")
  db.migrate: print("migrating")
  db.tables.list: print("tables")

tests:
  - hello: assert result.output == "second root callback\\nhello\\n"
  - -v hello: assert result.output == "running hello on dev\\nsecond root callback\\nhello\\n"
  - --verbose --profile prod hello: assert result.output.startswith("running hello on prod\\n")
  - db migrate: assert result.output == "second root callback\\nconnecting\\nmigrating\\n"
  - db tables --schema app list: assert result.output.endswith("connecting\\nschema app\\ntables\\n")
  - "": assert result.output == "no command\\nsecond root callback\\n"
  - --version: assert "1.2.3" in result.output and "callback" not in result.output
  - --aliases: assert "hi" in result.output and "callback" not in result.output
"""


@pytest.fixture(params=[False, True], ids=["typer", "click"])
def callbacks_manifest(request, tmp_path):
    framework = "click" if request.param else "typer"
    path = tmp_path / f"callbacks_{framework}.yaml"
    path.write_text(CALLBACKS_MANIFEST.format(name=f"cb-{framework}", use_click=str(request.param).lower()))
    return str(path)


def test_callbacks_run_before_commands_and_keep_builtin_options(callbacks_manifest):
    tester = ManifestTester(callbacks_manifest)
    assert tester.total_cases == 8

    for case in tester.test_pipeline:
        runs = tester.invoke_test(case.command, case.assert_script)  # type: ignore[union-attr]
        result = next(runs)
        assert result.exception is None or isinstance(result.exception, SystemExit), result.output
        assert result.exit_code == 0, result.output
        # runs the assert of the manifest test
        assert next(runs, None) is None


def test_callbacks_manifest_passes_cli_test(callbacks_manifest):
    result = CliRunner().invoke(manifest_test_command, [callbacks_manifest])
    assert "All tests passed" in result.output
    assert result.exit_code == 0


def test_callbacks_example_passes_cli_test():
    result = CliRunner().invoke(manifest_test_command, ["examples/callbacks.yaml"])
    assert "All tests passed" in result.output
    assert result.exit_code == 0


def test_callback_params_are_options_of_the_cli(callbacks_manifest):
    result = CliRunner().invoke(cli, ["run", callbacks_manifest, "--", "--help"])
    assert result.exit_code == 0
    # rich colours the help when it thinks it is on a CI runner (GITHUB_ACTIONS), also when captured
    output = click.unstyle(result.output)
    for option in ("--verbose", "-v", "--profile", "--version", "--aliases", "Print what is about to run"):
        assert option in output


def test_manifest_without_callbacks_generates_the_same_entry_point():
    manifest = CLIManifest(name="plain", version="1.0.0", commands={"a.b": "print(1)"})

    typer_code = TyperCommander(manifest)
    typer_code.generate_cli()
    assert "@cli.callback()\ndef main(\n    version: Optional[bool]" in typer_code.cli
    assert "ctx" not in typer_code.cli
    assert "a_app = typer.Typer()\n" in typer_code.cli

    click_code = ClickCommander(manifest)
    click_code.generate_cli()
    assert "def cli():\n" in click_code.cli
    assert "@click.group()\ndef a_app():\n" in click_code.cli
    assert "pass_context" not in click_code.cli


def test_typer_callback_codegen():
    manifest = CLIManifest(
        name="cb",
        version="1.0.0",
        commands={"db.up": "print(1)"},
        callbacks=[
            Callback(run=RunBlock("print('root')"), params=[SimpleCommandParam({"--debug": "bool = False"})]),
            Callback(group="db", run=RunBlock("$ echo db"), invoke_without_command=True),
        ],
    )
    commander = TyperCommander(manifest)
    commander.generate_cli()

    assert (
        "@cli.callback()\ndef main(\n    ctx: typer.Context,\n    debug: bool = typer.Option(False)," in commander.cli
    )
    assert "version: Optional[bool] = typer.Option(None, '--version'" in commander.cli
    assert "@db_app.callback(invoke_without_command=True)\ndef db_app_callback(\n    ctx: typer.Context,\n):" in (
        commander.cli
    )
    # shell lines work in callbacks like in commands
    assert "subprocess.run" in commander.cli


def test_click_callback_codegen():
    manifest = CLIManifest(
        name="cb",
        version="1.0.0",
        use_click=True,
        commands={"db.up": "print(1)"},
        callbacks=[
            Callback(
                run=RunBlock("print('root')"),
                params=[CommandParam(name="--debug", type="bool", short="-d", help="Debug output")],
                invoke_without_command=True,
            ),
            Callback(group="db", run=RunBlock("print('db')")),
        ],
    )
    commander = ClickCommander(manifest)
    commander.generate_cli()

    assert "@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)" in commander.cli
    assert "@click.version_option('1.0.0')" in commander.cli
    assert (
        "@click.option('--debug/--no-debug', '-d', help='Debug output')\n@click.pass_context\ndef cli(ctx, debug):"
        in (commander.cli)
    )
    assert "@click.group()\n@click.pass_context\ndef db_app(ctx):" in commander.cli


def test_click_cli_options_take_precedence_over_callback_invoke_without_command():
    manifest = CLIManifest(
        name="cb",
        version="1.0.0",
        use_click=True,
        commands={"up": "print(1)"},
        cli_options={"invoke_without_command": False},
        callbacks=[Callback(run=RunBlock("print('root')"), invoke_without_command=True)],
    )
    commander = ClickCommander(manifest)
    commander.generate_cli()

    assert commander.cli.count("invoke_without_command") == 1
    assert "invoke_without_command=False" in commander.cli


def test_callback_group_must_exist():
    with pytest.raises(ValidationError, match=r"callback group `nope` does not match any command group \(groups: db\)"):
        CLIManifest(
            name="cb",
            version="1.0.0",
            commands={"db.up | u": "print(1)", "hello": "print(2)"},
            callbacks=[Callback(group="nope", run=RunBlock("pass"))],
        )


def test_callback_requires_run():
    with pytest.raises(ValidationError):
        Callback()  # type: ignore[call-arg]
