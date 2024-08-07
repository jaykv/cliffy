import datetime

from ..commander import Command, Commander, Group
from ..manifests import Manifest


class TyperCommander(Commander):
    """Generates commands based on the command config"""

    def __init__(self, manifest: Manifest) -> None:
        super().__init__(manifest)
        self.base_imports.add("import typer")
        self.base_imports.add("import subprocess")
        self.base_imports.add("from typing import Optional, Any")

    def add_base_imports(self):
        self.cli = f"""## Generated {self.manifest.name} on {datetime.datetime.now()}\n"""
        for imp in self.base_imports:
            self.cli += imp + "\n"

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

"""

        self.cli += """
def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()
"""

        if self.aliases_by_commands:
            self.cli += """
def aliases_callback(value: bool):
    if value:
        print(\"\"\""""
            max_command_length = max(len(x) for x in self.aliases_by_commands.keys())
            self.cli += f"""
{"Command".ljust(max_command_length + 7)}Aliases
{"--------".ljust(max_command_length + 7)}--------
"""
            for command, alias_list in self.aliases_by_commands.items():
                self.cli += f"{command.ljust(max_command_length + 7)}"
                self.cli += ", ".join(alias_list)
                self.cli += "\n"
            self.cli += """\"\"\")
        raise typer.Exit()
"""
        self.cli += """
@cli.callback()
def main("""
        if self.aliases_by_commands:
            self.cli += """
    aliases: Optional[bool] = typer.Option(None, '--aliases', callback=aliases_callback, is_eager=True),"""

        self.cli += """
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass

"""

    def add_root_command(self, command: Command) -> None:
        parsed_command_func_name = self.parser.get_command_func_name(command)
        parsed_command_name = self.parser.get_parsed_command_name(command)
        self.cli += f"""
def {parsed_command_func_name}({self.parser.parse_args(command)}):
{self.parser.parse_command(command.script)}

cli.command("{parsed_command_name}")({parsed_command_func_name})
"""

        for alias in command.aliases:
            self.cli += f"""
cli.command("{alias}", hidden=True, epilog="Alias for {parsed_command_name}")({parsed_command_func_name})
"""

    def add_group(self, group: Group) -> None:
        self.cli += f"""{group.name}_app = typer.Typer()
cli.add_typer({group.name}_app, name="{group.name}", help="{group.help}")
"""

    def add_sub_command(self, command: Command, group: Group) -> None:
        parsed_command_func_name = self.parser.get_command_func_name(command)
        parsed_command_name = self.parser.get_parsed_command_name(command)
        self.cli += f"""
def {parsed_command_func_name}({self.parser.parse_args(command)}):
{self.parser.parse_command(command.script)}

{group.name}_app.command("{parsed_command_name}")({parsed_command_func_name})
"""

        for alias in command.aliases:
            self.cli += f"""
{group.name}_app.command("{alias}", hidden=True, epilog="Alias for {parsed_command_name}")({parsed_command_func_name})
"""

    def add_main_block(self) -> None:
        self.cli += """
if __name__ == "__main__":
    cli()
"""
