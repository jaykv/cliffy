## Generated pydev on 2023-02-27 17:53:19.380001
import typer; import subprocess; from typing import Optional;
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help']);
import sys
import subprocess

cli = typer.Typer(context_settings=CONTEXT_SETTINGS)

__version__ = '0.1.0'
__cli_name__ = 'pydev'

def version_callback(value: bool):
    if value:
        print(__cli_name__ + ", " + __version__)
        raise typer.Exit()

@cli.callback()
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
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


@cli.command("clean")
def clean():
    """Clean pycache artifacts"""
    subprocess.run(["find",".","-type","f","-name","*.pyc","-delete"])
    subprocess.run(["find",".","-type","d","-name","__pycache__","-delete"])
    subprocess.run(["echo","Cleaned!"])



@cli.command("format")
def format():
    """Format code with black"""
    subprocess.run(["black","."])
    subprocess.run(["echo","Formatted!"])



@cli.command("lint")
def lint():
    """Run linters on the code"""
    print(run_cmd('flake8 .'))
    print(run_cmd('black --check .'))
    print(run_cmd('mypy .'))
    print("Linting successful!")
    



@cli.command("test")
def test():
    """Run tests"""
    print(run_cmd('pytest'))
    print("Tests passed!")
    



@cli.command("bump")
def bump(major: int = typer.Option(..., help="Version part", min=0), minor: int = typer.Option(..., help="Version part", min=0), patch: int = typer.Option(..., help="Version part", min=0)):
    """Bump the package version"""
    current_version = run_cmd('python setup.py --version')
    print(f"Current version: {current_version}")
    parts = current_version.split('.')
    new_version = '.'.join(parts[:-1] + [str(int(parts[-1]) + 1)])
    print(f"New version: {new_version}")
    with open('setup.py', 'r') as f:
        contents = f.read()
    contents = contents.replace(current_version, new_version)
    with open('setup.py', 'w') as f:
        f.write(contents)
    print(f"Bumped version from {current_version} to {new_version}.")
    


