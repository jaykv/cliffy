import ast
import datetime
import re

from cliffy.commander import BaseGroup, Commander
from cliffy.helper import clean_help, py_str
from cliffy.manifest import (
    Callback,
    CLIManifest,
    Command,
    CommandParam,
    GenericCommandParam,
    ParamBlock,
    SimpleCommandParam,
)
from cliffy.parser import Parser


class ClickCommander(Commander):
    """Generates commands based on the command config using Click framework"""

    def __init__(self, manifest: CLIManifest) -> None:
        super().__init__(manifest)
        self.base_imports.add("import subprocess")
        self.base_imports.add("import rich_click as click")
        self.base_imports.add("from typing import Optional, Any")
        self.click_parser = ClickParser(manifest)

    def add_base_imports(self) -> None:
        self.cli = f"""## Generated {self.manifest.name} on {datetime.datetime.now()}\n"""
        # sorted: a set has no stable order, which made the generated code differ from run to run
        for imp in sorted(self.base_imports):
            self.cli += imp + "\n"

    def add_base_cli(self) -> None:
        self.cli += """
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
"""
        if self.aliases_by_commands:
            self.cli += f"""
def show_aliases(ctx, param, value):
    if not value:
        return
    print({py_str(self.aliases_table())})
    ctx.exit()
"""
        callbacks = self.callbacks_for()
        self.functions["cli"] = "callbacks"
        self.cli += """
@click.group(context_settings=CONTEXT_SETTINGS"""
        if "invoke_without_command" not in self.manifest.cli_options:
            self.cli += self.parse_callback_options(callbacks, leading=", ")
        if self.manifest.cli_options:
            self.cli += f",{self.click_parser.to_args(self.manifest.cli_options)}"
        self.cli += f""")
@click.version_option({self.manifest.version!r})"""

        if self.aliases_by_commands:
            self.cli += """
@click.option('--aliases', is_flag=True, callback=show_aliases, expose_value=False, is_eager=True,
    help='Show command aliases.')"""
        self.cli += f"""{self.parse_callback_decorators(callbacks)}
def cli({self.parse_callback_param_names(callbacks)}):
    {py_str(self.manifest.help)}
{self.parse_callback_run(callbacks)}
"""

    def parse_callback_options(self, callbacks: list[Callback], leading: str = "") -> str:
        return f"{leading}invoke_without_command=True" if any(cb.invoke_without_command for cb in callbacks) else ""

    def parse_callback_decorators(self, callbacks: list[Callback]) -> str:
        """Decorators for a group function with callbacks: its params, then the context."""
        if not callbacks:
            return ""

        decorators = self.click_parser.parse_param_list(self.callback_params(callbacks))
        return ("\n" + decorators if decorators else "") + "\n@click.pass_context"

    def parse_callback_param_names(self, callbacks: list[Callback]) -> str:
        if not callbacks:
            return ""

        names = self.click_parser.get_param_list_names(self.callback_params(callbacks))
        return f"ctx, {names}" if names else "ctx"

    @staticmethod
    def callback_params(callbacks: list[Callback]) -> list[ParamBlock]:
        return [param for callback in callbacks for param in callback.params]

    def parse_callback_run(self, callbacks: list[Callback]) -> str:
        return "".join(self.click_parser.parse_run_block(callback.run) for callback in callbacks) or "    pass\n"

    def define_groups(self) -> None:
        for group in self.groups.values():
            parsed_help = clean_help(group.help)
            callbacks = self.callbacks_for(group)
            self.functions[group.var_name] = f"callbacks (group {group.name})"
            self.cli += f"""
@click.group({self.parse_callback_options(callbacks)}){self.parse_callback_decorators(callbacks)}
def {group.var_name}({self.parse_callback_param_names(callbacks)}):
    {py_str(parsed_help)}
{self.parse_callback_run(callbacks)}"""

    def add_group(self, group: BaseGroup) -> None:
        parent_var = group.parent_group.var_name if group.parent_group else "cli"
        self.cli += f"""
{parent_var}.add_command({group.var_name}, name={py_str(group.short_name)})
"""

    def add_root_command(self, command: Command) -> None:
        if not command.run:
            return

        parsed_command_func_name = self.command_func_name(command)
        parsed_command_name = self.click_parser.get_parsed_command_name(command)
        parsed_help = clean_help(command.help)

        self.cli += f"""
@cli.command(name={py_str(parsed_command_name)})
{self.click_parser.parse_params(command)}
def {parsed_command_func_name}({self.click_parser.get_param_names(command)}):
    {py_str(parsed_help)}
{self.click_parser.parse_command_run(command)}
"""

        for alias in command.aliases:
            self.cli += f"""
@cli.command(name={py_str(alias)}, hidden=True)
{self.click_parser.parse_params(command)}
def {self.alias_func_name(command, alias)}({self.click_parser.get_param_names(command)}):
    {py_str("Alias for " + parsed_command_name)}
{self.click_parser.parse_command_run(command)}
"""

    def add_sub_command(self, command: Command, group: BaseGroup) -> None:
        parsed_command_func_name = self.command_func_name(command)
        parsed_command_name = self.click_parser.get_parsed_command_name(command)
        parsed_help = clean_help(command.help)

        self.cli += f"""
@{group.var_name}.command(name={py_str(parsed_command_name)})
{self.click_parser.parse_params(command)}
def {parsed_command_func_name}({self.click_parser.get_param_names(command)}):
    {py_str(parsed_help)}
{self.click_parser.parse_command_run(command)}
"""

        for alias in command.aliases:
            self.cli += f"""
@{group.var_name}.command(name={py_str(alias)}, hidden=True)
{self.click_parser.parse_params(command)}
def {self.alias_func_name(command, alias)}({self.click_parser.get_param_names(command)}):
    {py_str("Alias for " + parsed_command_name)}
{self.click_parser.parse_command_run(command)}
"""

    def alias_func_name(self, command: Command, alias: str) -> str:
        """Name of the function that is registered under an alias: Click needs one function per command name."""
        return self.unique_name(
            self.click_parser.get_alias_func_name(self.command_func_name(command), alias),
            source=f"commands.{command.name}",
        )

    def add_main_block(self) -> None:
        self.cli += """
if __name__ == "__main__":
    cli()
"""


class ClickParser(Parser):
    """Parses manifest params into Click decorators. Everything else is shared with the Typer parser."""

    GENERIC_OPTION_REGEX = re.compile(r"@click\.option\(\s*['\"]--([\w-]+)")
    GENERIC_ARGUMENT_REGEX = re.compile(r"@click\.argument\(\s*['\"]([\w-]+)['\"]")

    def _combined_params(self, command: Command) -> list[ParamBlock]:
        return self.manifest.global_params + command.params

    def get_param_names(self, command: Command) -> str:
        """Get parameter names for the function definition of a command"""
        return self.get_param_list_names(self._combined_params(command))

    def get_param_list_names(self, params: list[ParamBlock]) -> str:
        """Get parameter names for the function that is decorated with these params"""
        names: list[str] = []
        for param in params:
            if isinstance(param, GenericCommandParam):
                # a raw decorator: the name can only be read back from its first declaration
                match = self.GENERIC_OPTION_REGEX.search(param.root) or self.GENERIC_ARGUMENT_REGEX.search(param.root)
                if match:
                    names.append(self.normalize_param_name(match.group(1)).lower())
            else:
                # Click lowercases the names it passes to the command function
                names.append(self.normalize_param_name(param.name).lower())

        return ", ".join(names)

    def parse_params(self, command: Command) -> str:
        """Parse the parameters of a command, global ones included, into Click decorators"""
        return self.parse_param_list(self._combined_params(command))

    def parse_param_list(self, params: list[ParamBlock]) -> str:
        """Parse a list of parameters into Click decorators"""
        decorators = []
        for param in params:
            if isinstance(param, GenericCommandParam):
                decorators.append(param.root.strip())
            elif isinstance(param, CommandParam):
                decorators.append(self._build_click_option(param))
            elif isinstance(param, SimpleCommandParam):
                decorators.append(self._parse_simple_param(param))

        return "\n".join(decorators)

    def _option_declarations(self, name: str, short: str | None, param_type: str) -> list[str]:
        """--dry-run with short d -> ['--dry-run', '-d']. A bool is a `--flag/--no-flag` switch, like in Typer."""
        self.normalize_param_name(name)  # validates
        long_name = name.strip().lstrip("-")
        declaration = f"--{long_name}/--no-{long_name}" if param_type == "bool" else f"--{long_name}"
        declarations = [repr(declaration)]
        if short and short.strip():
            declarations.append(repr("-" + short.strip().lstrip("-")))
        return declarations

    def _parse_simple_param(self, param: SimpleCommandParam) -> str:
        """Parse SimpleCommandParam into Click decorator"""
        param_type = param.type
        default_value = param.default

        if param.is_option():
            parts = self._option_declarations(param.name, param.short, param_type)
            if param_type and param_type != "bool":
                parts.append(f"type={param_type}")
            if param.required:
                parts.append("required=True")
            if default_value is not None:
                parts.append(f"default={self._simple_default(param_type, default_value)}")

            return f"@click.option({', '.join(parts)})"

        self.normalize_param_name(param.name)  # validates
        parts = [repr(param.name.strip())]
        if param_type:
            parts.append(f"type={param_type}")
        if default_value is not None:
            parts.append(f"default={self._simple_default(param_type, default_value)}")

        return f"@click.argument({', '.join(parts)})"

    @staticmethod
    def _simple_default(param_type: str, default_value: str) -> str:
        """A str default may be written bare (`str = World`) or as a literal (`str = "World"`); the rest is Python."""
        if param_type != "str":
            return default_value

        try:
            literal = ast.literal_eval(default_value)
        except (ValueError, SyntaxError):
            return repr(default_value)
        return repr(literal) if isinstance(literal, str) else repr(default_value)

    def _build_click_option(self, param: CommandParam) -> str:
        """Build Click option decorator from CommandParam"""
        parts = self._option_declarations(param.name, param.short, param.type)

        if param.type and param.type != "bool":
            parts.append(f"type={param.type}")

        if param.required:
            parts.append("required=True")

        if param.default is not None:
            # a str default is data, not an expression: emit it as a string literal
            parts.append(f"default={str(param.default)!r}" if param.type == "str" else f"default={param.default}")

        if param.help:
            parts.append(f"help={param.help!r}")

        return f"@click.option({', '.join(parts)})"

    def get_alias_func_name(self, command_func_name: str, alias: str) -> str:
        """Function name for the copy of a command that is registered under an alias"""
        alias_suffix = re.sub(r"\W", "_", alias)
        return f"{command_func_name}_{alias_suffix}"
