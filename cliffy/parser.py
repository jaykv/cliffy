## Command parser
from typing import Any, Optional, Tuple, Union

from pybash.transformer import transform as transform_bash

from .manifest import CLIManifest, Command, CommandBlock, CommandArg


class Parser:
    __slots__ = ("manifest",)

    def __init__(self, manifest: CLIManifest) -> None:
        self.manifest = manifest

    def is_param_required(self, param_type: str) -> bool:
        return (
            param_type.strip().endswith("!")
            if "=" not in param_type
            else param_type.split("=")[0].strip().endswith("!")
        )

    def is_param_option(self, param_name: str) -> bool:
        return param_name.startswith("-")

    def get_default_param_val(self, param_type: str) -> str:
        return param_type.split("=")[1].strip() if "=" in param_type else ""

    def capture_param_aliases(self, param_name: str) -> Tuple[str, list[str]]:
        if "|" not in param_name:
            return param_name.lstrip("-"), []

        base_param_name = param_name.split("|")[0].lstrip("-").strip()
        aliases = param_name.split("|")[1:]

        return base_param_name, aliases

    def parse_command_block(self, script: Union[str, list[str]]) -> str:
        norm_script = "\n".join(script) if isinstance(script, list) else script
        parsed_script = transform_bash(norm_script).strip()
        return "".join(" " * 4 + line + "\n" for line in parsed_script.split("\n"))

    def parse_command(self, block: CommandBlock) -> str:
        if isinstance(block, Command):
            code = f'    """\n    {block.help}\n    """\n' if block.help else ""
            code += self.parse_command_block(block.run)
        elif isinstance(block, list):
            script_block = []
            help_text = ""
            for block_elem in block:
                if isinstance(block_elem, dict):
                    help_text = block_elem.get("help", "")
                else:
                    script_block.append(block_elem)

            code = f'    """\n    {help_text}\n    """\n' if help_text else ""
            code += "".join(map(self.parse_command_block, script_block))
        else:
            code = self.parse_command_block(block)

        return code

    def build_param_type(
        self,
        arg_name: str,
        arg_type: str,
        typer_cls: str,
        aliases: Optional[list[str]] = None,
        default_val: Any = None,
        is_required: bool = False,
        help: Optional[str] = None,
        extra_params: Optional[str] = None,
    ) -> str:
        parsed_arg_type = f"{arg_name}: {arg_type} = typer.{typer_cls}"
        if not default_val:
            # Required param needs ...
            parsed_arg_type += "(..." if is_required else "(None"
        else:
            parsed_arg_type += f"({default_val.strip()}"

        if aliases:
            parsed_arg_type += f', "--{arg_name}"'
            for alias in aliases:
                parsed_arg_type += f', "{alias.strip()}"'

        if help:
            parsed_arg_type += f', help="{help}"'

        if extra_params:
            parsed_arg_type += f", {extra_params}"

        parsed_arg_type += "),"
        return parsed_arg_type

    def parse_arg(self, arg_name: str, arg_type: str) -> str:
        is_required = self.is_param_required(arg_type)
        default_val = self.get_default_param_val(arg_type)
        param_type = "Option" if self.is_param_option(arg_name) else "Argument"
        arg_aliases: list[str] = []

        # extract default val before parsing it
        if "=" in arg_type:
            arg_type = arg_type.split("=")[0].strip()

        # lstrip - before parsing it
        if self.is_param_option(arg_name):
            arg_name, arg_aliases = self.capture_param_aliases(arg_name)

        # rstrip ! before parsing it
        if is_required:
            arg_type = arg_type[:-1]

        # replace - with _ for arg name
        arg_name = arg_name.replace("-", "_")

        # check for a type def that matches arg_type
        if arg_type in self.manifest.types:
            return f"{arg_name}: {self.manifest.types[arg_type]},"

        return self.build_param_type(
            arg_name,
            arg_type,
            typer_cls=param_type,
            aliases=arg_aliases,
            default_val=default_val,
            is_required=is_required,
        )

    def parse_args(self, command: Command) -> str:
        if not command.args:
            return ""

        parsed_command_args = ""
        combined_command_args = self.manifest.global_args + command.args
        for arg in combined_command_args:
            if isinstance(arg, CommandArg):
                aliases = [f"-{arg.short}"] if arg.short else None

                parsed_command_args += (
                    self.build_param_type(
                        arg_name=arg.name,
                        arg_type=arg.type,
                        typer_cls=arg.kind,
                        help=arg.help,
                        aliases=aliases,
                        default_val=str(arg.default) if arg.default is not None else None,
                        is_required=arg.required,
                    )
                    + " "
                )
            elif isinstance(arg, str):
                parsed_command_args += f"{arg}, "
            elif isinstance(arg, dict):
                arg_name, arg_type = next(iter(arg.items()))

                if "typer." in arg_type:
                    parsed_command_args += f"{arg_name.strip()}: {arg_type.strip()}, "
                else:
                    parsed_command_args += f"{self.parse_arg(arg_name.strip(), arg_type.strip())} "

        # strip the extra ", "
        return parsed_command_args[:-2]

    def get_command_func_name(self, command) -> str:
        """a -> a, a.b -> a_b, a-b -> a_b, a|b -> a_b"""
        return command.name.replace(".", "_").replace("-", "_").replace("|", "_")

    def get_parsed_command_name(self, command) -> str:
        """a -> a, a.b -> b"""
        return command.name.split(".")[-1] if "." in command.name else command.name

    def to_args(self, d: dict) -> str:
        s = "".join(f" {k}={v}," for k, v in d.items())
        return s[:-1]
