## CLI to generate CLIs
import rich_click as click
from rich.console import Console
from rich.syntax import Syntax

from .manifests import get_cli_manifest
from .transformer import Transformer, write_to_file

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def cli():
    pass


@cli.command()
@click.argument('manifests', type=click.File('rb'), nargs=-1)
def load(manifests):
    """Load CLI for given manifest(s)"""
    for manifest in manifests:
        cli = Transformer(manifest).load_cli()
        click.secho(f"~ Generated {cli.name} CLI v{cli.version} ~", fg="green")
        click.secho(click.style("$", fg="magenta"), nl=False)
        click.echo(f" {cli.name} -h")


@cli.command()
@click.argument('manifest', type=click.File('rb'))
def render(manifest):
    """Render the CLI manifest generation as code"""
    T = Transformer(manifest)
    T.render_cli()
    syntax = Syntax(T.cli.code, "python", theme="monokai", line_numbers=False)
    console = Console()
    console.print(syntax)
    click.secho(f"# Rendered {T.cli.name} CLI v{T.cli.version} ~", fg="green")


@cli.command()
@click.argument('cli_name', type=str)
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
def init(cli_name, version, render, raw):
    """Generate a CLI manifest template"""
    manifest = get_cli_manifest(version)
    if raw:
        template = manifest.get_raw_template(cli_name)
    else:
        template = manifest.get_template(cli_name)

    if render:
        syntax = Syntax(template, "yaml", theme="monokai", line_numbers=False)
        console = Console()
        console.print(syntax)
    else:
        write_to_file(f'{cli_name}.yaml', text=template)


@cli.command()
@click.argument('cli_name', type=str)
def enable(cli_name):
    click.echo("# TODO")


@cli.command()
@click.argument('cli_name', type=str)
def disable(cli_name):
    click.echo("# TODO")


@cli.command("list")
def list_clis():
    click.echo("# TODO")


@cli.command()
@click.argument('cli_name', type=str)
def unload(cli_name):
    click.echo("# TODO")
