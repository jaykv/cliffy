import datetime
from collections import namedtuple

from .parser import Parser

Command = namedtuple('Command', ['name', 'script'])
CLI = namedtuple('CLI', ['name', 'version', 'code'])


class Commander:
    """Generates commands based on the command config"""

    def __init__(self, command_config: dict) -> None:
        self.command_config = command_config
        self.parser = Parser(command_config)
        self.cli = f"""## Generated {self.command_config['name']} on {datetime.datetime.now()}

import rich_click as click; import subprocess; CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help']);
        """

    def build_cli(self):
        self.add_base_cli()
        commands = self.command_config["commands"]
        for name, script in commands.items():
            current_command = Command(name, script)
            if '.' in name:
                group = name.split('.')[:-2]
                self.add_sub_command(current_command, group)
            else:
                self.add_group_command(current_command)

    def add_base_cli(self):
        self.cli += f"""
@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option('{self.command_config['version']}')
def cli():
    pass
"""

    def add_group_command(self, command: Command):
        self.cli += f"""
@cli.command()
def {command.name}():
    \"\"\"Help for {command.name}\"\"\"
    {self.parser.parse(command.script)}
"""

    def add_sub_command(self, command: Command, group: str):
        self.cli += f"""
@{group}.command()
def {command.name}():
    \"\"\"Help for {command.name}\"\"\"
    {self.parser.parse(command.script)}
"""


def build_cli(command_config: dict) -> CLI:
    commander = Commander(command_config)
    commander.build_cli()
    return CLI(command_config['name'], command_config['version'], commander.cli)
