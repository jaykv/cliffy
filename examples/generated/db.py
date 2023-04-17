## Generated db on 2023-04-16 23:26:47.592785
import typer; import subprocess; from typing import Optional;
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help']);
from rich.console import Console
console = Console()


cli = typer.Typer(context_settings=CONTEXT_SETTINGS, add_completion=False, help="Database CLI")
__version__ = '0.1.0'
__cli_name__ = 'db'

def version_callback(value: bool):
    if value:
        print(__cli_name__ + ", " + __version__)
        raise typer.Exit()

@cli.callback()
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
    pass



@cli.command("create")
def create(name: str = typer.Option(..., prompt="What is the name of the database?", confirmation_prompt=True)):
    """Create a new database"""
    console.print(f"Creating database {name}", style="green")
    



@cli.command("delete")
def delete(name: str = typer.Option(..., prompt="What is the name of the database?", confirmation_prompt=True)):
    """Delete a database"""
    sure = typer.confirm("Are you really really really sure?")
    if sure:
        console.print(f"Deleting database {name}", style="red")
    else:
        console.print(f"Back to safety!", style="green")
    



@cli.command("list")
def list():
    """List databases"""
    print(f"Listing all databases")
    


