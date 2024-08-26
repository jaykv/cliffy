## Generated hello on 2024-08-25 23:31:48.022732
import typer
import subprocess
from typing import Optional, Any

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="""Hello world!""")
__version__ = '0.1.0'
__cli_name__ = 'hello'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass


def bash():
    subprocess.run(["echo","hello from bash"])


cli.command("bash")(bash)

def python():
    print("hello from python")


cli.command("python")(python)

if __name__ == "__main__":
    cli()
