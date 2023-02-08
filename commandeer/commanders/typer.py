import datetime
from collections import defaultdict

from ..commander import Command, Commander


class TyperCommander(Commander):
    """Generates commands based on the command config"""

    def add_imports(self):
        self.cli = f"""## Generated {self.command_config['name']} on {datetime.datetime.now()}
import typer; import subprocess; from typing import Optional;
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help']);
        """

    def add_base_cli(self):
        self.groups = defaultdict(lambda: defaultdict())
        self.cli += f"""
cli = typer.Typer(context_settings=CONTEXT_SETTINGS)

__version__ = '{self.command_config['version']}'
__cli_name__ = '{self.command_config['name']}'

def version_callback(value: bool):
    if value:
        print(__cli_name__ + ", " + __version__)
        raise typer.Exit()

@cli.callback()
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
    pass
"""

    def add_group_command(self, command: Command):
        self.cli += f"""
@cli.command("{self.parser.get_parsed_command_name(command)}")
def {self.parser.get_command_func_name(command)}({self.parser.parse_args(command)}):
    \"\"\"Help for {command.name}\"\"\"
{self.parser.parse(command.script)}

"""

    def add_sub_command(self, command: Command, group: str):
        if group not in self.groups:
            self.cli += f"""{group}_app = typer.Typer(); cli.add_typer({group}_app, name="{group}");"""
            self.groups[group].update({command.name: command})
        else:
            self.groups[group][command.name] = command

        self.cli += f"""
@{group}_app.command("{self.parser.get_parsed_command_name(command)}")
def {self.parser.get_command_func_name(command)}({self.parser.parse_args(command)}):
    \"\"\"Help for {command.name}\"\"\"
{self.parser.parse(command.script)}

"""
