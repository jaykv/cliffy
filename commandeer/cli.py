import rich_click as click

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def cli():
    pass


@cli.command()
@click.argument('manifest', type=click.File('rb'))
def generate(manifest):
    """Dynamically generate CLI with a given manifest"""
    print(f"generating cli with {manifest}")


def run():
    cli()
