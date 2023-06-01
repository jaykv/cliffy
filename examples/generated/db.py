## Generated db on 2023-06-01 00:21:03.266082
import typer
import subprocess
from typing import Optional
from rich.console import Console
console = Console()



CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, add_completion=False, help="""Database CLI""")
__version__ = '0.1.0'
__cli_name__ = 'db'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
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
    print("Listing all databases")
    


@cli.command("view")
def view(name: str = typer.Option(..., prompt="What is the name of the database?", confirmation_prompt=True), table: str = typer.Option(..., prompt="What is the name of the table?")):
    """View database table"""
    console.print(f"Viewing {table} table for {name} DB")
    


if __name__ == "__main__":
    cli()
