## Generated db on 2025-01-21 22:35:01.728607
import subprocess
import typer
from typing import Optional, Any
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

def aliases_callback(value: bool):
    if value:
        print("""
Command      Aliases
--------     --------
create       mk
delete       rm
list         ls
view         v
""")
        raise typer.Exit()

@cli.callback()
def main(
    aliases: Optional[bool] = typer.Option(None, '--aliases', callback=aliases_callback, is_eager=True),
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass


def create(name: str = typer.Option(..., prompt="What is the name of the database?", confirmation_prompt=True)):
    console.print("Running pre-run hook", style="green")
    """Create a new database"""
    console.print(f"Creating database {name}", style="green")


cli.command("create", help="",)(create)

cli.command("mk", hidden=True, epilog="Alias for create")(create)

def delete(name: str = typer.Option(..., prompt="What is the name of the database?", confirmation_prompt=True)):
    """Delete a database"""
    sure = typer.confirm("Are you really really really sure?")
    if sure:
        console.print(f"Deleting database {name}", style="red")
    else:
        console.print(f"Back to safety!", style="green")


cli.command("delete", help="",)(delete)

cli.command("rm", hidden=True, epilog="Alias for delete")(delete)

def list():
    """List databases"""
    print("Listing all databases")


cli.command("list", help="",)(list)

cli.command("ls", hidden=True, epilog="Alias for list")(list)

def view(name: str = typer.Option(..., prompt="What is the name of the database?", confirmation_prompt=True), table: str = typer.Option(..., prompt="What is the name of the table?")):
    """View database table"""
    console.print(f"Viewing {table} table for {name} DB")


cli.command("view", help="",)(view)

cli.command("v", hidden=True, epilog="Alias for view")(view)

if __name__ == "__main__":
    cli()
