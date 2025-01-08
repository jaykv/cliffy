## Generated requires on 2025-01-07 20:58:01.905034
from typing import Optional, Any
import subprocess
import typer
import six


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS)
__version__ = '0.1.0'
__cli_name__ = 'requires'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass


def bash():
    subprocess.run(["echo","hello from bash"])


cli.command("bash")(bash)

def python():
    print("hello from python")


cli.command("python")(python)

def py():
    if six.PY2:
        print("python 2")
    if six.PY3:
        print("python 3")


cli.command("py")(py)

if __name__ == "__main__":
    cli()
