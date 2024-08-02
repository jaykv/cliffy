## Generated environ on 2024-08-02 13:49:30.829970
import typer
import subprocess
from typing import Optional
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
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
    pass


@cli.command("read")
def read(env_var: str = typer.Argument(...)):
    subprocess.run(["echo"])


@cli.command("hello")
def hello():
    subprocess.run(["echo","hello"])


@cli.command("bye")
def bye():
    subprocess.run(["echo",f"""{os.environ['ENVIRON_BYE_TEXT']}"""])


@cli.command("hello-bye")
def hello_bye():
    subprocess.run(["echo","hello"])
    subprocess.run(["echo","bye:",f"""{os.environ['ENVIRON_BYE_TEXT']}"""])


if __name__ == "__main__":
    cli()
