## CLI to generate CLIs
import rich_click as click
from rich.console import Console
from rich.syntax import Syntax

from .transformer import Transformer

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def cli():
    pass


@cli.command()
@click.argument('manifest', type=click.File('rb'))
def load(manifest):
    """Dynamically generate CLI with a given manifest"""
    cli = Transformer(manifest).load_cli()
    click.secho(f"~ Generated {cli.name} CLI v{cli.version} ~", fg="green")
    click.secho(click.style("$", fg="magenta"), nl=False)
    click.echo(f" {cli.name} -h")


@cli.command()
@click.argument('manifest', type=click.File('rb'))
def render(manifest):
    """Display rendered CLI code with a given manifest"""
    cli = Transformer(manifest).render_cli()
    syntax = Syntax(cli.code, "python", theme="monokai", line_numbers=False)
    console = Console()
    console.print(syntax)
    click.secho(f"# Rendered {cli.name} CLI v{cli.version} ~", fg="green")
