import datetime
from typing import Union


from cliffy.commander import Commander, BaseGroup
from cliffy.manifest import Command


from pybash.transformer import transform as transform_bash

from cliffy.manifest import (
    CLIManifest,
    CommandParam,
    GenericCommandParam,
    RunBlock,
    RunBlockList,
    SimpleCommandParam,
)
import re


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
        for imp in self.base_imports:
            self.cli += imp + "\n"

    def add_base_cli(self) -> None:
        self.cli += """
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
"""
        if self.aliases_by_commands:
            self.cli += """
def show_aliases(ctx, param, value):
    if not value:
        return
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
    ctx.exit()
"""
        self.cli += """
@click.group(context_settings=CONTEXT_SETTINGS"""
        if self.manifest.cli_options:
            self.cli += f",{self.click_parser.to_args(self.manifest.cli_options)}"
        self.cli += f""")
@click.version_option('{self.manifest.version}')"""

        if self.aliases_by_commands:
            self.cli += """
@click.option('--aliases', is_flag=True, callback=show_aliases, expose_value=False, is_eager=True,
    help='Show command aliases.')"""
        self.cli += f"""
def cli():
    \"\"\"{self.manifest.help or ""}\"\"\"
    pass

"""

    def define_groups(self) -> None:
        for group in self.groups.values():
            parsed_help = group.help.replace("\n", "") if group.help else ""
            self.cli += f"""
@click.group()
def {group.var_name}():
    \"\"\"{parsed_help}\"\"\"
    pass
"""

    def add_group(self, group: BaseGroup) -> None:
        parent_var = group.parent_group.var_name if group.parent_group else "cli"
        self.cli += f"""
{parent_var}.add_command({group.var_name}, name="{group.short_name}")
"""

    def add_root_command(self, command: Command) -> None:
        if not command.run:
            return

        parsed_command_func_name = self.click_parser.get_command_func_name(command)
        parsed_command_name = self.click_parser.get_parsed_command_name(command)
        parsed_help = command.help.replace("\n", "") if command.help else ""

        self.cli += f"""
@cli.command(name="{parsed_command_name}")
{self.click_parser.parse_params(command)}
def {parsed_command_func_name}({self.click_parser.get_param_names(command)}):
    \"\"\"{parsed_help}\"\"\"
{self.click_parser.parse_command_run(command)}
"""

        for alias in command.aliases:
            self.cli += f"""
@cli.command(name="{alias}", hidden=True)
{self.click_parser.parse_params(command)}
def {parsed_command_func_name}_{alias}({self.click_parser.get_param_names(command)}):
    \"\"\"Alias for {parsed_command_name}\"\"\"
{self.click_parser.parse_command_run(command)}
"""

    def add_sub_command(self, command: Command, group: BaseGroup) -> None:
        parsed_command_func_name = self.click_parser.get_command_func_name(command)
        parsed_command_name = self.click_parser.get_parsed_command_name(command)
        parsed_help = command.help.replace("\n", "") if command.help else ""

        self.cli += f"""
@{group.var_name}.command(name="{parsed_command_name}")
{self.click_parser.parse_params(command)}
def {parsed_command_func_name}({self.click_parser.get_param_names(command)}):
    \"\"\"{parsed_help}\"\"\"
{self.click_parser.parse_command_run(command)}
"""

        for alias in command.aliases:
            self.cli += f"""
@{group.var_name}.command(name="{alias}", hidden=True)
{self.click_parser.parse_params(command)}
def {parsed_command_func_name}_{alias}({self.click_parser.get_param_names(command)}):
    \"\"\"Alias for {parsed_command_name}\"\"\"
{self.click_parser.parse_command_run(command)}
"""

    def add_main_block(self) -> None:
        self.cli += """
if __name__ == "__main__":
    cli()
"""


class ClickParser:
    def __init__(self, manifest: CLIManifest) -> None:
        self.manifest = manifest

    def parse_run_block(self, script: Union[RunBlock, RunBlockList]) -> str:
        norm_script = script.to_script() if isinstance(script, RunBlockList) else script.root
        if not isinstance(norm_script, str):
            raise ValueError(f"Invalid script type: {type(norm_script)}")
        parsed_script: str = transform_bash(norm_script).strip()
        return "".join(" " * 4 + line + "\n" for line in parsed_script.split("\n"))

    def parse_command_run(self, command: Command) -> str:
        code = ""
        if command.pre_run:
            code += self.parse_run_block(command.pre_run)
        code += self.parse_run_block(command.run)
        if command.post_run:
            code += self.parse_run_block(command.post_run)
        return code

    def get_param_names(self, command: Command) -> str:
        """Get parameter names for function definition"""

        params = ""
        decorators = self.parse_params(command)

        option_regex = re.compile(r"@click\.option\(['\"](--\w+)['\"]")
        argument_regex = re.compile(r"@click\.argument\(['\"](\w+)['\"]")

        for decorator in decorators.split("\n"):
            option_match = option_regex.search(decorator)
            argument_match = argument_regex.search(decorator)

            if option_match:
                param_name = option_match.group(1).lstrip("-").replace("-", "_")
                params += f"{param_name}, "
            elif argument_match:
                param_name = argument_match.group(1).replace("-", "_")
                params += f"{param_name}, "

        return params.rstrip(", ")

    def parse_params(self, command: Command) -> str:
        """Parse parameters into Click decorators"""
        if not command.params:
            return ""

        decorators = []
        for param in self.manifest.global_params + command.params:
            if isinstance(param, GenericCommandParam):
                name = param.root.strip()
                decorators.append(name)
            elif isinstance(param, CommandParam):
                decorator = self._build_click_option(param)
                decorators.append(decorator)
            elif isinstance(param, SimpleCommandParam):
                decorator = self._parse_simple_param(param)
                decorators.append(decorator)

        return "\n".join(decorators)

    def _parse_simple_param(self, param: SimpleCommandParam) -> str:
        """Parse SimpleCommandParam into Click decorator"""
        name = next(iter(param.root.keys()))
        param_spec = next(iter(param.root.values()))

        # Split type and default value if present
        type_parts = param_spec.split("=")
        param_type = type_parts[0].rstrip("!")
        default_value = type_parts[1] if len(type_parts) > 1 else None

        # Check if required
        required = param_spec.endswith("!")

        # Determine if option or argument based on name prefix
        if name.startswith("-"):
            # Strip leading dashes for option name
            option_name = name.lstrip("-")
            option_parts = [f"@click.option('--{option_name}'"]

            if param_type:
                option_parts.append(f"type={param_type}")
            if required:
                option_parts.append("required=True")
            if default_value is not None:
                if param_type == "str":
                    option_parts.append(f"default='{default_value}'")
                else:
                    option_parts.append(f"default={default_value}")

            return ", ".join(option_parts) + ")"
        else:
            # Regular argument
            arg_parts = [f"@click.argument('{name}'"]
            if param_type:
                arg_parts.append(f"type={param_type}")
            if default_value is not None:
                if param_type == "str":
                    arg_parts.append(f"default='{default_value}'")
                else:
                    arg_parts.append(f"default={default_value}")

            return ", ".join(arg_parts) + ")"

    def _build_click_option(self, param: CommandParam) -> str:
        """Build Click option decorator from CommandParam"""
        option_parts = [f"@click.option('--{param.name}'"]

        if param.short:
            option_parts.append(f"'-{param.short}'")

        if param.type:
            option_parts.append(f"type={param.type}")

        if param.required:
            option_parts.append("required=True")

        if param.default is not None:
            if param.type == "str":
                option_parts.append(f"default='{param.default}'")
            else:
                option_parts.append(f"default={param.default}")

        if param.help:
            option_parts.append(f"help='{param.help}'")

        return ", ".join(option_parts) + ")"

    def get_command_func_name(self, command: Command) -> str:
        """Get valid Python function name for command"""
        if not command.name.replace(".", "").replace("-", "").replace("_", "").replace("|", "").isalnum():
            raise ValueError(f"Invalid command name: {command.name}")
        return command.name.replace(".", "_").replace("-", "_").replace("|", "_")

    def get_parsed_command_name(self, command: Command) -> str:
        """Get command name for Click"""
        return command.name.split(".")[-1] if "." in command.name else command.name

    def to_args(self, d: dict) -> str:
        s = "".join(f' {k}="{v}",' if isinstance(v, str) else f" {k}={v}," for k, v in d.items())
        return s[:-1]
