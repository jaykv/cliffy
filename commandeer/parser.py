## Command parser
from typing import Any

import pybash


class Parser:
    def __init__(self, command_config) -> None:
        self.command_config = command_config
        self.args = self.command_config.get("args") or {}

    def is_param_required(self, param: str):
        return param.strip().endswith('!') if '=' not in param else param.split('=')[0].strip().endswith('!')

    def is_param_option(self, param: str):
        return param.startswith('-')

    def get_default_param_val(self, param: str):
        return param.split('=')[1].strip() if '=' in param else None

    def parse(self, script: str):
        ## Bash commands start with $
        if script.startswith('$'):
            script = '>' + script[1:]
            return pybash.Transformer.transform_source(script)

        parsed_script = ""
        for line in script.split('\n'):
            parsed_script += "    " + line + "\n"
        return parsed_script

    def build_param_type(
        self, arg_name: str, arg_type: str, typer_cls: str, default_val: Any = None, is_required: bool = False
    ):
        parsed_arg_type = f"{arg_name}: {arg_type} = typer.{typer_cls}"

        if not default_val:
            # Required param needs ...
            parsed_arg_type += "(...)," if is_required else "(None),"
        else:
            # Optional if default_val given
            if arg_type == "str":
                parsed_arg_type += f"('{default_val}'),"
            else:
                parsed_arg_type += f"({default_val}),"

        return parsed_arg_type

    def parse_arg(self, arg_name: str, arg_type: str):
        parsed_arg_type = ""
        is_required = self.is_param_required(arg_type)
        default_val = self.get_default_param_val(arg_type)
        param_type = 'Option' if self.is_param_option(arg_type) else 'Argument'

        # extract default val before parsing it
        if '=' in arg_type:
            arg_type = arg_type.split('=')[0].strip()

        # strip - before parsing it
        if self.is_param_option(arg_type):
            arg_type = arg_type[1:]

        # strip ! before parsing it
        if is_required:
            arg_type = arg_type[:-1]

        parsed_arg_type = self.build_param_type(
            arg_name, arg_type, typer_cls=param_type, default_val=default_val, is_required=is_required
        )

        # check for type def that matches arg_type
        types = self.command_config.get("types")
        if not types or arg_type not in types:
            return parsed_arg_type

        ## Override with types refs
        return f"{arg_name}: {types[arg_type]},"

    def parse_args(self, command):
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

    def get_command_func_name(self, command):
        """land.build -> land_build, sell -> sell"""
        return command.name.replace('.', '_')

    def get_parsed_command_name(self, command):
        """land.build -> build, sell -> sell"""
        if '.' in command.name:
            return command.name.split('.')[-1]

        return command.name
