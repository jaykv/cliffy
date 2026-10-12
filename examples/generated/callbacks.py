## Generated callbacks with cliffy 0.7.1
from typing import Optional, Any
import subprocess
import typer

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="Callbacks run before the commands of a CLI or of a command group")
__version__ = "0.1.0"
__cli_name__ = "callbacks"


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print what is about to run"),
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    ctx.obj = {"verbose": verbose}
    if ctx.invoked_subcommand is None:
        print("no command given, try --help")
    elif verbose:
        print(f"running {ctx.invoked_subcommand}")

db_app = typer.Typer()

@db_app.callback()
def db_app_callback(
    ctx: typer.Context,
):
    print("connecting to db")


def hello():
    print("hello")


cli.command("hello", )(hello)
cli.add_typer(db_app, name="db", help="")

def db_migrate():
    print("migrating")


db_app.command("migrate", )(db_migrate)

def db_status():
    print("up to date")


db_app.command("status", )(db_status)

if __name__ == "__main__":
    cli()
