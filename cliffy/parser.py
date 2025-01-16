## Command parser
from typing import Any, Optional, Tuple, Union

from pybash.transformer import transform as transform_bash

from .manifest import (
    CLIManifest,
    Command,
    CommandParam,
    GenericCommandParam,
    RunBlock,
    RunBlockList,
    SimpleCommandParam,
)


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

    def build_param_type(
        self,
        param_name: str,
        param_type: str,
        typer_cls: str,
        aliases: Optional[list[str]] = None,
        default_val: Any = None,
        is_required: bool = False,
        help: Optional[str] = None,
        extra_params: Optional[str] = None,
    ) -> str:
        """
        Builds a type-annotated parameter definition for Typer CLI command.

        Args:
            param_name (str): Name of the parameter to be defined.
            param_type (str): Type annotation for the parameter.
            typer_cls (str): Typer class to use (e.g., "Option", "Argument").
            aliases (list[str], optional): Alternative names for the parameter.
            default_val (Any, optional): Default value for the parameter.
            is_required (bool, default=False): Whether the parameter is mandatory.
            help (str, optional): Help text describing the parameter.
            extra_params (str, optional): Additional Typer parameter configurations.

        Returns:
            str: A formatted parameter type definition for Typer CLI command generation.

        Example:
            # Generates: username: str = typer.Option("", "--username", help="User login")
            build_param_type(
                param_name="username",
                param_type="str",
                typer_cls="Option",
                default_val="",
                help="User login"
            )
        """
        parsed_param_type = f"{param_name}: {param_type} = typer.{typer_cls}"
        if default_val is None:
            # Required param needs ...
            parsed_param_type += "(..." if is_required else "(None"
        else:
            parsed_param_type += f"({default_val}"

        if aliases and typer_cls == "Option":
            if param_name.startswith("--"):
                parsed_param_type += f', "{param_name}"'
            else:
                parsed_param_type += f', "--{param_name}"'

            for alias in aliases:
                parsed_param_type += f', "{alias.strip()}"'

        if help:
            parsed_param_type += f', help="{help}"'

        if extra_params:
            parsed_param_type += f", {extra_params}"

        parsed_param_type += "),"
        return parsed_param_type

    def parse_param(self, param: Union[CommandParam, GenericCommandParam, SimpleCommandParam]) -> str:
        if isinstance(param, GenericCommandParam):
            return f"{param.root}, "

        typer_cls = "Option" if param.is_option() else "Argument"
        norm_param_name = self.normalize_param_name(param.name)
        param_type = param.type

        if isinstance(param, SimpleCommandParam) and "typer." in param.raw_type:
            return f"{norm_param_name.strip()}: {param_type.strip()}, "

        if param_type in self.manifest.types:
            return f"{norm_param_name}: {self.manifest.types[param_type]},"

        aliases = [param.short] if param.short else None

        if isinstance(param, CommandParam):
            # wrap default_val in quotes if it's a string and not wrapped already
            default_val = (
                f'"{param.default.replace('"', r"\"")}"'
                if param.type == "str" and param.default is not None
                else param.default
            )
        else:
            # for simple, assume it's already wrapped
            default_val = param.default

        return self.build_param_type(
            param_name=norm_param_name,
            param_type=param_type,
            typer_cls=typer_cls,
            aliases=aliases,
            default_val=default_val,
            is_required=param.required,
            help=param.help,
        )

    def parse_params(self, command: Command) -> str:
        if not command.params:
            return ""

        combined_command_params = self.manifest.global_params + command.params
        parsed_command_params = "".join(f"{self.parse_param(param)} " for param in combined_command_params)
        # strip the extra ", " if exists
        return parsed_command_params.strip().rstrip(",")

    def get_parsed_config(self, command: Command) -> str:
        """
        Retrieve and format the configuration options for a given command.

        Converts the command's configuration to a string of python params, excluding any unset options.

        Args:
            command (Command): The command whose configuration is to be parsed.

        Returns:
            str: A formatted string of python-style params representing the command's configuration,
                 or an empty string if no configuration is set.

        Example:
            If a command has a configuration with {'verbose': True, 'output': 'log.txt'},
            this method would return 'verbose=True, output="log.txt"'
        """
        if not command.config:
            return ""

        configured_options = command.config.model_dump(exclude_unset=True)
        return self.to_args(configured_options)

    def normalize_param_name(self, name: str) -> str:
        return name.lstrip("-").replace("-", "_")

    def get_command_func_name(self, command: Command) -> str:
        """a -> a, a.b -> a_b, a-b -> a_b, a|b -> a_b"""
        if not command.name.replace(".", "").replace("-", "").replace("_", "").replace("|", "").isalnum():
            raise ValueError(f"Invalid command name: {command.name}")
        return command.name.replace(".", "_").replace("-", "_").replace("|", "_")

    def get_parsed_command_name(self, command: Command) -> str:
        """a -> a, a.b -> b"""
        return command.name.split(".")[-1] if "." in command.name else command.name

    def to_args(self, d: dict) -> str:
        s = "".join(f' {k}="{v}",' if isinstance(v, str) else f" {k}={v}," for k, v in d.items())
        return s[:-1]
