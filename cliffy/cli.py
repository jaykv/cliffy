## CLI to generate CLIs
import contextlib
from typing import TextIO

try:
    import rich_click as click
    from rich.console import Console
    from rich.syntax import Syntax
    from rich_click.rich_group import RichGroup as AliasGroup
except ImportError:
    import click
    from .rich import Console, Syntax
    from click import Group as AliasGroup

from .helper import print_rich_table, write_to_file
from .homer import get_clis, get_metadata, get_metadata_path, remove_metadata, save_metadata
from .loader import Loader
from .manifests import Manifest, set_manifest_version
from .transformer import Transformer

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class AliasedGroup(AliasGroup):
    def get_command(self, ctx, cmd_name):
        with contextlib.suppress(KeyError):
            cmd_name = ALIASES[cmd_name].name
        return super().get_command(ctx, cmd_name or "")


@click.group(context_settings=CONTEXT_SETTINGS, cls=AliasedGroup)
@click.version_option()
def cli() -> None:
    pass


@cli.command()
@click.argument('manifests', type=click.File('rb'), nargs=-1)
def load(manifests: list[TextIO]) -> None:
    """Load CLI for given manifest(s)"""
    for manifest in manifests:
        T = Transformer(manifest)
        Loader.load_cli(T.cli)
        save_metadata(manifest.name, T.cli)
        click.secho(f"~ Generated {T.cli.name} CLI v{T.cli.version} ~", fg="green")
        click.secho(click.style("$", fg="magenta"), nl=False)
        click.echo(f" {T.cli.name} -h")


@cli.command()
@click.argument('cli_names', type=str, nargs=-1)
def update(cli_names: list[str]) -> None:
    """Reloads CLI by name"""
    for cli_name in cli_names:
        if cli_metadata := get_metadata(cli_name):
            T = Transformer(open(cli_metadata.runner_path, "r"))
            Loader.load_cli(T.cli)
            save_metadata(cli_metadata.runner_path, T.cli)
            click.secho(f"~ Reloaded {T.cli.name} CLI v{T.cli.version} ~", fg="green")
            click.secho(click.style("$", fg="magenta"), nl=False)
            click.echo(f" {T.cli.name} -h")
        else:
            click.secho(f"~ {cli_name} not found", fg="red")


@cli.command()
@click.argument('manifest', type=click.File('rb'))
def render(manifest: TextIO) -> None:
    """Render the CLI manifest generation as code"""
    T = Transformer(manifest)
    console = Console()
    console.print(T.cli.code, overflow="fold", emoji=False, markup=False)
    click.secho(f"# Rendered {T.cli.name} CLI v{T.cli.version} ~", fg="green")


@cli.command()
@click.argument('cli_name', type=str, default="cliffy")
@click.option('--version', '-v', type=str, show_default=True, default="v1", help="Manifest version")
@click.option(
    '--render', type=bool, is_flag=True, show_default=True, default=False, help="Render template to terminal directly"
)
@click.option(
    '--raw',
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
        syntax = Syntax(template, "yaml", theme="monokai", line_numbers=False)
        console = Console()
        console.print(syntax)
    else:
        write_to_file(f'{cli_name}.yaml', text=template)
        click.secho(f"+ {cli_name}.yaml", fg="green")


@cli.command("list")
def list_clis() -> None:
    "List all CLIs loaded"
    cols = ["Name", "Version", "Manifest"]
    rows = [[metadata.cli_name, metadata.version, metadata.runner_path] for metadata in get_clis()]
    print_rich_table(cols, rows, styles=["cyan", "magenta", "green"])


@cli.command()
@click.argument('cli_names', type=str, nargs=-1)
def remove(cli_names: list[str]) -> None:
    "Remove a loaded CLI by name"
    for cli_name in cli_names:
        if get_metadata_path(cli_name):
            remove_metadata(cli_name)
            Loader.unload_cli(cli_name)
            click.secho(f"~ {cli_name} unloaded", fg="green")
        else:
            click.secho(f"~ {cli_name} not found", fg="red")


ALIASES = {
    "rm": remove,
    "ls": list_clis,
}
