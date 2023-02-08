from collections import namedtuple, defaultdict

from .parser import Parser

Command = namedtuple('Command', ['name', 'script'])
CLI = namedtuple('CLI', ['name', 'version', 'code'])


class Commander:
    """Generates commands based on the command config"""

    def __init__(self, command_config: dict) -> None:
        self.command_config = command_config
        self.parser = Parser(command_config)
        self.cli = ""

    def build_cli(self):
        self.groups = defaultdict(lambda: defaultdict())
        self.greedy = []
        self.add_imports()
        self.add_base_cli()
        self.add_functions()
        commands = self.command_config["commands"]
        for name, script in commands.items():
            current_command = Command(name, script)
            self.parse_command(current_command)
            
        self.parse_greedy_commands()
        
    def parse_command(self, command: Command):
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
                
    def add_functions(self):
        funcs = self.command_config.get('functions')
        if not funcs:
            return

        for func_name, func in funcs.items():
            params, body = func
            self.cli += f"""
def {func_name}({params}):
    {body}

"""

    def parse_greedy_commands(self):
        """Greedy commands get lazy-loaded. Only supported for group-commands currently"""
        
        for greedy_command in self.greedy:
            if greedy_command.name.startswith('(*)'):
                for group in self.groups:
                    # make it lazy
                    lazy_command_name = greedy_command.name.replace('(*)', group)
                    lazy_command_script = greedy_command.script.replace('{{(*)}}', group)   
                    
                    # lazy load the greedy args
                    greedy_command_args = self.parser.args.get(greedy_command.name)
                    if greedy_command_args:
                        self.parser.args[lazy_command_name] = greedy_command_args
                        
                    # lazy parse
                    self.parse_command(Command(lazy_command_name, lazy_command_script))

    def is_greedy(self, val: str):
        """Greedy strings must contain (*)- marked to be evaluated lazily."""
        return '(*)' in val

    def add_group(self):
        raise NotImplementedError
    
    def add_imports(self):
        raise NotImplementedError

    def add_base_cli(self):
        raise NotImplementedError

    def add_group_command(self, command: Command):
        raise NotImplementedError

    def add_sub_command(self, command: Command, group: str):
        raise NotImplementedError


def build_cli(command_config: dict, commander_cls=Commander) -> CLI:
    commander = commander_cls(command_config)
    commander.build_cli()
    return CLI(command_config['name'], command_config['version'], commander.cli)
