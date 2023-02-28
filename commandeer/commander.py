from collections import defaultdict, namedtuple

from .parser import Parser

Command = namedtuple('Command', ['name', 'script'])
CLI = namedtuple('CLI', ['name', 'version', 'code'])


class Commander:
    """Generates commands based on the command config"""

    def __init__(self, command_config: dict) -> None:
        self.command_config: dict = command_config
        self.commands: dict = self.command_config.get("commands", {})
        self.functions: dict = self.command_config.get("functions", {})
        self.imports: str = self.command_config.get("imports", "")
        self.parser: Parser = Parser(self.command_config)
        self.cli: str = ""
        self.groups: dict = defaultdict(lambda: defaultdict())
        self.greedy: list = []
        self.help: str = self.command_config.get("help")
        self.cli_options: dict = self.command_config.get("cli_options", {})

    def build_cli(self) -> None:
        self.add_base_imports()
        self.add_imports()
        self.add_base_cli()
        self.add_functions()
        for name, script in self.commands.items():
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

            # Add the group
            if group not in self.groups:
                self.add_group(group, command)

            # Save to groups dict
            self.groups[group][command.name] = command

            # Add the subcommand
            self.add_sub_command(command, group)
        else:
            # Group command- top-level commands
            if command.name not in self.groups:
                self.groups[command.name] = {}

            # Add the group command
            self.add_group_command(command)

    def add_imports(self) -> None:
        if self.imports:
            self.cli += self.imports

    def add_functions(self) -> None:
        for func_name, func in self.functions.items():
            params, body = func
            self.cli += f"""
def {func_name}({params}):
{self.parser.indent_block(body)}

"""

    def add_greedy_commands(self) -> None:
        """Greedy commands get lazy-loaded. Only supported for group-commands currently"""
        for greedy_command in self.greedy:
            if greedy_command.name.startswith('(*)'):
                for group in self.groups:
                    # make it lazy and interpolate
                    lazy_command_name = greedy_command.name.replace('(*)', group)
                    lazy_command_script = greedy_command.script.replace('{{(*)}}', group)

                    # lazy load the greedy args
                    greedy_command_args = self.parser.args.get(greedy_command.name)
                    if greedy_command_args:
                        self.parser.args[lazy_command_name] = greedy_command_args

                    # lazy parse
                    self.add_command(Command(lazy_command_name, lazy_command_script))

    def is_greedy(self, val: str) -> bool:
        """Greedy strings must contain (*)- marked to be evaluated lazily."""
        return '(*)' in val

    def add_group(self) -> None:
        raise NotImplementedError

    def add_base_imports(self) -> None:
        raise NotImplementedError

    def add_base_cli(self) -> None:
        raise NotImplementedError

    def add_group_command(self, command: Command) -> None:
        raise NotImplementedError

    def add_sub_command(self, command: Command, group: str) -> None:
        raise NotImplementedError


def build_cli(command_config: dict, commander_cls=Commander) -> CLI:
    commander = commander_cls(command_config)
    commander.build_cli()
    return CLI(command_config['name'], command_config['version'], commander.cli)
