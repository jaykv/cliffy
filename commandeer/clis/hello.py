## Generated hello on 2023-02-05 13:24:00.300389
import typer; import subprocess; CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help']);
from typing import Optional;
        
cli = typer.Typer(context_settings=CONTEXT_SETTINGS)

__version__ = '0.1.0'
__cli_name__ = 'hello'

def version_callback(value: bool):
    if value:
        print(__cli_name__ + ", " + __version__)
        raise typer.Exit()

@cli.callback()
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
    pass

@cli.command()
def bash():
    """Help for bash"""
    subprocess.run(["echo","hello from bash"])


@cli.command()
def python():
    """Help for python"""
    print("hello from python")
