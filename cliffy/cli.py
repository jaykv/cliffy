import json
import sys
import traceback
from io import TextIOWrapper
from typing import Any, TextIO

from cliffy.ai import ai
from cliffy.blueprint import BlueprintError, installed_blueprints, resolve_blueprint
from cliffy.builder import build_cli, build_cli_from_manifest, run_cli
from cliffy.doc import DocGenerator
from cliffy.helper import (
    CLI_NAME_PATTERN,
    ManifestOrCLI,
    age_datetime,
    exit_err,
    indent_block,
    out,
    out_err,
    write_to_file,
)
from cliffy.homer import get_clis, get_metadata, get_metadata_path, remove_metadata, save_metadata
from cliffy.loader import Loader
from cliffy.manifest import CLIManifest
from cliffy.reloader import Reloader
from cliffy.rich import Console, click, print_rich_table  # type: ignore
from cliffy.tester import ShellScript, Tester
from cliffy.transformer import Transformer

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
ALIASES = {
    "ls": "list",
    "add": "load",
    "reload": "update",
    "rm": "remove",
    "rm-all": "remove-all",
    "rmall": "remove-all",
    "blueprints": "blueprint list",
}


def show_aliases_callback(ctx: Any, param: Any, val: bool) -> None:
    if val:
        out("Aliases:")
        for alias, command in ALIASES.items():
            out(f"  {alias.ljust(10)} Alias for {command}")
        ctx.exit()


blueprint_option = click.option(
    "--blueprint",
    "-b",
    type=str,
    default=None,
    help="Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. "
    "Overrides the `blueprint:` key of the file.",
)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
@click.option("--aliases", type=bool, is_flag=True, is_eager=True, callback=show_aliases_callback)
def cli(aliases: bool) -> None:
    pass


@click.argument("manifests", type=click.File("rb"), nargs=-1)
@blueprint_option
def load(manifests: list[TextIO], blueprint: str | None = None) -> None:
    """Load CLI for given manifest(s)"""
    for manifest in manifests:
        T = Transformer(manifest, blueprint=blueprint)
        Loader.load_from_cli(T.cli)
        save_metadata(manifest.name, T.cli)
        out(f"✨ Generated {T.cli.name} CLI v{T.cli.version} ✨", fg="green")
        out("$", fg="magenta", nl=False)
        out(f" {T.cli.name} -h")


@click.argument("cli_names", type=str, nargs=-1)
def update(cli_names: list[str]) -> None:
    """Reloads CLI by name"""
    failed = False
    for cli_name in cli_names:
        if cli_metadata := get_metadata(cli_name):
            with open(cli_metadata.runner_path, encoding="utf-8") as manifest:
                T = Transformer(manifest, blueprint=cli_metadata.blueprint)
            Loader.load_from_cli(T.cli)
            save_metadata(cli_metadata.runner_path, T.cli)
            out(f"✨ Reloaded {T.cli.name} CLI v{T.cli.version} ✨", fg="green")
            out("$", fg="magenta", nl=False)
            out(f" {T.cli.name} -h")
        else:
            out_err(f"~ {cli_name} not found")
            failed = True

    if failed:
        raise SystemExit(1)


@click.argument("manifest", type=click.File("rb"))
@blueprint_option
def render(manifest: TextIO, blueprint: str | None = None) -> None:
    """Render the CLI manifest generation as code"""
    T = Transformer(manifest, blueprint=blueprint)
    console = Console()
    console.print(T.cli.code, overflow="fold", emoji=False, markup=False)
    out(f"# Rendered {T.cli.name} CLI v{T.cli.version} ~", fg="green")


@click.argument("manifest", type=click.File("rb"))
@click.argument("cli_args", type=str, nargs=-1)
@blueprint_option
def cliffy_run(manifest: TextIO, cli_args: tuple[str], blueprint: str | None = None) -> None:
    """Run CLI for a manifest"""
    T = Transformer(manifest, blueprint=blueprint)
    run_cli(T.cli.name, T.cli.code, cli_args)


@click.argument("cli_name", type=str, default="mycli")
@click.option("--render", is_flag=True, show_default=True, default=False, help="Print template to terminal directly")
@click.option(
    "--raw",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Raw template without boilerplate helpers and examples.",
)
@click.option(
    "--json-schema",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Write JSON schema (cliffy_schema.json) file to the current directory. Useful for development.",
)
def init(cli_name: str, render: bool, raw: bool, json_schema: bool) -> None:
    """Generate a CLI manifest template"""
    if not CLI_NAME_PATTERN.fullmatch(cli_name):
        exit_err(f"~ invalid CLI name {cli_name}: use letters, digits, `_` and `-`, starting with a letter or `_`")

    try:
        template = (
            CLIManifest.get_raw_template(cli_name, json_schema)
            if raw
            else CLIManifest.get_template(cli_name, json_schema)
        )
    except ValueError as e:
        exit_err(f"~ {e}")

    if render:
        console = Console()
        console.print(template, overflow="fold", emoji=False, markup=False)
    else:
        try:
            write_to_file(f"{cli_name}.yaml", text=template)
        except Exception as e:
            exit_err(f"~ error writing to file: {e}")
        out(f"+ {cli_name}.yaml", fg="green")

    if json_schema:
        import json

        write_to_file("cliffy_schema.json", json.dumps(CLIManifest.model_json_schema()))
        out("+ cliffy_schema.json", fg="green")


def cliffy_list() -> None:
    """List all CLIs loaded"""
    cols = ["Name", "Version", "Age", "Manifest"]
    rows = [
        [metadata.cli_name, metadata.version, age_datetime(metadata.loaded), metadata.runner_path]
        for metadata in get_clis()
    ]
    print_rich_table(cols, rows, styles=["cyan", "magenta", "green", "blue"])


@click.argument("cli_names", type=str, nargs=-1)
def remove(cli_names: list[str]) -> None:
    """Remove a loaded CLI by name"""
    failed = False
    for cli_name in cli_names:
        if get_metadata_path(cli_name):
            remove_metadata(cli_name)
            Loader.unload_cli(cli_name)
            out(f"~ {cli_name} removed 💥", fg="green")
        else:
            out_err(f"~ {cli_name} not loaded")
            failed = True

    if failed:
        raise SystemExit(1)


def remove_all() -> None:
    """Remove all loaded CLIs"""
    for metadata in get_clis():
        remove_metadata(metadata.cli_name)
        Loader.unload_cli(metadata.cli_name)
        out(f"~ {metadata.cli_name} removed 💥", fg="green")


@click.argument("cli_or_manifests", type=ManifestOrCLI(), nargs=-1)
@click.option("--output-dir", "-o", type=click.Path(file_okay=False, dir_okay=True, writable=True), help="Output dir")
@click.option(
    "--python",
    "-p",
    type=str,
    help="Python interpreter to set as the zipapp shebang. This gets added after the #! ",
    default="/usr/bin/env python3",
    show_default=True,
)
@blueprint_option
def build(
    cli_or_manifests: list[TextIOWrapper | str], output_dir: str, python: str, blueprint: str | None = None
) -> None:
    """Build a CLI manifest or a loaded CLI into a single-file executable (zipapp)"""
    failed = False
    for cli_or_manifest in cli_or_manifests:
        if isinstance(cli_or_manifest, TextIOWrapper):
            cli, result = build_cli_from_manifest(
                cli_or_manifest, output_dir=output_dir, interpreter=python, blueprint=blueprint
            )
            cli_name = cli.name
        else:
            cli_name = cli_or_manifest
            if not (metadata := get_metadata(cli_name)):
                out_err(f"~ {cli_name} not loaded")
                failed = True
                continue

            result = build_cli(
                cli_name,
                script_path=Loader.get_cli_path(cli_name),
                deps=metadata.requires,
                output_dir=output_dir,
                interpreter=python,
            )

        if result.exit_code != 0:
            out(result.output)
            if result.exception:
                out(str(result.exception))
            out_err(f"~ {cli_name} build failed")
            failed = True
            continue

        out(f"+ {cli_name} built 📦", fg="green")
        out(f"  {result.path} (single file, needs Python {result.requires_python})")

    if failed:
        raise SystemExit(1)


@click.argument("cli_name", type=str)
def info(cli_name: str) -> None:
    """Display CLI info"""
    metadata = get_metadata(cli_name) or exit_err(f"~ {cli_name} not loaded")
    out(f"{click.style('name:', fg='blue')} {metadata.cli_name}")
    out(f"{click.style('version:', fg='blue')} {metadata.version}")
    out(f"{click.style('requires:', fg='blue')} {metadata.requires}")
    if metadata.blueprint:
        out(f"{click.style('blueprint:', fg='blue')} {metadata.blueprint}")
    out(f"{click.style('age:', fg='blue')} {age_datetime(metadata.loaded)} ({metadata.loaded.ctime()})")
    out(f"{click.style('manifest:', fg='blue')}\n{indent_block(metadata.manifest, spaces=2)}")


@click.argument("manifest", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.option(
    "--run-cli",
    default=False,
    help="If passed, runs CLI on each reload. Useful for syntax checks or testing command execution on each reload",
    is_flag=True,
)
@click.argument("run-cli-args", type=str, nargs=-1)
@blueprint_option
def dev(manifest: str, run_cli: bool, run_cli_args: tuple[str], blueprint: str | None = None) -> None:
    """Start hot-reloader for a manifest for active development.

    Examples:

    - cli dev examples/hello.yaml

    - cli dev examples/hello.yaml --run-cli  -- -h

    - cli dev examples/hello.yaml --run-cli hello
    """
    out(f"🔄 Watching {manifest} for changes...\n", fg="magenta")
    if blueprint:
        Reloader.watch(manifest, run_cli, run_cli_args, blueprint=blueprint)
    else:
        Reloader.watch(manifest, run_cli, run_cli_args)


@click.argument("manifest", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.option(
    "--exitfirst",
    "-x",
    is_flag=True,
    show_default=True,
    default=False,
    help="exit instantly on first error or failed test.",
)
@blueprint_option
def test(manifest: str, exitfirst: bool, blueprint: str | None = None) -> None:
    """Run tests defined in a manifest"""
    tester = Tester(manifest, blueprint=blueprint)
    if not tester.test_pipeline:
        exit_err("Missing tests section in manifest")
    out("✨ Invoking tests ✨", nl=False)
    total = tester.total_cases
    passed = 0
    for i, case in enumerate(tester.test_pipeline):
        if isinstance(case, ShellScript):
            tester.invoke_shell(case)
            continue

        out(f"\n\n🪄 > {tester.T.cli.name} {case.command}\n")
        try:
            test = tester.invoke_test(case.command, case.assert_script)
            result = next(test)
            out("⚗️ > \n" + result.output)
            if result.exception:
                out(str(result))
            next(test, "")
            out(f"\n✅ {i + 1} of {total}")
            passed += 1
        except AssertionError:
            _, _, tb = sys.exc_info()
            tb_info = traceback.extract_tb(tb)
            _, line_no, _, _ = tb_info[-1]
            expr = case.assert_script.split("\n")[line_no - 1]
            out(f"💔 AssertionError: (line {line_no}) > {expr}")
            if exitfirst:
                raise SystemExit(1) from None
        except SyntaxError:
            out("💔 Syntax error")
            traceback.print_exc()
            if exitfirst:
                raise SystemExit(1) from None
        except Exception:
            out("💔 Exception")
            traceback.print_exc()
            if exitfirst:
                raise SystemExit(1) from None

    if not passed:
        exit_err("All tests failed")

    if passed == total:
        out("\n\n💚 All tests passed!")
    else:
        out("\n\n💛 Some tests failed :(")
        raise SystemExit(1)


@click.argument("manifest", type=click.File("rb"), required=True)
@blueprint_option
def validate(manifest: TextIO, blueprint: str | None = None) -> None:
    """Validate the syntax and structure of a CLI manifest"""
    try:
        Transformer(manifest, blueprint=blueprint)
        out(f"Manifest {manifest.name} is valid", fg="green")
    except Exception as e:
        exit_err(f"Manifest {manifest.name} is invalid: {e}")


@click.argument("cli_or_manifest", type=ManifestOrCLI())
@click.option("--format", "-f", type=click.Choice(["md", "rst", "html"]), default="md")
@click.option(
    "--output-dir", "-o", type=click.Path(exists=True, dir_okay=True, file_okay=False), help="Output directory"
)
@blueprint_option
def docs(cli_or_manifest: str, format: str, output_dir: str, blueprint: str | None = None) -> None:
    """Generate documentation for a CLI"""
    if isinstance(cli_or_manifest, TextIOWrapper):
        T = Transformer(cli_or_manifest, blueprint=blueprint)
        doc_generator = DocGenerator(T.manifest)  # type: ignore
        doc_generator.generate(format, output_dir)
        out(f"+ {T.cli.name}.{format}")
    else:
        metadata = get_metadata(cli_or_manifest) or exit_err(f"~ {cli_or_manifest} not loaded")
        # metadata.manifest is the raw manifest text. It still has to be rendered and merged with its
        # includes, so it is transformed from its source like `cli update` does.
        with open(metadata.runner_path, encoding="utf-8") as manifest:
            T = Transformer(manifest, validate_requires=False, blueprint=blueprint or metadata.blueprint)
        doc_generator = DocGenerator(T.manifest)  # type: ignore
        doc_generator.generate(format, output_dir)
        out(f"+ {metadata.cli_name}.{format}")


@click.group("blueprint", context_settings=CONTEXT_SETTINGS)
def blueprint_group() -> None:
    """Work with blueprints: custom YAML specs that map onto a CLI"""


def blueprint_list() -> None:
    """List the blueprints provided by installed packages"""
    blueprints = installed_blueprints()
    if not blueprints:
        out("No blueprints installed. Use a .py file or module:Class reference, or install a blueprint package.")
        return

    rows = []
    for blueprint in blueprints:
        try:
            description = blueprint.load().describe()
        except BlueprintError as e:
            description = f"error: {e}"
        rows.append([blueprint.name, blueprint.target, blueprint.package, description])
    print_rich_table(["Name", "Blueprint", "Package", "Description"], rows, styles=["cyan", "magenta", "green", "blue"])


@click.argument("blueprint", type=str)
@click.option("--output", "-o", type=click.Path(dir_okay=False, writable=True), help="Write the schema to a file")
def blueprint_schema(blueprint: str, output: str | None) -> None:
    """Print the JSON schema of a blueprint's spec, for validation and editor completion"""
    try:
        schema = json.dumps(resolve_blueprint(blueprint).spec_json_schema(), indent=2)
    except BlueprintError as e:
        exit_err(f"~ {e}")

    if output:
        write_to_file(output, schema + "\n")
        out(f"+ {output}", fg="green")
    else:
        out(schema)


# register commands
load_command = cli.command("load")(load)
build_command = cli.command("build")(build)
dev_command = cli.command("dev")(dev)
info_command = cli.command("info")(info)
init_command = cli.command("init")(init)
list_command = cli.command("list")(cliffy_list)
render_command = cli.command("render")(render)
remove_command = cli.command("remove")(remove)
remove_all_command = cli.command("remove-all")(remove_all)
run_command = cli.command("run")(cliffy_run)
update_command = cli.command("update")(update)
test_command = cli.command("test")(test)
validate_command = cli.command("validate")(validate)
docs_command = cli.command("docs")(docs)
cli.add_command(ai)
cli.add_command(blueprint_group)
blueprint_list_command = blueprint_group.command("list")(blueprint_list)
blueprint_schema_command = blueprint_group.command("schema")(blueprint_schema)

# register aliases
cli.command("add", hidden=True, epilog="Alias for load")(
    click.argument("manifests", type=click.File("rb"), nargs=-1)(blueprint_option(load))
)
cli.command("blueprints", hidden=True, epilog="Alias for blueprint list")(blueprint_list)
cli.command("ls", hidden=True, epilog="Alias for list")(cliffy_list)
cli.command("rm", hidden=True, epilog="Alias for remove")(click.argument("cli_names", type=str, nargs=-1)(remove))
cli.command("rm-all", hidden=True, epilog="Alias for remove-all")(remove_all)
cli.command("rmall", hidden=True, epilog="Alias for remove-all")(remove_all)
cli.command("reload", hidden=True, epilog="Alias for update")(click.argument("cli_names", type=str, nargs=-1)(update))
