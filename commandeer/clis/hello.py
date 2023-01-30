## Generated hello on 2023-01-29 23:32:25.144228

import subprocess

import rich_click as click

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
