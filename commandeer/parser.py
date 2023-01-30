## Command parser
import pybash


class Parser:
    def __init__(self, command_config) -> None:
        self.command_config = command_config

    def parse(self, script: str):
        ## Bash commands start with $
        if script.startswith('$'):
            script = '>' + script[1:]
            return pybash.Transformer.transform_source(script)

        return script
