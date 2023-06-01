## Generated venv on 2023-06-01 00:21:03.541859
import typer
import subprocess
from typing import Optional
import os
from pathlib import Path
from shutil import rmtree


HOME_PATH = str(Path.home())
DEFAULT_VENV_STORE = f"{HOME_PATH}/venv-store/"


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="""~ Virtualenv store ~
Simplify virtualenvs
""")
__version__ = '0.1.0'
__cli_name__ = 'venv'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()


@cli.callback()
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
    pass

def get_venv_path(name: str) -> str:
    return f"{DEFAULT_VENV_STORE}{name}"

def venv_exists(name: str) -> bool:
    return os.path.exists(get_venv_path(name))



@cli.command("ls")
def ls():
    """
    List venvs in the store
    """
    subprocess.run(["ls","" + f"""{DEFAULT_VENV_STORE}""" + ""])
    


@cli.command("rm")
def rm(name: str = typer.Argument(...)):
    """
    Remove a venv
    """
    rmtree(get_venv_path(name))


@cli.command("go")
def go(name: str = typer.Argument(...), interpreter: str = typer.Option("python", "--interpreter", "-i")):
    """
    Activate a venv
    """
    if venv_exists(name):
        print(f"~ sourcing {name}")
    else:
        print(f"~ creating {name}")
        subprocess.run(["" + f"""{interpreter}""" + "","-m","venv","" + f"""{os.path.join(DEFAULT_VENV_STORE, name)}""" + ""])
    
    os.system(f'/bin/bash --rcfile {get_venv_path(name)}/bin/activate')


if __name__ == "__main__":
    cli()
