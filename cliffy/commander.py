from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator, ItemsView, ValuesView, Optional
from pybash.transformer import transform as transform_bash
from pydantic import BaseModel
from collections import defaultdict


from cliffy.manifest import (
    ParamBlock,
    CLIManifest,
    Command,
    CommandParam,
    CommandConfig,
    GenericCommandParam,
    PostRunBlock,
    PreRunBlock,
    RunBlock,
    SimpleCommandParam,
    RunBlockList,
)
from cliffy.parser import Parser


class CLI(BaseModel):
    name: str
    version: str
    code: str
    requires: list[str] = []


class BaseGroup(BaseModel):
    name: str
    short_name: str = ""
    parent_group: Optional[BaseGroup] = None
    commands: list[Command] = []
    help: str = ""

    @property
    def var_name(self) -> str:
        """Returns valid Python variable name for group app"""
        return self.name.replace(".", "_") + "_app"


class Groups(BaseModel):
    """Root container for all groups"""

    root: dict[str, BaseGroup] = {}

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        return iter(self.root)

    def items(self) -> ItemsView[str, BaseGroup]:  # type: ignore[override]
        return self.root.items()

    def values(self) -> ValuesView[BaseGroup]:
        return self.root.values()

    def __getitem__(self, key: str) -> BaseGroup:
        return self.root[key]

    def __len__(self) -> int:
        return len(self.root)

    def add_group_by_full_path(self, full_path: str) -> str:
        if "." not in full_path:
            self.root[full_path] = BaseGroup(name=full_path, short_name=full_path, parent_group=None)
            return full_path

        group_name, _ = full_path.rsplit(".", 1)
        if "." in group_name:
            parent_group_name, short_name = group_name.rsplit(".", 1)
            if parent_group_name in self.root:
                parent_group = self.root[parent_group_name]
            else:
                parent_group = self.root[self.add_group_by_full_path(parent_group_name)]
        else:
            short_name = group_name
            parent_group = None

        if group_name in self.root:
            return group_name

        self.root[group_name] = BaseGroup(name=group_name, short_name=short_name, parent_group=parent_group)
        return group_name

    def add_command_to_group(self, command: Command) -> None:
        group_name = self.add_group_by_full_path(command.name)
        self.root[group_name].commands.append(command)


class Commander(ABC):
    """Generates commands based on the command config"""

    __slots__ = (
        "manifest",
        "parser",
        "cli",
        "groups",
        "greedy",
        "root_commands",
        "base_imports",
        "aliases_by_commands",
        "commands",
        "root_group",
    )

    def __init__(self, manifest: CLIManifest) -> None:
        self.manifest = manifest
        self.parser = Parser(self.manifest)
        self.cli: str = ""
        self.greedy: list[Command] = []
        self.groups = Groups()
        self.root_group = BaseGroup(name="__root__", short_name="cli", commands=[])

        if isinstance(self.manifest.commands, list):
            self.manifest.commands = {command.name: command for command in self.manifest.commands}
        for name, command in self.manifest.commands.items():
            if isinstance(command, Command) and not command.name:
                self.manifest.commands[name].name = name  # type: ignore

        self.base_imports: set[str] = set()
        self.aliases_by_commands: dict[str, list[str]] = defaultdict(list)

        self.commands: list[Command] = [
            command if isinstance(command, Command) else Command(name=name, run=command)
            for name, command in self.manifest.commands.items()
        ]
        self.build_groups()

    def _merge_command_template(self, command: Command) -> None:
        """Merge command with its template if specified."""
        if not command.template:
            return

        template = self.manifest.command_templates.get(command.template)
        if not template:
            raise ValueError(f"Template {command.template} undefined in command_templates")

        if template.params:
            command.params = template.params + (command.params or [])
        if template.config:
            merged = template.config.model_dump(exclude_unset=True) | (
                command.config.model_dump(exclude_unset=True) if command.config else {}
            )
            command.config = CommandConfig(**merged)
        if template.pre_run:
            command.pre_run = PreRunBlock(template.pre_run.root + "\n" + (command.pre_run.root or ""))
        if template.post_run:
            command.post_run = PostRunBlock((command.post_run.root or "") + "\n" + template.post_run.root)

    def build_groups(self) -> None:
        """Build group hierarchy from command names"""
        for command in self.commands:
            if self.is_greedy(command.name):
                self.greedy.append(command)
                continue

            self._merge_command_template(command)

            if "|" in command.name:
                command_parts = [s.strip() for s in command.name.split("|")]
                command.name = command_parts[0]
                command.aliases += command_parts[1:]
                self.aliases_by_commands[command_parts[0]] = command_parts[1:]

            if "." in command.name:
                self.groups.add_command_to_group(command)
            else:
                self.root_group.commands.append(command)

        # loop again to check for group help
        # TODO: probably should be a separate manifest field i.e. group_config
        for command in self.commands:
            # set group help- must be script-less command with help defined
            if not command.run and command.help and command.name in self.groups:
                self.groups[command.name].help = command.help

    def add_subcommands(self) -> None:
        for group in self.groups.values():
            self.add_group(group)
            for subcommand in group.commands:
                self.add_sub_command(subcommand, group)

    def generate_cli(self) -> None:
        self.add_base_imports()
        self.add_imports()
        self.add_vars()
        self.add_base_cli()
        self.define_groups()
        self.add_functions()
        self.add_root_commands()
        self.add_subcommands()
        self.add_greedy_commands()
        self.add_main_block()

    def add_root_commands(self) -> None:
        for root_command in self.root_group.commands:
            self.add_root_command(root_command)

    def add_imports(self) -> None:
        if not self.manifest.imports:
            return

        if isinstance(self.manifest.imports, str):
            self.cli += self.manifest.imports + "\n"
        elif isinstance(self.manifest.imports, list):
            for _import in self.manifest.imports:
                self.cli += _import + "\n"
        self.cli += "\n"

    def add_vars(self) -> None:
        if not self.manifest.vars:
            return

        for var, val in self.manifest.vars.items():
            if isinstance(val, dict):
                self.cli += f"{var} = {next(iter(val))}\n"
            else:
                self.cli += f"{var} = '{val}'\n"
        self.cli += "\n"

    def add_functions(self) -> None:
        if not self.manifest.functions:
            return
        if isinstance(self.manifest.functions, str):
            self.cli += self.manifest.functions + "\n"
        elif isinstance(self.manifest.functions, list):
            for func in self.manifest.functions:
                self.cli += f"{transform_bash(func)}\n"
        self.cli += "\n"

    def add_command(self, command: Command) -> None:
        if "." in command.name:
            group = command.name.rsplit(".")[0]
            self.add_sub_command(command, self.groups[group])

    def add_greedy_commands(self) -> None:
        """Greedy commands get lazy-loaded. Only supported for group-commands currently"""
        for greedy_command in self.greedy:
            if greedy_command.name.startswith("(*)"):
                for group in self.groups.values():
                    self.add_lazy_command(greedy_command, group)

    def add_lazy_command(self, greedy_command: Command, group: BaseGroup) -> None:
        # make it lazy and interpolate
        lazy_command = self.from_greedy_make_lazy_command(greedy_command=greedy_command, group=group.name)

        # lazy load
        self.commands.append(lazy_command)
        self.add_command(lazy_command)

    def is_greedy(self, val: str) -> bool:
        """Greedy strings must contain (*)- marked to be evaluated lazily."""
        return "(*)" in val

    def from_greedy_make_lazy_command(self, greedy_command: Command, group: str) -> Command:
        """
        Convert a greedy command to a lazy command by replacing placeholders with a specific group name.

        Args:
            greedy_command (Command): The original greedy command to be transformed
            group (str): The group name to replace placeholders with

        Returns:
            Command: A new command with placeholders replaced by the group name, ready for lazy loading

        Notes:
            - Handles replacement in command name, run blocks, help text, template, pre-run, and post-run blocks
            - Supports different parameter types: GenericCommandParam, CommandParam, and SimpleCommandParam
            - Preserves the original command's structure while updating placeholder-based content
        """
        lazy_command = greedy_command.model_copy(deep=True)
        lazy_command.name = greedy_command.name.replace("(*)", group)
        if isinstance(lazy_command.run, RunBlock):
            lazy_command.run = RunBlock(lazy_command.run.root.replace("{(*)}", group))
        elif isinstance(lazy_command.run, RunBlockList):
            lazy_command.run = RunBlockList(
                [RunBlock(script_block.root.replace("{(*)}", group)) for script_block in lazy_command.run]
            )
        if lazy_command.help:
            lazy_command.help = lazy_command.help.replace("{(*)}", group)

        if lazy_command.template:
            lazy_command.template = lazy_command.template.replace("{(*)}", group)

        if lazy_command.pre_run:
            lazy_command.pre_run.root = lazy_command.pre_run.root.replace("{(*)}", group)

        if lazy_command.post_run:
            lazy_command.post_run.root = lazy_command.post_run.root.replace("{(*)}", group)

        if lazy_command.params:
            if isinstance(lazy_command.params, GenericCommandParam):
                lazy_command.params.root = lazy_command.params.root.replace("{(*)}", group)
            elif isinstance(lazy_command.params, list):
                lazy_parsed_params: list[ParamBlock] = []
                for param in lazy_command.params:
                    if isinstance(param, GenericCommandParam):
                        lazy_parsed_params.append(GenericCommandParam(param.root.replace("{(*)}", group)))
                    if isinstance(param, CommandParam):
                        if param.help:
                            param.help = param.help.replace("{(*)}", group)
                        if param.default:
                            param.default = param.default.replace("{(*)}", group)
                        if param.short:
                            param.short = param.short.replace("{(*)}", group)
                        lazy_parsed_params.append(param)
                    if isinstance(param, SimpleCommandParam):
                        new_param = SimpleCommandParam(
                            {k.replace("{(*)}", group): v.replace("{(*)}", group) for k, v in param.root.items()}
                        )
                        lazy_parsed_params.append(new_param)
                lazy_command.params = lazy_parsed_params
        return lazy_command

    @abstractmethod
    def define_groups(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_group(self, group: BaseGroup) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_base_imports(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_base_cli(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_root_command(self, command: Command) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_sub_command(self, command: Command, group: BaseGroup) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_main_block(self) -> None:
        raise NotImplementedError


def generate_cli(manifest: CLIManifest, commander_cls: type[Commander] = Commander) -> CLI:
    """
    Generate a CLI object from a CLI manifest using the specified commander class.

    Args:
        manifest (CLIManifest): The manifest containing CLI configuration details
        commander_cls (type[Commander], optional): Commander class to use for CLI generation. Defaults to Commander.

    Returns:
        CLI: A CLI object with generated code, name, version, and required dependencies
    """
    commander = commander_cls(manifest)
    commander.generate_cli()
    return CLI(name=manifest.name, version=manifest.version, code=commander.cli, requires=manifest.requires)
