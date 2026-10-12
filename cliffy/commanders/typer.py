import datetime

from cliffy.commander import BaseGroup, Commander
from cliffy.helper import clean_help, py_str
from cliffy.manifest import Callback, CLIManifest, Command


class TyperCommander(Commander):
    """Generates commands based on the command config"""

    def __init__(self, manifest: CLIManifest) -> None:
        super().__init__(manifest)
        self.base_imports.add("import subprocess")
        self.base_imports.add("import typer")
        self.base_imports.add("from typing import Optional, Any")

    def add_base_imports(self) -> None:
        self.cli = f"""## Generated {self.manifest.name} on {datetime.datetime.now()}\n"""
        # sorted: a set has no stable order, which made the generated code differ from run to run
        for imp in sorted(self.base_imports):
            self.cli += imp + "\n"

    def add_base_cli(self) -> None:
        self.cli += """
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS"""
        if self.manifest.cli_options:
            self.cli += f",{self.parser.to_args(self.manifest.cli_options)}"
        if self.manifest.help:
            self.cli += f", help={py_str(self.manifest.help)}"
        self.cli += f""")
__version__ = {py_str(self.manifest.version)}
__cli_name__ = {py_str(self.manifest.name)}

"""

        self.cli += """
def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()
"""

        if self.aliases_by_commands:
            self.cli += f"""
def aliases_callback(value: bool):
    if value:
        print({py_str(self.aliases_table())})
        raise typer.Exit()
"""
        callbacks = self.callbacks_for()
        self.functions["main"] = "callbacks"
        self.cli += f"""
@cli.callback({self.parse_callback_options(callbacks)})
def main({self.parse_callback_params(callbacks)}"""
        if self.aliases_by_commands:
            self.cli += """
    aliases: Optional[bool] = typer.Option(None, '--aliases', callback=aliases_callback, is_eager=True),"""

        self.cli += """
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
"""
        self.cli += self.parse_callback_run(callbacks) + "\n"

    def parse_callback_options(self, callbacks: list[Callback]) -> str:
        return "invoke_without_command=True" if any(cb.invoke_without_command for cb in callbacks) else ""

    def parse_callback_params(self, callbacks: list[Callback]) -> str:
        """Signature lines for a callback function: the context first, then the params of each callback."""
        if not callbacks:
            return ""

        signature = "\n    ctx: typer.Context,"
        for callback in callbacks:
            for param in callback.params:
                signature += f"\n    {self.parser.parse_param(param).strip().rstrip(',')},"
        return signature

    def parse_callback_run(self, callbacks: list[Callback]) -> str:
        return "".join(self.parser.parse_run_block(callback.run) for callback in callbacks) or "    pass\n"

    def add_root_command(self, command: Command) -> None:
        """
        Add a root command to the CLI application with optional aliases.

        Args:
            command (Command): The command configuration to be added as a root command.
        """
        if not command.run:
            return

        parsed_command_func_name = self.command_func_name(command)
        parsed_command_name = self.parser.get_parsed_command_name(command)
        parsed_command_config = self.parser.get_parsed_config(command)
        parsed_help = clean_help(command.help)
        empty_or_help = f"help={py_str(parsed_help)}," if parsed_help else ""
        command_args = f"{py_str(parsed_command_name)}, {empty_or_help}{parsed_command_config}"
        alias_epilog = py_str(f"Alias for {parsed_command_name}")

        self.cli += f"""
def {parsed_command_func_name}({self.parser.parse_params(command)}):
{self.parser.parse_command_run(command)}

cli.command({command_args})({parsed_command_func_name})
"""

        for alias in command.aliases:
            self.cli += f"""
cli.command({py_str(alias)}, hidden=True, epilog={alias_epilog})({parsed_command_func_name})
"""

    def define_groups(self) -> None:
        for group in self.groups.values():
            parsed_help = clean_help(group.help)
            empty_or_help = f"help={py_str(parsed_help)}," if parsed_help else ""
            self.cli += f"""{group.var_name} = typer.Typer({empty_or_help})
"""
            if callbacks := self.callbacks_for(group):
                callback_name = self.unique_name(f"{group.var_name}_callback", source=f"callbacks (group {group.name})")
                self.cli += f"""
@{group.var_name}.callback({self.parse_callback_options(callbacks)})
def {callback_name}({self.parse_callback_params(callbacks)}
):
{self.parse_callback_run(callbacks)}
"""

    def add_group(self, group: BaseGroup) -> None:
        """Add a group to the CLI with proper nesting"""
        parent_group = group.parent_group.var_name if group.parent_group else "cli"
        parsed_help = clean_help(group.help)
        group_args = f"name={py_str(group.short_name)}, help={py_str(parsed_help)}"
        self.cli += f"""{parent_group}.add_typer({group.var_name}, {group_args})
"""

    def add_sub_command(self, command: Command, group: BaseGroup) -> None:
        """Add a sub-command to a group"""
        if not command.run:
            # a script-less command only carries the help of the group with the same name
            return

        parsed_command_func_name = self.command_func_name(command)
        parsed_command_name = self.parser.get_parsed_command_name(command)
        parsed_command_config = self.parser.get_parsed_config(command)
        parsed_help = clean_help(command.help)
        empty_or_help = f"help={py_str(parsed_help)}," if parsed_help else ""
        command_args = f"{py_str(parsed_command_name)}, {empty_or_help}{parsed_command_config}"
        alias_epilog = py_str(f"Alias for {parsed_command_name}")

        self.cli += f"""
def {parsed_command_func_name}({self.parser.parse_params(command)}):
{self.parser.parse_command_run(command)}

{group.var_name}.command({command_args})({parsed_command_func_name})
"""

        for alias in command.aliases:
            self.cli += f"""
{group.var_name}.command({py_str(alias)}, hidden=True, epilog={alias_epilog})({parsed_command_func_name})
"""

    def add_main_block(self) -> None:
        self.cli += """
if __name__ == "__main__":
    cli()
"""
