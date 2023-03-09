## Command parser
from typing import Any, Tuple, Union

import pybash


class Parser:
    def __init__(self, command_config) -> None:
        self.command_config: dict = command_config
        self.args: dict = self.command_config.get("args", {})
        self.types: dict = self.command_config.get("types", {})

    def is_param_required(self, param_type: str) -> bool:
        return (
            param_type.strip().endswith('!')
            if '=' not in param_type
            else param_type.split('=')[0].strip().endswith('!')
        )

    def is_param_option(self, param_name: str) -> bool:
        return '-' in param_name

    def get_default_param_val(self, param_type: str) -> str:
        return param_type.split('=')[1].strip() if '=' in param_type else None

    def capture_param_aliases(self, param_name: str) -> Tuple[str, list[str]]:
        if '|' not in param_name:
            return param_name.replace('-', ''), []

        base_param_name = param_name.split('|')[0].replace('-', '')
        aliases = param_name.split('|')[1:]

        return base_param_name, aliases

    def parse_command_block(self, script: str):
        ## Bash commands start with $
        if script.startswith('$'):
            script = '>' + script[1:]
            return " " * 4 + pybash.Transformer.transform_source(script)

        parsed_script = ""
        for line in script.split('\n'):
            parsed_script += " " * 4 + line + "\n"
        return parsed_script

    def parse_command(self, block: Union[str, list[str]]) -> str:
        if isinstance(block, list):
            code = "".join(map(self.parse_command_block, block))
        else:
            code = self.parse_command_block(block)

        return code

    def build_param_type(
        self,
        arg_name: str,
        arg_type: str,
        typer_cls: str,
        aliases: list[str] = None,
        default_val: Any = None,
        is_required: bool = False,
    ) -> str:
        parsed_arg_type = f"{arg_name}: {arg_type} = typer.{typer_cls}"

        if not default_val:
            # Required param needs ...
            parsed_arg_type += "(..." if is_required else "(None"
        else:
            # Optional if default_val given
            if arg_type == "str":
                parsed_arg_type += f"('{default_val}'"
            else:
                parsed_arg_type += f"({default_val}"

            if aliases:
                parsed_arg_type += f', "--{arg_name}"'
                for alias in aliases:
                    parsed_arg_type += f', "{alias}"'

        parsed_arg_type += '),'
        return parsed_arg_type

    def parse_arg(self, arg_name: str, arg_type: str) -> str:
        parsed_arg_type = ""
        is_required = self.is_param_required(arg_type)
        default_val = self.get_default_param_val(arg_type)
        param_type = 'Option' if self.is_param_option(arg_name) else 'Argument'
        arg_aliases = []

        # extract default val before parsing it
        if '=' in arg_type:
            arg_type = arg_type.split('=')[0].strip()

        # strip - before parsing it
        if self.is_param_option(arg_name):
            arg_name, arg_aliases = self.capture_param_aliases(arg_name)

        # strip ! before parsing it
        if is_required:
            arg_type = arg_type[:-1]

        # check for a type def that matches arg_type
        if arg_type in self.types:
            return f"{arg_name}: {self.types[arg_type]},"

        # otherwise parse it
        parsed_arg_type = self.build_param_type(
            arg_name,
            arg_type,
            typer_cls=param_type,
            aliases=arg_aliases,
            default_val=default_val,
            is_required=is_required,
        )

        return parsed_arg_type

    def parse_args(self, command) -> str:
        if not self.args:
            return ""

        command_args = self.args.get(command.name)
        if not command_args:
            return ""

        parsed_command_args = ""
        for arg in command_args:
            arg_name, arg_type = next(iter(arg.items()))
            parsed_command_args += self.parse_arg(arg_name.strip(), arg_type.strip()) + ' '

        # strip the extra ", "
        return parsed_command_args[:-2]

    def get_command_func_name(self, command) -> str:
        """land.build -> land_build or sell -> sell"""
        return command.name.replace('.', '_')

    def get_parsed_command_name(self, command) -> str:
        """land.build -> build or sell -> sell"""
        if '.' in command.name:
            return command.name.split('.')[-1]

        return command.name

    def indent_block(self, block: str) -> str:
        blocklines = block.splitlines()
        indented_block = "\n".join([" " * 4 + line for line in blocklines])
        return indented_block

    def to_args(self, d: dict) -> str:
        s = ""
        for k, v in d.items():
            s += f" {k}={v},"
        return s[:-1]
