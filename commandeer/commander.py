from collections import namedtuple

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
        self.add_imports()
        self.add_base_cli()
        self.add_functions()
        commands = self.command_config["commands"]
        for name, script in commands.items():
            current_command = Command(name, script)
            if '.' in name:
                group = name.split('.')[:-1][-1]
                self.add_sub_command(current_command, group)
            else:
                self.add_group_command(current_command)

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
