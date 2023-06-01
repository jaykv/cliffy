from collections import defaultdict
from typing import DefaultDict

from pybash.transformer import transform as transform_bash
from pydantic import BaseModel

from .manifests import COMMAND_BLOCK, Manifest
from .parser import Parser


class Command(BaseModel):
    name: str
    script: COMMAND_BLOCK


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

    __slots__ = ("manifest", "parser", "cli", "groups", "greedy", "commands", "root_commands")

    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest
        self.parser = Parser(self.manifest)
        self.cli: str = ""
        self.groups: dict[str, Group] = {}
        self.greedy: list[Command] = []
        self.commands: list[Command] = [
            Command(name=name, script=script) for name, script in self.manifest.commands.items()
        ]
        self.root_commands: list[Command] = [command for command in self.commands if "." not in command.name]
        self.build_groups()

    def build_groups(self) -> None:
        groups: DefaultDict[str, list[Command]] = defaultdict(list)
        group_help_dict: dict[str, str] = {}
        for command in self.commands:
            # Check for greedy commands- evaluate them at the end
            if self.is_greedy(command.name):
                self.greedy.append(command)
                continue

            if "." in command.name:
                group_name = command.name.split(".")[:-1][-1]
                groups[group_name].append(command)
            else:
                for script_block in command.script:
                    if isinstance(script_block, dict) and script_block.get("help"):
                        group_help = script_block["help"]
                        group_help_dict[command.name] = group_help

        for group_name, commands in groups.items():
            self.groups[group_name] = Group(
                name=group_name, commands=commands, help=group_help_dict.get(group_name, "")
            )

    def build_cli(self) -> None:
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

    def add_greedy_commands(self) -> None:
        """Greedy commands get lazy-loaded. Only supported for group-commands currently"""
        for greedy_command in self.greedy:
            if greedy_command.name.startswith("(*)"):
                for group in self.groups:
                    # make it lazy and interpolate
                    lazy_command_name = greedy_command.name.replace("(*)", group)
                    lazy_command_script = ""
                    if isinstance(greedy_command.script, str):
                        lazy_command_script = greedy_command.script.replace("{(*)}", group)
                    elif isinstance(greedy_command.script, list):
                        lazy_command_script = []
                        for script_block in greedy_command.script:
                            if isinstance(script_block, dict):
                                lazy_command_script.append(script_block["help"].replace("{(*)}", group))
                            else:
                                lazy_command_script.append(script_block.replace("{(*)}", group))

                    if greedy_command_args := self.manifest.args.get(greedy_command.name):
                        self.manifest.args[lazy_command_name] = greedy_command_args

                    # lazy load
                    lazy_command = Command(name=lazy_command_name, script=lazy_command_script)
                    self.commands.append(lazy_command)
                    self.add_command(lazy_command)

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


def build_cli(manifest: Manifest, commander_cls=Commander) -> CLI:
    commander = commander_cls(manifest)
    commander.build_cli()
    return CLI(name=manifest.name, version=manifest.version, code=commander.cli, requires=manifest.requires)
