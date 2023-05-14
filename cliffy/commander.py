from collections import defaultdict, namedtuple
from typing import DefaultDict

from .manifests import Manifest
from .parser import Parser

Command = namedtuple('Command', ['name', 'script'])
CLI = namedtuple('CLI', ['name', 'version', 'code'])


class Commander:
    """Generates commands based on the command config"""

    __slots__ = ('manifest', 'parser', 'cli', 'groups', 'greedy')

    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest
        self.parser = Parser(self.manifest)
        self.cli: str = ""
        self.groups: DefaultDict[str, dict] = defaultdict(lambda: defaultdict())
        self.greedy: list[Command] = []

    def build_cli(self) -> None:
        self.add_base_imports()
        self.add_imports()
        self.add_base_cli()
        self.add_functions()
        for name, script in self.manifest.commands.items():
            current_command = Command(name, script)
            self.add_command(current_command)

        self.add_greedy_commands()

    def add_command(self, command: Command) -> None:
        # Check for greedy commands- evaluate them at the end
        if self.is_greedy(command.name):
            self.greedy.append(command)
            return

        if '.' in command.name:
            # Sub command- nested commands
            group = command.name.split('.')[:-1][-1]

            if group not in self.groups:
                self.add_group(group, command)

            self.groups[group][command.name] = command
            self.add_sub_command(command, group)
        else:
            # Group command- top-level commands
            if command.name not in self.groups:
                self.groups[command.name] = {}

                # TODO: by default, add a group app from here to allow for group-level invokes
                # self.add_group(command.name, command)

            self.add_group_command(command)

    def add_imports(self) -> None:
        if isinstance(self.manifest.imports, str):
            self.cli += self.manifest.imports + "\n"
        elif isinstance(self.manifest.imports, list):
            for _import in self.manifest.imports:
                self.cli += _import + "\n"

    def add_functions(self) -> None:
        self.cli += "\n"
        for func in self.manifest.functions:
            self.cli += f"{func}"
        self.cli += "\n"

    def add_greedy_commands(self) -> None:
        """Greedy commands get lazy-loaded. Only supported for group-commands currently"""
        for greedy_command in self.greedy:
            if greedy_command.name.startswith('(*)'):
                for group in self.groups:
                    # make it lazy and interpolate
                    lazy_command_name = greedy_command.name.replace('(*)', group)
                    lazy_command_script = greedy_command.script.replace('{(*)}', group)

                    if greedy_command_args := self.manifest.args.get(greedy_command.name):
                        self.manifest.args[lazy_command_name] = greedy_command_args

                    # lazy parse
                    self.add_command(Command(lazy_command_name, lazy_command_script))

    def is_greedy(self, val: str) -> bool:
        """Greedy strings must contain (*)- marked to be evaluated lazily."""
        return '(*)' in val

    def add_group(self, group: str, command: Command) -> None:
        raise NotImplementedError

    def add_base_imports(self) -> None:
        raise NotImplementedError

    def add_base_cli(self) -> None:
        raise NotImplementedError

    def add_group_command(self, command: Command) -> None:
        raise NotImplementedError

    def add_sub_command(self, command: Command, group: str) -> None:
        raise NotImplementedError


def build_cli(manifest: Manifest, commander_cls=Commander) -> CLI:
    commander = commander_cls(manifest)
    commander.build_cli()
    return CLI(manifest.name, manifest.version, commander.cli)
