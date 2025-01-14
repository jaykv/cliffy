from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

from pybash.transformer import transform as transform_bash
from pydantic import BaseModel


from .manifest import (
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
from .parser import Parser


class CLI(BaseModel):
    name: str
    version: str
    code: str
    requires: list[str] = []


class Group(BaseModel):
    name: str
    commands: list[Command]
    help: str = ""


class Commander:
    """Generates commands based on the command config"""

    __slots__ = (
        "manifest",
        "parser",
        "cli",
        "groups",
        "greedy",
        "root_commands",
        "command_aliases",
        "base_imports",
        "aliases_by_commands",
        "commands",
    )

    def __init__(self, manifest: CLIManifest) -> None:
        self.manifest = manifest
        self.parser = Parser(self.manifest)
        self.cli: str = ""
        self.groups: dict[str, Group] = {}
        self.greedy: list[Command] = []
        for name, command in self.manifest.commands.items():
            if isinstance(command, Command) and not command.name:
                self.manifest.commands[name].name = name  # type: ignore
        self.commands: list[Command] = [
            command if isinstance(command, Command) else Command(name=name, run=command)
            for name, command in self.manifest.commands.items()
        ]
        self.root_commands: list[Command] = [command for command in self.commands if "." not in command.name]
        self.base_imports: set[str] = set()
        self.aliases_by_commands: dict[str, list[str]] = defaultdict(list)
        self.build_groups()
        self.setup_command_aliases()

    def setup_command_aliases(self) -> None:
        """Support inferred-aliasing with | operator.
        i.e. command_name | command_alias: print("hello")
        """
        for command in self.commands:
            if "|" in command.name:
                aliases = [s.strip() for s in command.name.split("|")]

                # skip group command aliases
                if "." in aliases[0]:
                    continue

                command.name = aliases[0]  # update command.name without the alias part
                for alias in aliases[1:]:
                    command.aliases.append(alias)
                    self.aliases_by_commands[command.name].append(alias)

    def build_groups(self) -> None:
        """
        Organize commands into groups and process command templates and aliases.

        This method performs several key operations:
        - Separates greedy commands for later processing
        - Merges command templates with individual commands
        - Handles command aliases
        - Creates command groups based on hierarchical command names

        Side Effects:
            - Populates self.greedy with greedy commands
            - Populates self.groups with organized command groups
            - Updates command attributes with template configurations
            - Tracks command aliases in self.aliases_by_commands

        Raises:
            ValueError: If a referenced command template is undefined
        """
        groups: DefaultDict[str, list[Command]] = defaultdict(list)
        group_help_dict = {}

        for command in self.commands:
            # Check for greedy commands- evaluate them at the end
            if self.is_greedy(command.name):
                self.greedy.append(command)
                continue

            # Merge with command template
            if command.template:
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

            if "." in command.name:
                group_name = command.name.split(".")[:-1][-1]

                if "|" in command.name:
                    command_aliases = command.name.rsplit(".", 1)[1].split("|")
                    command_name_sub_alias = command.name.split("|", 1)[0]
                    for alias in command_aliases[1:]:
                        command.aliases.append(alias)
                        self.aliases_by_commands[command_name_sub_alias].append(alias)

                    command.name = command_name_sub_alias

                groups[group_name].append(command)
            else:
                group_name = command.name
                group_help_dict[command.name] = command.help

        for group_name, commands in groups.items():
            self.groups[group_name] = Group(
                name=group_name,
                commands=commands,
                help=group_help_dict.get(group_name, ""),
            )

    def generate_cli(self) -> None:
        self.add_base_imports()
        self.add_imports()
        self.add_vars()
        self.add_base_cli()
        self.add_functions()
        self.add_root_commands()
        self.add_subcommands()
        self.add_greedy_commands()
        self.add_main_block()

    def add_root_commands(self) -> None:
        for root_command in self.root_commands:
            self.add_root_command(root_command)

    def add_subcommands(self) -> None:
        for group in self.groups.values():
            self.add_group(group)
            for subcommand in group.commands:
                self.add_sub_command(subcommand, group)

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

        for func in self.manifest.functions:
            self.cli += f"{transform_bash(func)}\n"
        self.cli += "\n"

    def add_command(self, command: Command) -> None:
        if "." in command.name:
            group = command.name.split(".")[:-1][-1]
            self.add_sub_command(command, self.groups[group])

    def add_lazy_command(self, greedy_command: Command, group: str) -> None:
        # make it lazy and interpolate
        lazy_command = self.from_greedy_make_lazy_command(greedy_command=greedy_command, group=group)

        # lazy load
        self.commands.append(lazy_command)
        self.add_command(lazy_command)

    def add_greedy_commands(self) -> None:
        """Greedy commands get lazy-loaded. Only supported for group-commands currently"""
        for greedy_command in self.greedy:
            if greedy_command.name.startswith("(*)"):
                for group in self.groups:
                    self.add_lazy_command(greedy_command, group)

    def is_greedy(self, val: str) -> bool:
        """Greedy strings must contain (*)- marked to be evaluated lazily."""
        return "(*)" in val

    def add_group(self, group: Group) -> None:
        raise NotImplementedError

    def add_base_imports(self) -> None:
        raise NotImplementedError

    def add_base_cli(self) -> None:
        raise NotImplementedError

    def add_root_command(self, command: Command) -> None:
        raise NotImplementedError

    def add_group_command(self, command: Command) -> None:
        raise NotImplementedError

    def add_sub_command(self, command: Command, group: Group) -> None:
        raise NotImplementedError

    def add_main_block(self) -> None:
        raise NotImplementedError

    def from_greedy_make_lazy_command(self, greedy_command: Command, group: str) -> Command:
        """
        Convert a greedy command to a lazy command by replacing placeholders with a specific group name.

        This method creates a deep copy of the input greedy command and replaces all occurrences of 
        greedy placeholders ('{(*)}' and '(*)') with the provided group name across various command attributes.

        Parameters:
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


def generate_cli(manifest: CLIManifest, commander_cls: type[Commander] = Commander) -> CLI:
    """
    Generate a CLI object from a CLI manifest using the specified commander class.

    Parameters:
        manifest (CLIManifest): The manifest containing CLI configuration details
        commander_cls (type[Commander], optional): Commander class to use for CLI generation. Defaults to Commander.

    Returns:
        CLI: A CLI object with generated code, name, version, and required dependencies
    """
    commander = commander_cls(manifest)
    commander.generate_cli()
    return CLI(name=manifest.name, version=manifest.version, code=commander.cli, requires=manifest.requires)
