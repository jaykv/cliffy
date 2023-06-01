## CLI to generate CLIs
import contextlib
from tempfile import NamedTemporaryFile
from typing import TextIO

try:
    import rich_click as click  # type: ignore
    from rich.console import Console  # type: ignore
    from rich_click.rich_group import RichGroup as AliasGroup  # type: ignore
except ImportError:
    import click
    from .rich import Console
    from click import Group as AliasGroup

from .builder import build_cli, run_cli
from .helper import CLIFFY_CLI_DIR, age_datetime, exit_err, indent_block, out, out_err, print_rich_table, write_to_file
from .homer import get_clis, get_metadata, get_metadata_path, remove_metadata, save_metadata
from .loader import Loader
from .manifests import Manifest, set_manifest_version
from .transformer import Transformer

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class AliasedGroup(AliasGroup):  # type: ignore
    def get_command(self, ctx, cmd_name):
        with contextlib.suppress(KeyError):
            cmd_name = ALIASES[cmd_name].name
        return super().get_command(ctx, cmd_name or "")


@click.group(context_settings=CONTEXT_SETTINGS, cls=AliasedGroup)
@click.version_option()
def cli() -> None:
    pass


@cli.command()
@click.argument("manifests", type=click.File("rb"), nargs=-1)
def load(manifests: list[TextIO]) -> None:
    """Load CLI for given manifest(s)"""
    for manifest in manifests:
        T = Transformer(manifest)
        Loader.load_from_cli(T.cli)
        save_metadata(manifest.name, T.cli)
        out(f"✨ Generated {T.cli.name} CLI v{T.cli.version} ✨", fg="green")
        out("$", fg="magenta", nl=False)
        out(f" {T.cli.name} -h")


@cli.command()
@click.argument("cli_names", type=str, nargs=-1)
def update(cli_names: list[str]) -> None:
    """Reloads CLI by name"""
    for cli_name in cli_names:
        if cli_metadata := get_metadata(cli_name):
            T = Transformer(open(cli_metadata.runner_path, "r"))
            Loader.load_from_cli(T.cli)
            save_metadata(cli_metadata.runner_path, T.cli)
            out(f"✨ Reloaded {T.cli.name} CLI v{T.cli.version} ✨", fg="green")
            out("$", fg="magenta", nl=False)
            out(f" {T.cli.name} -h")
        else:
            out_err(f"~ {cli_name} not found")


@cli.command()
@click.argument("manifest", type=click.File("rb"))
def render(manifest: TextIO) -> None:
    """Render the CLI manifest generation as code"""
    T = Transformer(manifest)
    console = Console()
    console.print(T.cli.code, overflow="fold", emoji=False, markup=False)
    out(f"# Rendered {T.cli.name} CLI v{T.cli.version} ~", fg="green")


@cli.command("run")
@click.argument("manifest", type=click.File("rb"))
@click.argument("cli_args", type=str, nargs=-1)
def cliffy_run(manifest: TextIO, cli_args: tuple[str]) -> None:
    """Run CLI for a manifest"""
    T = Transformer(manifest)
    run_cli(T.cli.name, T.cli.code, cli_args)


@cli.command()
@click.argument("cli_name", type=str, default="cliffy")
@click.option("--version", "-v", type=str, show_default=True, default="v1", help="Manifest version")
@click.option("--render", is_flag=True, show_default=True, default=False, help="Render template to terminal directly")
@click.option(
    "--raw",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Raw template without boilerplate helpers and examples.",
)
def init(cli_name: str, version: str, render: bool, raw: bool) -> None:
    """Generate a CLI manifest template"""
    set_manifest_version(version)
    template = Manifest.get_raw_template(cli_name) if raw else Manifest.get_template(cli_name)

    if render:
        console = Console()
        console.print(template, overflow="fold", emoji=False, markup=False)
    else:
        try:
            write_to_file(f"{cli_name}.yaml", text=template)
        except Exception as e:
            exit_err(f"~ error writing to file: {e}")
        out(f"+ {cli_name}.yaml", fg="green")


@cli.command("list")
def cliffy_list() -> None:
    "List all CLIs loaded"
    cols = ["Name", "Version", "Age", "Manifest"]
    rows = [
        [metadata.cli_name, metadata.version, age_datetime(metadata.loaded), metadata.runner_path]
        for metadata in get_clis()
    ]
    print_rich_table(cols, rows, styles=["cyan", "magenta", "green", "blue"])


@cli.command()
@click.argument("cli_names", type=str, nargs=-1)
def remove(cli_names: list[str]) -> None:
    "Remove a loaded CLI by name"
    for cli_name in cli_names:
        if get_metadata_path(cli_name):
            remove_metadata(cli_name)
            Loader.unload_cli(cli_name)
            out(f"~ {cli_name} removed 💥", fg="green")
        else:
            out_err(f"~ {cli_name} not loaded")


@cli.command()
@click.argument("cli_names", type=str, nargs=-1)
@click.option("--debug", is_flag=True, show_default=True, default=False, help="Display build output")
@click.option("--output-dir", "-o", type=click.Path(file_okay=False, dir_okay=True, writable=True), help="Output dir")
def bundle(cli_names: list[str], debug: bool, output_dir: str) -> None:
    "Bundle a loaded CLI into a zipapp"
    for cli_name in cli_names:
        if not (metadata := get_metadata(cli_name)):
            out_err(f"~ {cli_name} not loaded")
            continue

        result = build_cli(
            cli_name, script_path=f"{CLIFFY_CLI_DIR}/{cli_name}.py", deps=metadata.requires, output_dir=output_dir
        )

        if result.exit_code != 0:
            out(result.stdout)
            out_err(f"~ {cli_name} bundle failed")
            continue

        if debug:
            out(result.stdout)
        out(f"+ {cli_name} bundled 📦", fg="green")


@cli.command()
@click.argument("manifests", type=click.File("rb"), nargs=-1)
@click.option("--debug", is_flag=True, show_default=True, default=False, help="Display build output")
@click.option("--output-dir", "-o", type=click.Path(file_okay=False, dir_okay=True, writable=True), help="Output dir")
def build(manifests: list[TextIO], debug: bool, output_dir: str) -> None:
    "Build a CLI manifest into a zipapp"
    for manifest in manifests:
        T = Transformer(manifest, validate_requires=False)
        with NamedTemporaryFile(mode="w", prefix=f"{T.cli.name}_", suffix=".py", delete=True) as script:
            script.write(T.cli.code)
            script.flush()
            result = build_cli(T.cli.name, script_path=script.name, deps=T.cli.requires, output_dir=output_dir)

        if result.exit_code != 0:
            out(result.stdout)
            out_err(f"~ {T.cli.name} build failed")
            continue

        if debug:
            out(result.stdout)
        out(f"+ {T.cli.name} built 📦", fg="green")


@cli.command()
@click.argument("cli_name", type=str)
def info(cli_name: str):
    "Display CLI info"
    metadata = get_metadata(cli_name) or exit_err(f"~ {cli_name} not loaded")
    out(f"{click.style('name:', fg='blue')} {metadata.cli_name}")
    out(f"{click.style('version:', fg='blue')} {metadata.version}")
    out(f"{click.style('requires:', fg='blue')} {metadata.requires}")
    out(f"{click.style('age:', fg='blue')} {age_datetime(metadata.loaded)} ({metadata.loaded.ctime()})")
    out(f"{click.style('manifest:', fg='blue')}\n{indent_block(metadata.manifest, spaces=2)}")


ALIASES = {
    "add": load,
    "rm": remove,
    "ls": cliffy_list,
}
