## CLI to generate CLIs
import rich_click as click

from .transformer import Transformer

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def cli():
    pass


@cli.command()
@click.argument('manifest', type=click.File('rb'))
def generate(manifest):
    """Dynamically generate CLI with a given manifest"""
    cli = Transformer(manifest).generate()
    click.secho(f"~ Generated {cli.name} CLI v{cli.version} ~", fg="green")
    click.secho(click.style("$", fg="magenta"), nl=False)
    click.echo(f" {cli.name} -h")
