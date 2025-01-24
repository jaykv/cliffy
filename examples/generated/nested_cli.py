## Generated nested-cli on 2025-01-24 13:22:43.899895
import subprocess
from typing import Optional, Any
import typer

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="""Demo nested command structure""")
__version__ = '0.1.0'
__cli_name__ = 'nested-cli'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass

group1_app = typer.Typer()
group1_subgroup_app = typer.Typer()
group2_app = typer.Typer()

def command4():
    subprocess.run(["echo","bar"])


cli.command("command4", )(command4)
cli.add_typer(group1_app, name="group1", help="")
group1_app.add_typer(group1_subgroup_app, name="subgroup", help="")

def group1_subgroup_command1():
    subprocess.run(["echo","hello"])


group1_subgroup_app.command("command1", )(group1_subgroup_command1)

def group1_subgroup_command2():
    subprocess.run(["echo","world"])


group1_subgroup_app.command("command2", )(group1_subgroup_command2)
cli.add_typer(group2_app, name="group2", help="")

def group2_command3():
    subprocess.run(["echo","foo"])


group2_app.command("command3", )(group2_command3)

if __name__ == "__main__":
    cli()
