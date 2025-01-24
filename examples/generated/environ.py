## Generated environ on 2025-01-24 13:22:43.893773
import subprocess
from typing import Optional, Any
import typer
import os

default_env_var = 'hello'


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="""Environment variable reader""")
__version__ = '0.1.0'
__cli_name__ = 'environ'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass


def read(env_var: str = typer.Argument(...)):
    subprocess.run(["echo",f"""{os.environ[env_var]}"""])


cli.command("read", )(read)

def hello():
    subprocess.run(["echo","hello"])


cli.command("hello", )(hello)

def bye():
    subprocess.run(["echo",f"""{os.environ['ENVIRON_BYE_TEXT']}"""])


cli.command("bye", )(bye)

def hello_bye():
    subprocess.run(["echo","hello","bye"])


cli.command("hello-bye", )(hello_bye)

if __name__ == "__main__":
    cli()
