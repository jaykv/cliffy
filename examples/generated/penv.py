## Generated penv on 2024-08-07 10:34:35.569851
import typer
import subprocess
from typing import Optional, Any
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
__cli_name__ = 'penv'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass

def get_venv_path(name: str) -> str:
    return f"{DEFAULT_VENV_STORE}{name}"

def venv_exists(name: str) -> bool:
    return os.path.exists(get_venv_path(name))



def ls():
    """
    List venvs in the store
    """
    subprocess.run(["ls",f"""{DEFAULT_VENV_STORE}"""])


cli.command("ls")(ls)

def rm(name: str = typer.Argument(...)):
    """
    Remove a venv
    """
    rmtree(get_venv_path(name))


cli.command("rm")(rm)

def go(name: str = typer.Argument(...), interpreter: str = typer.Option("python", "--interpreter", "-i")):
    """
    Activate a venv
    """
    if venv_exists(name):
        print(f"~ sourcing {name}")
    else:
        print(f"~ creating {name}")
        subprocess.run([f"""{interpreter}""","-m","venv",f"""{os.path.join(DEFAULT_VENV_STORE, name)}"""])
    
    os.system(f"""bash -c ". {get_venv_path(name)}/bin/activate; env PS1='\[\e[38;5;211m\]({name})\[\e[\033[00m\] \w $ ' bash --norc\"""")


cli.command("go")(go)

if __name__ == "__main__":
    cli()
