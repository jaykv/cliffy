## Generated pydev on 2024-08-25 23:31:48.031791
import typer
import subprocess
from typing import Optional, Any
import sys



CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="""Python developer utilities""")
__version__ = '0.1.0'
__cli_name__ = 'pydev'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass

def run_cmd(cmd: str):
    """Helper function to run a command."""
    try:
        result = subprocess.run(cmd, shell=True, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Exit code: {e.returncode}")
        print(f"Output: {e.output.decode('utf-8').strip()}")
        sys.exit(1)

    return result.stdout.decode('utf-8').strip()

def get_file_contents(file_name: str):
    with open(file_name, 'r') as f:
        contents = f.read()
    return contents

def write_to_file(file_name: str, contents: str):
    with open(file_name, 'w') as f:
        f.write(contents)



def clean():
    """
    Clean pycache artifacts
    """
    subprocess.run(["find",".","-type","f","-name","*.pyc","-delete"])
    subprocess.run(["find",".","-type","d","-name","__pycache__","-delete"])
    subprocess.run(["echo","Cleaned!"])


cli.command("clean")(clean)

def format():
    """
    Format code with black
    """
    subprocess.run(["black","."])
    subprocess.run(["echo","Formatted!"])


cli.command("format")(format)

def lint():
    """
    Run linters on the code
    """
    subprocess.run(["flake8","."])
    subprocess.run(["black","--check","."])
    subprocess.run(["mypy","."])
    print("Linting successful!")


cli.command("lint")(lint)

def test():
    """
    Run tests
    """
    subprocess.run(["pytest"])
    print("Tests passed!")


cli.command("test")(test)

def bump(major: int = typer.Option(..., help="Version part", min=0), minor: int = typer.Option(..., help="Version part", min=0), patch: int = typer.Option(..., help="Version part", min=0)):
    """
    Bump the package version
    """
    current_version = run_cmd("python setup.py --version")
    print(f"Current version: {current_version}")
    parts = current_version.split('.')
    new_version = '.'.join(parts[:-1] + [str(int(parts[-1]) + 1)])
    print(f"New version: {new_version}")
    contents = get_file_contents("setup.py")
    contents = contents.replace(current_version, new_version)
    write_to_file("setup.py", contents)
    print(f"Bumped version from {current_version} to {new_version}.")


cli.command("bump")(bump)

if __name__ == "__main__":
    cli()
