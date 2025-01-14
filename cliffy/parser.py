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
        parsed_param_type = f"{param_name}: {param_type} = typer.{typer_cls}"
        if not default_val:
            # Required param needs ...
            parsed_param_type += "(..." if is_required else "(None"
        else:
            parsed_param_type += f"({default_val.strip()}"

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

    def parse_param(self, param_name: str, param_type: str) -> str:
        is_required = self.is_param_required(param_type)
        default_val = self.get_default_param_val(param_type)
        param_typer_cls = "Option" if self.is_param_option(param_name) else "Argument"
        arg_aliases: list[str] = []

        # extract default val before parsing it
        if "=" in param_type:
            param_type = param_type.split("=")[0].strip()

        # lstrip - before parsing it
        if self.is_param_option(param_name):
            param_name, arg_aliases = self.capture_param_aliases(param_name)

        # rstrip ! before parsing it
        if is_required:
            param_type = param_type[:-1]

        # replace - with _ for arg name
        param_name = param_name.replace("-", "_")

        # check for a type def that matches param_type
        if param_type in self.manifest.types:
            return f"{param_name}: {self.manifest.types[param_type]},"

        return self.build_param_type(
            param_name,
            param_type,
            typer_cls=param_typer_cls,
            aliases=arg_aliases,
            default_val=default_val,
            is_required=is_required,
        )

    def parse_params(self, command: Command) -> str:
        if not command.params:
            return ""

        parsed_command_params = ""
        combined_command_params = self.manifest.global_params + command.params
        for param in combined_command_params:
            if isinstance(param, CommandParam):
                aliases = [param.short] if param.short else None

                parsed_command_params += (
                    self.build_param_type(
                        param_name=param.name,
                        param_type=param.type,
                        typer_cls="Option" if param.is_option() else "Argument",
                        help=param.help,
                        aliases=aliases,
                        default_val=str(param.default) if param.default is not None else None,
                        is_required=param.required,
                    )
                    + " "
                )
            elif isinstance(param, GenericCommandParam):
                parsed_command_params += f"{param}, "
            elif isinstance(param, SimpleCommandParam):
                param_name, param_type = next(iter(param.root.items()))

                if "typer." in param_type:
                    parsed_command_params += f"{param_name.strip()}: {param_type.strip()}, "
                else:
                    parsed_command_params += f"{self.parse_param(param_name.strip(), param_type.strip())} "

        # strip the extra ", "
        return parsed_command_params[:-2]

    def get_parsed_config(self, command: Command) -> str:
        if not command.config:
            return ""

        configured_options = command.config.model_dump(exclude_unset=True)
        return self.to_args(configured_options)

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
