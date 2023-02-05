## Command parser
import pybash


class Parser:
    def __init__(self, command_config) -> None:
        self.command_config = command_config

    def parse(self, script: str):
        ## Bash commands start with $
        if script.startswith('$'):
            script = '>' + script[1:]
            return pybash.Transformer.transform_source(script)

        return script

    def build_param_type(self, arg_name: str, arg_type: str, typer_cls: str):
        required = arg_type.startswith('!')
        if required:
            arg_type = arg_type[1:]

        if '=' not in arg_type:
            parsed_arg_type = f"{arg_name}: {arg_type} = typer.{typer_cls}"

            # Required param needs ...
            parsed_arg_type += "(None)," if not required else "(...),"
        else:
            ## Optional if default val given
            default_val = arg_type.split('=')[1].strip()
            if arg_type == "str":
                parsed_arg_type = f"{arg_name}: {arg_type} = typer.{typer_cls}('{default_val}'),"
            else:
                parsed_arg_type = f"{arg_name}: {arg_type} = typer.{typer_cls}({default_val}),"

        return parsed_arg_type

    def parse_arg(self, arg_name: str, arg_type: str):
        parsed_arg_type = ""
        if arg_type.startswith('-'):
            arg_type = arg_type[1:]
            parsed_arg_type = self.build_param_type(arg_name, arg_type, paramtyper_cls_type='Option')
            ## Option
        else:
            ## Param
            parsed_arg_type = self.build_param_type(arg_name, arg_type, typer_cls='Argument')

        types = self.command_config.get("types")
        if not types or arg_type not in types:
            return parsed_arg_type

        ## Override with types refs
        return f"{arg_name}: {types[arg_type]},"

    def parse_args(self, command):
        args = self.command_config.get("args")
        if not args:
            return ""

        command_args = args.get(command.name)
        if not command_args:
            return ""

        parsed_command_args = ""
        for arg in command_args.split(','):
            arg_name, arg_type = arg.split(':')
            parsed_command_args += self.parse_arg(arg_name.strip(), arg_type.strip())

        return parsed_command_args[:-1]

    def get_command_func_name(self, command):
        """land.build -> land_build, sell -> sell"""
        return command.name.replace('.', '_')

    def get_parsed_command_name(self, command):
        """land.build -> build, sell -> sell"""
        if '.' in command.name:
            return command.name.split('.')[-1]

        return command.name
