import datetime

from ..commander import Command, Commander, Group


class TyperCommander(Commander):
    """Generates commands based on the command config"""

    def add_base_imports(self):
        self.cli = f"""## Generated {self.manifest.name} on {datetime.datetime.now()}
import typer
import subprocess
from typing import Optional
"""

    def add_base_cli(self) -> None:
        self.cli += """
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS"""

        if self.manifest.cli_options:
            self.cli += f",{self.parser.to_args(self.manifest.cli_options)}"
        if self.manifest.help:
            self.cli += f', help="""{self.manifest.help}"""'

        self.cli += f""")
__version__ = '{self.manifest.version}'
__cli_name__ = '{self.manifest.name}'


def version_callback(value: bool):
    if value:
        print(f"{{__cli_name__}}, {{__version__}}")
        raise typer.Exit()


@cli.callback()
def main(version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)):
    pass

"""

    def add_root_command(self, command: Command) -> None:
        self.cli += f"""
@cli.command("{self.parser.get_parsed_command_name(command)}")
def {self.parser.get_command_func_name(command)}({self.parser.parse_args(command)}):
{self.parser.parse_command(command.script)}
"""

    def add_group(self, group: Group) -> None:
        self.cli += f"""{group.name}_app = typer.Typer()
cli.add_typer({group.name}_app, name="{group.name}", help="{group.help}")
"""

    def add_sub_command(self, command: Command, group: Group) -> None:
        self.cli += f"""
@{group.name}_app.command("{self.parser.get_parsed_command_name(command)}")
def {self.parser.get_command_func_name(command)}({self.parser.parse_args(command)}):
{self.parser.parse_command(command.script)}
"""

    def add_main_block(self) -> None:
        self.cli += """
if __name__ == "__main__":
    cli()
"""
