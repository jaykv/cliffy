import ast
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
        self.cli = self.header()
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
@cli.command(name={py_str(parsed_command_name)}{self.click_parser.get_parsed_config(command)})
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
        if not command.run:
            # a script-less command only carries the help of the group with the same name
            return

        parsed_command_func_name = self.command_func_name(command)
        parsed_command_name = self.click_parser.get_parsed_command_name(command)
        parsed_help = clean_help(command.help)

        self.cli += f"""
@{group.var_name}.command(name={py_str(parsed_command_name)}{self.click_parser.get_parsed_config(command)})
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
        return "\n".join(self.parse_param(param) for param in params)

    def parse_param(self, param: ParamBlock) -> str:  # type: ignore[override]
        """Parse one param into a Click decorator"""
        if isinstance(param, GenericCommandParam):
            decorator = param.root.strip()
            if not decorator.startswith("@"):
                raise ValueError(
                    f"param `{decorator}` is a function signature entry, which only the Typer backend can use. "
                    "With `use_click: true` a string param has to be a Click decorator, "
                    "i.e. \"@click.option('--name', ...)\"."
                )
            return decorator

        if isinstance(param, SimpleCommandParam):
            if "typer." in param.raw_type:
                raise ValueError(
                    f"param `{param.name}` is a Typer definition (`{param.raw_type.strip()}`), which the Click "
                    "backend cannot use. Write it as a Click decorator string, "
                    "i.e. \"@click.option('--name', ...)\", or remove `use_click`."
                )
            default, required, help_text = param.default, param.required, ""
        else:
            default, required, help_text = param.default, param.required, param.help
            if default is not None:
                default = str(default)

        param_type = param.type.strip()
        if param_type in self.manifest.types:
            definition = self.manifest.types[param_type].strip()
            if definition.startswith("@click."):
                # a complete Click decorator: used as written, like a Typer definition is for the Typer backend
                return definition
            if "typer." in definition:
                raise ValueError(
                    f"param `{param.name}` uses types.{param_type}, which is a Typer definition (`{definition}`). "
                    f"With `use_click: true` a type is a plain type such as `{param_type}: int`, or a Click decorator "
                    f"such as `{param_type}: \"@click.option('--name', ...)\"`."
                )
            # `N: int = 5` names a type and a default. A default on the param itself wins.
            param_type, _, type_default = (part.strip() for part in definition.partition("="))
            if default is None and type_default:
                default = type_default

        click_type, multiple = self._click_type(param_type)
        if default is not None:
            if isinstance(param, CommandParam):
                # a str default of an explicit param is data, not an expression: emit it as a string literal
                default = repr(default) if click_type == "str" else default
            else:
                default = self._simple_default(click_type, default)

        self.normalize_param_name(param.name)  # validates
        if param.is_option():
            parts = self._option_declarations(param.name, param.short, click_type)
            if click_type and click_type != "bool":
                parts.append(f"type={click_type}")
            if multiple:
                parts.append("multiple=True")
            if required:
                parts.append("required=True")
            if default is not None:
                parts.append(f"default={default}")
            if help_text:
                parts.append(f"help={help_text!r}")
            return f"@click.option({', '.join(parts)})"

        parts = [repr(param.name.strip())]
        if click_type:
            parts.append(f"type={click_type}")
        if multiple:
            parts.append("nargs=-1")
            if required:
                parts.append("required=True")
        elif not required and default is None:
            # an argument is optional unless it is marked with `!` or `required`, as in Typer
            parts.append("required=False")
        if default is not None:
            parts.append(f"default={default}")
        if help_text:
            parts.append(f"help={help_text!r}")
        return f"@click.argument({', '.join(parts)})"

    OPTIONAL_TYPE = re.compile(r"(?:typing\.)?Optional\[(.+)\]|(.+?)\s*\|\s*None|None\s*\|\s*(.+)")
    LIST_TYPE = re.compile(r"(?:typing\.)?[Ll]ist\[(.+)\]")

    def _click_type(self, param_type: str) -> tuple[str, bool]:
        """Annotation -> (Click type, takes several values). Optional[int] -> int, list[str] -> str, several."""
        click_type = param_type.strip()
        if match := self.OPTIONAL_TYPE.fullmatch(click_type):
            click_type = next(group for group in match.groups() if group).strip()
        multiple = False
        if match := self.LIST_TYPE.fullmatch(click_type):
            click_type, multiple = match.group(1).strip(), True
        if click_type in ("Any", "typing.Any"):
            click_type = ""
        return click_type, multiple

    def _option_declarations(self, name: str, short: str | None, param_type: str) -> list[str]:
        """--dry-run with short d -> ['--dry-run', '-d']. A bool is a `--flag/--no-flag` switch, like in Typer."""
        long_name = name.strip().lstrip("-")
        declaration = f"--{long_name}/--no-{long_name}" if param_type == "bool" else f"--{long_name}"
        declarations = [repr(declaration)]
        if short and short.strip():
            declarations.append(repr("-" + short.strip().lstrip("-")))
        return declarations

    def _parse_simple_param(self, param: SimpleCommandParam) -> str:
        """Parse SimpleCommandParam into Click decorator"""
        return self.parse_param(param)

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

    def get_parsed_config(self, command: Command) -> str:
        """Command `config` as keyword arguments of Click's `command()`, with a leading comma when there are any."""
        if not command.config:
            return ""

        configured_options = command.config.model_dump(exclude_unset=True)
        if "rich_help_panel" in configured_options:
            # rich-click calls the panel a command is listed under `panel`
            configured_options["panel"] = configured_options.pop("rich_help_panel")
        return f",{self.to_args(configured_options)}" if configured_options else ""

    def get_alias_func_name(self, command_func_name: str, alias: str) -> str:
        """Function name for the copy of a command that is registered under an alias"""
        alias_suffix = re.sub(r"\W", "_", alias)
        return f"{command_func_name}_{alias_suffix}"
