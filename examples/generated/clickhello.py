## Generated clickhello with cliffy 0.7.0
from typing import Optional, Any
import rich_click as click
import subprocess

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

def show_aliases(ctx, param, value):
    if not value:
        return
    print("\nCommand     Aliases\n--------    --------\nhello       hl\n")
    ctx.exit()

@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option('0.1.0')
@click.option('--aliases', is_flag=True, callback=show_aliases, expose_value=False, is_eager=True,
    help='Show command aliases.')
def cli():
    "Hello World with Click!"
    pass


@cli.command(name="hello")

def hello():
    ""
    subprocess.run(["echo","world"])


@cli.command(name="hl", hidden=True)

def hello_hl():
    "Alias for hello"
    subprocess.run(["echo","world"])


if __name__ == "__main__":
    cli()
