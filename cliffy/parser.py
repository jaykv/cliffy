## Command parser
import keyword
from typing import Any

from pybash.transformer import transform as transform_bash

from cliffy.helper import py_str, to_identifier
from cliffy.manifest import (
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

    def parse_run_block(self, script: RunBlock | RunBlockList) -> str:
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
        aliases: list[str] | None = None,
        default_val: Any = None,
        is_required: bool = False,
        help: str | None = None,
        extra_params: str | None = None,
        option_name: str | None = None,
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
            option_name (str, optional): Option name as written in the manifest (e.g. "--dry-run").
                Defaults to param_name. Only used when aliases are given.

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
            # typer derives `--dry-run` from `dry_run` on its own, but not when other names are passed
            parsed_param_type += f", {py_str('--' + (option_name or param_name).strip().lstrip('-'))}"

            for alias in aliases:
                parsed_param_type += f", {py_str(alias.strip())}"

        if help:
            parsed_param_type += f", help={py_str(help)}"

        if extra_params:
            parsed_param_type += f", {extra_params}"

        parsed_param_type += "),"
        return parsed_param_type

    def parse_param(self, param: CommandParam | GenericCommandParam | SimpleCommandParam) -> str:
        if isinstance(param, GenericCommandParam):
            return f"{param.root}, "

        typer_cls = "Option" if param.is_option() else "Argument"
        norm_param_name = self.normalize_param_name(param.name)
        param_type = param.type

        if isinstance(param, SimpleCommandParam) and "typer." in param.raw_type:
            # a full typer definition, i.e. `name: str = typer.Option(..., prompt=True)`, is passed through as-is
            return f"{norm_param_name}: {param.raw_type.strip()}, "

        aliases = [param.short] if param.short else None
        default_val = param.default

        # only wrap strings for CommandParam, leave simple params as-is
        if default_val is not None and isinstance(param, CommandParam) and param.type == "str":
            # a str default is data, not an expression: emit it as a string literal
            default_val = py_str(default_val)

        if param_type in self.manifest.types:
            definition = self.manifest.types[param_type].strip()
            if "typer." in definition:
                # a complete Typer definition replaces everything after the param name
                return f"{norm_param_name}: {definition},"
            # `N: int` or `N: int = 5` names a type (and a default): the param keeps its own name, kind and help
            param_type, _, type_default = (part.strip() for part in definition.partition("="))
            if default_val is None and type_default:
                default_val = type_default
            elif isinstance(param, CommandParam) and param.default is not None and param_type == "str":
                default_val = py_str(param.default)

        return self.build_param_type(
            param_name=norm_param_name,
            param_type=param_type,
            typer_cls=typer_cls,
            aliases=aliases,
            default_val=default_val,
            is_required=param.required,
            help=param.help,
            option_name=param.name,
        )

    def parse_params(self, command: Command) -> str:
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
        """--dry-run -> dry_run. The result is the name the run block uses, so it is validated, never renamed."""
        norm_name = name.strip().lstrip("-").replace("-", "_")
        if not norm_name.isidentifier() or keyword.iskeyword(norm_name):
            raise ValueError(
                f"Invalid param name: {name}. A param becomes a Python variable, "
                "so it has to be a valid identifier and cannot be a keyword."
            )
        return norm_name

    def get_command_func_name(self, command: Command) -> str:
        """a -> a, a.b -> a_b, a-b -> a_b, a|b -> a_b, import -> import_, list -> list_"""
        if not command.name.replace(".", "").replace("-", "").replace("_", "").replace("|", "").isalnum():
            raise ValueError(f"Invalid command name: {command.name}")
        return to_identifier(command.name)

    def get_parsed_command_name(self, command: Command) -> str:
        """a -> a, a.b -> b"""
        return command.name.split(".")[-1] if "." in command.name else command.name

    def to_args(self, d: dict) -> str:
        s = "".join(f" {k}={py_str(v)}," if isinstance(v, str) else f" {k}={v!r}," for k, v in d.items())
        return s[:-1]
