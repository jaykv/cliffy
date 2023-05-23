## Generated environ on 2023-05-22 18:03:15.020633
import typer
import subprocess
from typing import Optional
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="Environment variable reader")
__version__ = '0.1.0'
__cli_name__ = 'environ'

def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
    pass



@cli.command("test")
def test():
    subprocess.run(["echo","hello"])



if __name__ == "__main__":
    cli()
