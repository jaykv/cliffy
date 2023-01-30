import pybash

pybash.add_hook()


def run():
    from .cli import cli

    cli()
