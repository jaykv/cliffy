from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

from pybash.transformer import transform as transform_bash
from pydantic import BaseModel

from .manifest import ArgBlock, CLIManifest, Command, CommandArg
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
                aliases = command.name.split("|")

                # skip group command aliases
                if "." in aliases[0]:
                    continue

                command.name = aliases[0]  # update command.name without the alias part
                for alias in aliases[1:]:
                    command.aliases.append(alias)
                    self.aliases_by_commands[command.name].append(alias)

    def build_groups(self) -> None:
        groups: DefaultDict[str, list[Command]] = defaultdict(list)
        group_help_dict = {}

        for command in self.commands:
            if not command.name:
                raise ValueError("Command name is missing :(")
            # Check for greedy commands- evaluate them at the end
            if self.is_greedy(command.name):
                self.greedy.append(command)
                continue

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

    def add_lazy_command(self, greedy_command: Command, group: str):
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
        lazy_command = greedy_command.model_copy(deep=True)
        lazy_command.name = greedy_command.name.replace("(*)", group)
        if isinstance(lazy_command.run, str):
            lazy_command.run = lazy_command.run.replace("{(*)}", group)
        elif isinstance(lazy_command.run, list):
            lazy_command.run = [script_block.replace("{(*)}", group) for script_block in lazy_command.run]
        if lazy_command.help:
            lazy_command.help = lazy_command.help.replace("{(*)}", group)

        if lazy_command.template:
            lazy_command.template.replace("{(*)}", group)

        if lazy_command.pre_run:
            lazy_command.pre_run.replace("{(*)}", group)

        if lazy_command.post_run:
            lazy_command.post_run.replace("{(*)}", group)

        if lazy_command.args:
            if isinstance(lazy_command.args, str):
                lazy_command.args.replace("{(*)}", group)
            elif isinstance(lazy_command.args, list):
                lazy_parsed_args: list[ArgBlock] = []
                for arg in lazy_command.args:
                    if isinstance(arg, str):
                        lazy_parsed_args.append(arg.replace("{(*)}", group))
                    if isinstance(arg, CommandArg):
                        if arg.help:
                            arg.help = arg.help.replace("{(*)}", group)
                        if arg.default:
                            arg.default = arg.default.replace("{(*)}", group)
                        if arg.short:
                            arg.short = arg.short.replace("{(*)}", group)
                        lazy_parsed_args.append(arg)
                    if isinstance(arg, dict):
                        lazy_parsed_args.append(arg)
                lazy_command.args = lazy_parsed_args
        return lazy_command


def generate_cli(manifest: CLIManifest, commander_cls=Commander) -> CLI:
    commander = commander_cls(manifest)
    commander.generate_cli()
    return CLI(name=manifest.name, version=manifest.version, code=commander.cli, requires=manifest.requires)
