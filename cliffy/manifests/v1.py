from typing import Union

from pydantic import BaseModel, Field


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
    commands: dict[str, Union[str, list[str]]] = Field(
        {},
        description="A dictionary containing the command definitions for the CLI. "
        "Each command should have a unique key, which can either reference nested subcommands joined by '.' "
        "in between each level OR just a parent-level command. The value is the python code to run "
        "when the command is called OR a list of bash commands to run (prefixed with $).",
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
    args: dict[str, list] = Field(
        {},
        description="A dictionary containing the arguments and options for each command. "
        "Each key in the dictionary should correspond to a command in the commands section "
        "and the value should be a list of dictionaries representing the params and options for that command.",
    )
    types: dict[str, str] = Field(
        {},
        description="A dictionary containing any shared type definitions. "
        "These types can be referenced by name in the args section to provide type annotations "
        "for params and options defined in the args section.",
    )
    cli_options: dict[str, str] = Field(
        {},
        Description="A dictionary for any additional options that can be used to customize the behavior of the CLI.",
    )
