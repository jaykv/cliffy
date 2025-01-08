from typing import Any, Optional, Union
from pydantic import BaseModel, Field
from .helper import wrap_as_comment
from datetime import datetime


class CommandArg(BaseModel):
    name: str
    type: str
    default: Any = None
    help: Optional[str] = None
    short: Optional[str] = None
    required: bool = False


ArgBlock = Union[dict[str, str], CommandArg, str]
VarBlock = Union[str, dict[str, None]]


class Command(BaseModel):
    run: Union[str, list[str]] = ""
    help: Optional[str] = None
    args: Optional[list[ArgBlock]] = []
    template: Optional[str] = None
    pre_run: Optional[str] = None
    post_run: Optional[str] = None
    aliases: list[str] = []
    name: str = ""


CommandBlock = Union[Command, str, list[str]]


class CommandTemplate(BaseModel):
    args: list[ArgBlock] = []
    pre_run: Optional[str] = None
    post_run: Optional[str] = None


class CLIManifest(BaseModel):
    manifestVersion: str = "v2"
    name: str = Field(..., description="The name of the CLI, used when invoking from command line.")
    version: str = Field(..., description="CLI version")
    help: str = Field("", description="Brief description of the CLI")

    requires: list[str] = Field(
        default=[],
        description="List of Python package dependencies for the CLI." "Supports requirements specifier syntax.",
    )
    includes: list[str] = Field(
        default=[],
        description="List of external CLI manifests to include."
        "Performs a deep merge of manifests sequentially in the order given to assemble a merged manifest. "
        "and finally, deep merges the merged manifest with this manifest.",
    )

    vars: dict[str, VarBlock] = Field(
        default_factory=dict,
        description="Mapping defining manifest variables that can be referenced in any other blocks. "
        "Environments variables can be used in this section with ${some_env_var} for dynamic parsing. "
        "Supports jinja2 formatted expressions as values. "
        "Interpolate defined vars in other blocks jinja2-styled {{ var_name }}.",
    )
    imports: Union[str, list[str]] = Field(
        default=[],
        description="String block or list of strings containing any module imports. "
        "These can be used to import any python modules that the CLI depends on.",
    )
    functions: list[str] = Field(
        default=[],
        description="List of helper function definitions. "
        "These functions should be defined as strings that can be executed by the Python interpreter.",
    )

    types: dict[str, str] = Field(
        default_factory=dict,
        description="A mapping containing any shared type definitions. "
        "These types can be referenced by name in the args section to provide type annotations "
        "for params and options defined in the args section.",
    )

    global_args: list[ArgBlock] = Field(default=[], description="Arguments applied to all commands")

    command_templates: dict[str, CommandTemplate] = Field(
        default_factory=dict, description="Reusable command templates"
    )

    commands: dict[str, CommandBlock] = Field(
        ...,
        description="A mapping containing the command definitions for the CLI. "
        "Each command should have a unique key- which can be either a group command or nested subcommands. "
        "Nested subcommands are joined by '.' in between each level. "
        "Aliases for commands can be separated in the key by '|'. "
        "A special '(*)' wildcard can be used to spread the subcommand to all group-level commands",
    )

    cli_options: dict[str, Any] = Field(default_factory=dict, description="Additional CLI configuration options")

    tests: list[Union[str, dict[str, str]]] = Field(default=[], description="Test cases for commands")

    class Config:
        extra = "allow"

    @classmethod
    def get_field_description(cls, field_name: str, as_comment: bool = True) -> str:
        field = cls.model_fields.get(field_name)
        if not field or not field.description:
            return ""

        if as_comment:
            return wrap_as_comment(field.description, split_on=". ")
        return field.description

    @property
    def args(self):
        for command in self.commands.values():
            if isinstance(command, str):
                continue

            if isinstance(command, dict):
                for sub_command in command.values():
                    yield from sub_command.args
            elif isinstance(command, Command) and command.args:
                yield from command.args

    @classmethod
    def get_template(cls, cli_name: str) -> str:
        return f"""manifestVersion: v2

{cls.get_field_description('name')}
name: {cli_name}

{cls.get_field_description('version')}
version: 0.1.0

{cls.get_field_description('help')}
help: A brief description of your CLI

{cls.get_field_description('requires')}
requires: []
  # - requests>=2.25.1
  # - pyyaml~=5.4

{cls.get_field_description('includes')}
includes: []
  # - path/to/other/manifest.yaml

{cls.get_field_description('vars')}
vars:
  data_file: "data.json"
  debug_mode: "{{{{ env['DEBUG'] or 'False' }}}}"

{cls.get_field_description('imports')}
imports: |
  import json
  import os
  from pathlib import Path

{cls.get_field_description('functions')}
functions:
  - |
    def load_data() -> dict:
        data_path = Path("{{{{ data_file }}}}")
        if data_path.exists():
            with data_path.open() as f:
                return json.load(f)
        return {{}}
  - |
      def save_data(data):
          with open("{{{{data_file}}}}", "w") as f:
              json.dump(data, f, indent=2)
{cls.get_field_description('types')}
types:
  Filename: str = typer.Argument(..., help="Name of the file to process")
  Verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")

{cls.get_field_description('global_args')}
global_args:
  - verbose: Verbose

{cls.get_field_description('command_templates')}
command_templates:
  with_confirmation:
    args:
      - "yes": bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
    pre_run: |
      if not yes:
        typer.confirm("Are you sure you want to proceed?", abort=True)

{cls.get_field_description('commands')}
commands:
  hello:
    help: Greet the user
    args:
      - name: str = typer.Option("World", "--name", "-n", help="Name to greet")
    run: |
      print(f"Hello, {{name}}!")
      $ echo "i can also mix-and-match this command script to run shell commands"

  file.process:
    help: Process a file
    args:
      - filename: Filename
    run: |
      data = load_data()
      print(f"Processing {{filename}}")
      if verbose:
        print("Verbose output enabled")
      data["processed"] = [filename]
      # Process the file here
      save_data(data)

  delete|rm:
    help: Delete a file
    template: with_confirmation
    args: [filename: Filename]
    run: |
      if verbose:
        print(f"Deleting {{filename}}")
      os.remove(filename)
      print("File deleted successfully")

{cls.get_field_description('cli_options')}
cli_options:
  rich_help_panel: True

{cls.get_field_description('tests')}
tests:
  - hello --name Alice: assert 'Hello, Alice!' in result.output
  - file process test.txt: assert 'Processing test.txt' in result.output
"""

    @classmethod
    def get_raw_template(cls, cli_name: str) -> str:
        return f"""
manifestVersion: v2

name: {cli_name}
version: 0.1.0
help: A brief description of your CLI

requires: []

includes: []

vars: {{}}

imports: ""

functions: []

types: {{}}

global_args: []

command_templates: {{}}

commands: {{}}

cli_options: {{}}

tests: []
"""


class IncludeManifest(BaseModel):
    """Special manifest specifically to define the allowed named objects that can be included"""

    requires: list[str]
    commands: dict[str, CommandBlock] = {}
    vars: dict[str, VarBlock] = {}
    imports: Union[str, list[str]] = []
    functions: list[str] = []
    types: dict[str, str] = {}
    cli_options: dict[str, str] = {}
    tests: list[Union[str, dict[str, str]]] = []


class CLIMetadata(BaseModel):
    """Metadata model"""

    cli_name: str
    runner_path: str
    version: str
    loaded: datetime
    manifest: str
    requires: list[str]


if __name__ == "__main__":
    yaml_template = CLIManifest.get_raw_template(cli_name="mycli")
    print(yaml_template)

    # You could also create an instance and validate it:
    # import yaml
    # manifest_dict = yaml.safe_load(yaml_template)
    # manifest = CLIManifest(**manifest_dict)
    # print(manifest.json(indent=2))
