## CLI to generate CLIs
from typing import TextIO

import rich_click as click
from rich.console import Console
from rich.syntax import Syntax

from .helper import print_rich_table, write_to_file
from .homer import Homer
from .loader import Loader
from .manifests import get_cli_manifest
from .transformer import Transformer

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
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
        Homer.save_cli_metadata(manifest.name, T.cli)
        click.secho(f"~ Generated {T.cli.name} CLI v{T.cli.version} ~", fg="green")
        click.secho(click.style("$", fg="magenta"), nl=False)
        click.echo(f" {T.cli.name} -h")


@cli.command()
@click.argument('manifest', type=click.File('rb'))
def render(manifest: TextIO) -> None:
    """Render the CLI manifest generation as code"""
    T = Transformer(manifest)
    syntax = Syntax(T.cli.code, "python", theme="monokai", line_numbers=False)
    console = Console()
    console.print(syntax)
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
    manifest = get_cli_manifest(version)
    template = manifest.get_raw_template(cli_name) if raw else manifest.get_template(cli_name)

    if render:
        syntax = Syntax(template, "yaml", theme="monokai", line_numbers=False)
        console = Console()
        console.print(syntax)
    else:
        write_to_file(f'{cli_name}.yaml', text=template)


@cli.command("list")
def list_clis() -> None:
    "List of CLIs loaded"
    metadata_paths = Homer.get_cli_metadata_paths()
    cols = ["Name", "Version", "Manifest"]
    rows = []
    for path in metadata_paths:
        runnerpath, metadata = Homer.get_cli_metadata(path)
        rows.append([path.name, metadata.get("version", "error"), runnerpath])

    print_rich_table(cols, rows, styles=["cyan", "magenta", "green"])


@cli.command()
@click.argument('cli_names', type=str, nargs=-1)
def unload(cli_names: list[str]) -> None:
    "Remove a loaded CLI by name"
    for cli_name in cli_names:
        if Homer.is_cliffy_cli(cli_name):
            Homer.remove_cli_metadata(cli_name)
            Loader.unload_cli(cli_name)
            click.secho(f"~ {cli_name} unloaded", fg="green")
        else:
            click.secho(f"~ {cli_name} not found", fg="red")


@cli.command()
@click.argument('cli_name', type=str)
def enable(cli_name) -> None:
    click.echo("# TODO")


@cli.command()
@click.argument('cli_name', type=str)
def disable(cli_name) -> None:
    click.echo("# TODO")
