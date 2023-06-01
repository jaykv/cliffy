from datetime import datetime
from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from ..helper import wrap_as_comment, wrap_as_var

COMMAND_BLOCK = Union[str, list[Union[str, dict[Literal["help"], str]]]]


class CLIManifest(BaseModel):
    name: str = Field(
        description="The name of the CLI. "
        "This will be used as the script name when invoking the CLI from the command line."
    )
    version: str = Field(
        description="The version of the CLI. "
        "This should follow the standard semantic versioning format (e.g., 'MAJOR.MINOR.PATCH')."
    )
    help: str = Field(
        "",
        description="A brief description of the CLI that is displayed when the user invokes the --help or -h option.",
    )
    requires: list[str] = Field(
        [],
        description="List of Python dependencies required for the CLI. Validated on CLI load, update and build. "
        "Supports basic requirements specifier syntax.",
    )
    includes: list[str] = Field(
        [],
        description="List of external CLI manifest paths to include into the main manifest. "
        "Performs a deep merge of manifests sequentially in the order given to assemble a merged manifest. "
        "and finally, deep merges the merged manifest with the main manifest.",
    )
    vars: dict[str, Union[str, dict[str, None]]] = Field(
        {},
        description="A mapping defining manifest variables that can be referenced in any other blocks. "
        "Environments variables can be used in this section with ${some_env_var} for dynamic parsing. "
        "Supports jinja2 formatted expressions as values. "
        "Interpolate defined vars in other blocks jinja2-styled {{ var_name }}.",
    )
    commands: dict[str, COMMAND_BLOCK] = Field(
        {},
        description="A mapping containing the command definitions for the CLI. "
        "Each command should have a unique key- which can be either a group command or nested subcommands. "
        "Nested subcommands are joined by '.' in between each level. "
        "A special (*) wildcard can be used to spread the subcommand to all group-level commands. "
        "The value is the python code to run when the command is called "
        "OR a list of bash commands to run (prefixed with $).",
    )
    imports: Union[str, list[str]] = Field(
        "",
        description="A string block or list of strings containing any module imports. "
        "These can be used to import any python modules that the CLI depends on.",
    )
    functions: list[str] = Field(
        [],
        description="A list containing any helper functions. "
        "Each element of the list can be a separate function. "
        "These functions should be defined as strings that can be executed by the Python interpreter.",
    )
    args: dict[str, list[dict[str, str]]] = Field(
        {},
        description="A mapping containing the arguments and options for each command. "
        "Each key in the mapping should correspond to a command in the commands section. "
        "The value should be a list of mappings representing the params and options for that command.",
    )
    types: dict[str, str] = Field(
        {},
        description="A mapping containing any shared type definitions. "
        "These types can be referenced by name in the args section to provide type annotations "
        "for params and options defined in the args section.",
    )
    cli_options: dict[str, Any] = Field(
        {},
        description="A mapping for any additional options that can be used to customize the behavior of the CLI.",
    )

    @classmethod
    def get_field_description(cls, field_name: str, as_comment: bool = True) -> str:
        field = cls.model_fields.get(field_name)
        if field and field.description:
            if as_comment:
                return wrap_as_comment(field.description, split_on=". ")
            return field.description
        return ""

    @classmethod
    def get_template(cls, name: str) -> str:
        return f"""# cliffy v1 template
manifestVersion: v1

{cls.get_field_description('name')}
name: {name} 

{cls.get_field_description('version')}
version: 0.1.0

{cls.get_field_description('help')}
help: hello world

{cls.get_field_description('includes')}
includes: []

{cls.get_field_description('requires')}
requires: []

{cls.get_field_description('vars')}
vars:
    default_mood: happy
    debug_mode: "{{ env['DEBUG'] or 'False' }}"

{cls.get_field_description('imports')}
imports:
    - import os
    - |
        from collections import defaultdict
        import re

{cls.get_field_description('functions')}
functions:
    - |
        def greet_name(name: str):
            print("hello " + name)

{cls.get_field_description('types')}
types:
    Language: str = typer.Option("english", "-l", help="Language to greet in", prompt=True)

{cls.get_field_description('args')}
args:
    world: [--name|-n: str!]                      # a REQUIRED option
    greet.all: 
        - names: str!                             # a REQUIRED param as denoted by the ! at the end
        - mood: str = "{wrap_as_var("default_mood")}"          # an OPTIONAL param that uses a manifest var as default
        - --language: Language                    # an option with a default that uses Language type as arg definition

{cls.get_field_description('commands')}
commands:
    # this is a parent command that will get invoked with: hello world
    world: 
        - |
            \"\"\"
            Help text for list
            \"\"\"
            greet_name("world")
        - $ echo "i can also mix-and-match this command script to run bash commands"
    
    # this is a nested command that will get invoked with: hello greet all
    greet.all: 
        - help: Help text for list.all       # you can also define help text like this
        - $ echo "hello all"                 # this is a bash command that will get converted to python subprocess call
        - print("greetings from python")     # this python code will get directly invoked

"""

    @classmethod
    def get_raw_template(cls, name: str) -> str:
        return f"""
# cliffy v1 raw template

manifestVersion: v1

{cls.get_field_description('name')}
name: {name} 

{cls.get_field_description('version')}
version: 0.1.0

{cls.get_field_description('help')}
help: 

{cls.get_field_description('includes')}
includes: []

{cls.get_field_description('vars')}
vars: {{}}

{cls.get_field_description('imports')}
imports: []

{cls.get_field_description('functions')}
functions: []

{cls.get_field_description('types')}
types: {{}}

{cls.get_field_description('args')}
args: {{}}

{cls.get_field_description('commands')}
commands: {{}}

"""


class IncludeManifest(BaseModel):
    """Special manifest specifically to define the allowed named objects that can be included"""

    commands: dict[str, Union[str, list[Union[str, dict[Literal["help"], str]]]]] = {}
    imports: Union[str, list[str]] = []
    functions: list[str] = []
    args: dict[str, list[dict[str, str]]] = {}
    types: dict[str, str] = {}
    cli_options: dict[str, str] = {}
    requires: list[str]


class CLIMetadata(BaseModel):
    """Metadata model"""

    cli_name: str
    runner_path: str
    version: str
    loaded: datetime
    manifest: str
    requires: list[str]
