## Generated hello on 2023-04-16 23:26:47.594975
import typer
import subprocess
from typing import Optional

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


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


@cli.command("bash")
def bash():
    subprocess.run(["echo", "hello from bash"])


@cli.command("python")
def python():
    print("hello from python")
