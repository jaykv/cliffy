import datetime

from ..commander import Command, Commander, Group


class TyperCommander(Commander):
    """Generates commands based on the command config"""

    def add_base_imports(self):
        self.cli = f"""## Generated {self.manifest.name} on {datetime.datetime.now()}\n"""
        for imp in self.base_imports:
            self.cli += imp + "\n"

    def add_base_cli(self) -> None:
        if self.command_aliases:
            self.cli += f"""BASE_ALIASES = {str(self.command_aliases)}
class BaseAliasGroup(TyperGroup):
    def get_command(self, ctx: Any, cmd_name: str) -> Optional[Any]:
        if cmd_name in BASE_ALIASES:
            return self.commands.get(BASE_ALIASES[cmd_name])

        return super().get_command(ctx, cmd_name)
"""

        self.cli += """
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS"""

        if self.manifest.cli_options:
            self.cli += f",{self.parser.to_args(self.manifest.cli_options)}"
        if self.manifest.help:
            self.cli += f', help="""{self.manifest.help}"""'
        if self.command_aliases:
            self.cli += ", cls=BaseAliasGroup"
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
        print(\"\"\"
"""
            for command, alias_list in self.aliases_by_commands.items():
                self.cli += f"{command}: "
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
        self.cli += f"""
@cli.command("{self.parser.get_parsed_command_name(command)}")
def {self.parser.get_command_func_name(command)}({self.parser.parse_args(command)}):
{self.parser.parse_command(command.script)}
"""

    def add_group(self, group: Group) -> None:
        if group.command_aliases:
            self.cli += f"""
{group.name.upper()}_ALIASES = {str(group.command_aliases)}
class {group.name.capitalize()}AliasGroup(TyperGroup):
    def get_command(self, ctx: Any, cmd_name: str) -> Optional[Any]:
        if cmd_name in {group.name.upper()}_ALIASES:
            return self.commands.get({group.name.upper()}_ALIASES[cmd_name])

        return super().get_command(ctx, cmd_name)

"""
        self.cli += f"{group.name}_app = typer.Typer("

        if group.command_aliases:
            self.cli += f"cls={group.name.capitalize()}AliasGroup"

        self.cli += f""")
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
