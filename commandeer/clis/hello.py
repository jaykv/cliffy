## Generated hello on 2023-01-29 22:36:05.236724

import rich_click as click
import subprocess

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option('0.1.0')
def cli():
    pass


@cli.command()
def bash():
    """Help for bash"""
    subprocess.run(["echo", "hello from bash"])


@cli.command()
def python():
    """Help for python"""
    print("hello from python")
