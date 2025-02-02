from functools import cached_property
from typing import Any, ItemsView, Iterator, Optional, Union
from pydantic import BaseModel, Field, RootModel, field_validator, ValidationInfo
from .helper import wrap_as_comment
from datetime import datetime
import sys

LATEST_SCHEMA_VERSION = "v3"


class Example(BaseModel):
    command: str
    description: str


class GenericCommandParam(RootModel):
    root: str = Field(
        json_schema_extra={"title": "Generic Command Param\nGets appended to the command params signature."}
    )


class SimpleCommandParam(RootModel):
    root: dict[str, str] = Field(
        json_schema_extra={
            "title": "Simple Command Param\nBuild params with key as the param name and value as the type and default vals, i.e. `verbose: bool = typer.Option(...)`"
        },
        min_length=1,
        max_length=1,
    )

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        return iter(self.root)

    def items(self) -> ItemsView[str, str]:  # type: ignore[override]
        return self.root.items()

    @cached_property
    def raw_name(self) -> str:
        return next(iter(self.root)).strip()

    @property
    def raw_type(self) -> str:
        return self.root[self.raw_name]

    @property
    def name(self) -> str:
        return self.raw_name.split("|")[0] if "|" in self.raw_name else self.raw_name

    @property
    def type(self) -> str:
        parsed_type = self.raw_type.split("=")[0].strip() if "=" in self.raw_type else self.raw_type
        return parsed_type.rstrip("!")

    @property
    def required(self) -> bool:
        return self.raw_type.endswith("!")

    @property
    def default(self) -> Optional[str]:
        return self.raw_type.split("=")[1].strip() if "=" in self.raw_type else None

    @property
    def short(self) -> Optional[str]:
        return self.raw_name.split("|")[1] if "|" in self.raw_name else None

    def is_option(self) -> bool:
        return self.raw_name.startswith("-")

    @property
    def help(self) -> str:
        return ""


class CommandParam(BaseModel):
    """
    Defines the structure of a command parameter. It is used
    within the `params` field of a `Command` object.

    By default, parameters are treated as positional arguments. To specify an option, prefix the name with `--` to indicate flag.
    """

    name: str = Field(..., description="Parameter name. Prefix with `--` to indicate an option.")
    type: str = Field(
        ...,
        description="Parameter type (e.g., 'str', 'int', 'bool', or a custom type defined in the manifest's 'types' section).",
    )
    default: Any = Field(default=None, description="Default parameter value.")
    help: str = Field(default="", description="Parameter description.")
    short: str = Field(default="", description="Short option alias. i.e. '-v' for verbose.")
    required: bool = Field(default=False, description="Whether the parameter is required.")

    @field_validator("short", mode="after")
    @classmethod
    def short_only_with_option(cls, v: str, info: ValidationInfo) -> str:
        """
        Raises:
            ValueError: If a short alias is provided without a flag-style parameter name.

        Example:
            # Valid: Short alias with flag parameter
            param = CommandParam(name='--verbose', short='v')

            # Invalid: Short alias without flag parameter
            param = CommandParam(name='verbose', short='v')  # Raises ValueError
        """
        if v and not info.data.get("name", "").startswith("--"):
            raise ValueError("short can only be used when name is prefixed as flag: `--`.")
        return v

    def is_option(self) -> bool:
        return self.name.strip().startswith("--")


ParamBlock = Union[CommandParam, SimpleCommandParam, GenericCommandParam]
VarBlock = Union[str, dict[str, None]]


class CommandConfig(BaseModel):
    """Configuration options for a Cliffy command."""

    context_settings: dict[Any, Any] = Field(
        default={},
        description="""Arbitrary settings passed to Click's context. Useful for things
        like overriding the default `max_content_width`.
        See Click's documentation for more details:
        https://click.palletsprojects.com/en/8.1.x/advanced/#context-settings""",
    )
    epilog: str = Field(default="", description="Text displayed after the help message.")
    short_help: str = Field(default="", description="Short one-line help message displayed in help overviews.")
    options_metavar: str = Field(
        default="[OPTIONS]", description="Placeholder text displayed for options in help messages."
    )
    add_help_option: bool = Field(default=True, description="Whether to add the `--help` option automatically.")
    no_args_is_help: bool = Field(
        default=False,
        description="If True, invoking the command without any arguments displays the help message.",
    )
    hidden: bool = Field(
        default=False, description="If True, the command is hidden from help messages and command lists."
    )
    deprecated: bool = Field(
        default=False, description="If True, the command is marked as deprecated in help messages."
    )
    rich_help_panel: str = Field(
        default="",
        description="""Name of a Rich help panel to display after the default help. This is useful for
        displaying more complex help information, such as tables or formatted text.
        The content of the panel is defined using the `@rich_help` decorator.""",
    )


class RunBlock(RootModel):
    root: str = Field(
        json_schema_extra={"title": "Command Run Block"},
        description="Command execution logic. Lines prefixed with '$' are treated as shell commands.",
    )

    def __bool__(self) -> bool:
        return bool(self.root)


class PreRunBlock(RunBlock):
    root: str = Field(json_schema_extra={"title": "Pre-run Block"})


class PostRunBlock(RunBlock):
    root: str = Field(json_schema_extra={"title": "Post-run Block"})


class RunBlockList(RootModel):
    root: list[RunBlock] = Field(
        json_schema_extra={"title": "Run Block List\nList of Run Blocks executed in order."},
    )

    def __iter__(self) -> Iterator[RunBlock]:  # type: ignore[override]
        return iter(self.root)

    def __getitem__(self, item: int) -> RunBlock:
        return self.root[item]

    def to_script(self) -> str:
        return "\n".join(run.root for run in self.root)


class Command(BaseModel):
    """
    Defines a single command within the CLI. It specifies the command's execution logic,
    parameters, and configuration.
    """

    run: Union[RunBlock, RunBlockList] = Field(
        default=RunBlock(root=""),
    )
    help: str = Field(default="", description="A description of the command, displayed in the help output.")
    params: list[ParamBlock] = Field(
        default=[],
        description="A list of parameters for the command.\nThere are three ways to define a param: \n(generic) 1. A string as param definition. Gets appended to the command params signature.\n(implicit) 2. A mapping with the param name as the key and the type as the value. Custom types are accepted here. Same as the implicit v1 params syntax. \n(explicit) 3. A mapping with the following keys: `name` (required), `type` (required), `default` (None by default), `help` (Optional), `short` (Optional), `required` (False by default).",
    )
    template: str = Field(
        default="",
        description="A reference to a command template defined in the `command_templates` section of the manifest. This allows for reusable command definitions.",
    )
    pre_run: PreRunBlock = Field(
        default=PreRunBlock(root=""),
        description="Script to run before the command's run block. This can be used for setup tasks or preconditions.",
    )
    post_run: PostRunBlock = Field(
        default=PostRunBlock(root=""),
        description="Script to run after the command's run block. This can be used for cleanup tasks or post-processing.",
    )
    aliases: list[str] = Field(
        default=[],
        description="A list of aliases for the command. These aliases can be used to invoke the command with a different name.",
    )
    name: str = Field(
        default="",
        description="The name of the command. This is generally derived from the key in the `commands` section of the manifest, but can be explicitly set here.",
    )
    config: Optional[CommandConfig] = Field(
        default=None,
        description="An optional `CommandConfig` object that provides additional configuration options for the command, such as context settings, help text customization, and visibility.",
    )


CommandBlock = Union[Command, RunBlock, RunBlockList]


class CommandTemplate(BaseModel):
    """
    Defines a reusable template for command definitions.  Templates allow you to define
    common parameters, pre-run/post-run scripts, and configuration options that can be
    applied to multiple commands.
    """

    params: list[ParamBlock] = Field(
        default=[],
        description="A list of parameters for the command template.  These parameters will be applied to any command that uses this template.",
    )
    pre_run: PreRunBlock = Field(
        default=PreRunBlock(root=""),
        description="Script to run before the command's run and pre-run block. This script will be applied to any command that uses this template.",
    )
    post_run: PostRunBlock = Field(
        default=PostRunBlock(root=""),
        description="Script to run after the command's run and post-run block. This script will be applied to any command that uses this template.",
    )
    config: Optional[CommandConfig] = Field(
        default=None,
        description="Additional configuration options for commands using this template. This allows customization of help text, context settings, and other Typer command parameters.",
    )


class CLIManifest(BaseModel):
    manifestVersion: str = LATEST_SCHEMA_VERSION
    name: str = Field(..., description="The name of the CLI, used when invoking from command line.")
    version: str = Field(..., description="CLI version")
    help: str = Field(default="", description="Brief description of the CLI")
    use_click: bool = Field(default=False, description="Generate CLI to Click instead of Typer")
    requires: list[str] = Field(
        default=[],
        description="List of Python package dependencies for the CLI.Supports requirements specifier syntax.",
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
    functions: Union[str, list[str]] = Field(
        default=[],
        description="String block or list of helper function definitions. "
        "These functions should be defined as strings that can be executed by the Python interpreter.",
    )

    types: dict[str, str] = Field(
        default_factory=dict,
        description="A mapping containing any shared type definitions. "
        "These types can be referenced by name in the params section to provide type annotations "
        "for args and options defined in the params section.",
    )

    global_params: list[ParamBlock] = Field(default=[], description="Parameters applied to all commands")

    command_templates: dict[str, CommandTemplate] = Field(
        default_factory=dict, description="Reusable command templates"
    )

    commands: Union[dict[str, CommandBlock], list[Command]] = Field(
        ...,
        description="A mapping containing the command definitions for the CLI. "
        "Each command should have a unique key- which can be either a group command or nested subcommands. "
        "Nested subcommands are joined by '.' in between each level. "
        "Aliases for commands can be separated in the key by '|'. "
        "A special '(*)' wildcard can be used to spread the subcommand to all group-level commands",
    )

    cli_options: dict[str, Any] = Field(default_factory=dict, description="Additional CLI configuration options")

    tests: list[Union[str, dict[str, str]]] = Field(default=[], description="Test cases for commands")

    examples: list[Example] = Field(default=[], description="Example command usages to display in generated CLI docs.")

    @field_validator("manifestVersion", mode="after")
    @classmethod
    def is_v3(cls, value: str) -> str:
        if value.strip() == "v1":
            raise ValueError(
                "v1 schema is deprecated with cliffy >= 0.4.0. Please upgrade the manifest to the v3 schema."
            )
        if value.strip() == "v2":
            raise ValueError(
                "v2 schema is deprecated with cliffy >= 0.5.0. Please upgrade the manifest to the v3 schema."
            )
        if value.strip() != "v3":
            raise ValueError(f"Unrecognized manifest version {value}. Latest is {LATEST_SCHEMA_VERSION}.")
        return value

    @classmethod
    def get_field_description(cls, field_name: str, as_comment: bool = True) -> str:
        field = cls.model_fields.get(field_name)
        if not field or not field.description:
            return ""

        if as_comment:
            return wrap_as_comment(field.description, split_on=". ")
        return field.description

    @classmethod
    def get_template(cls, cli_name: str, json_schema: bool) -> str:
        """
        Generate a template for a CLI manifest with optional JSON schema reference.

        This method creates a comprehensive YAML template for a CLI application, providing a structured
        outline with placeholders and example configurations for various manifest components.

        Args:
            cls (type): The class on which the method is called (typically CLIManifest).
            cli_name (str): The name of the CLI, which must be a valid Python identifier.
            json_schema (bool): Flag to include a JSON schema reference comment.

        Returns:
            str: A YAML-formatted manifest template with example configurations.

        Raises:
            ValueError: If the provided CLI name is not a valid Python identifier.

        Example:
            manifest = CLIManifest.get_template("mycli", json_schema=True)
        """
        if not cli_name.isidentifier():
            raise ValueError("CLI name must be a valid Python identifier")

        manifest = ""
        if json_schema:
            manifest += "# yaml-language-server: $schema=cliffy_schema.json\n"
        manifest += f"""manifestVersion: {LATEST_SCHEMA_VERSION}

{"" if json_schema else cls.get_field_description("name")}
name: {cli_name}

{"" if json_schema else cls.get_field_description("version")}
version: 0.1.0

{"" if json_schema else cls.get_field_description("help")}
help: A brief description of your CLI

{"" if json_schema else cls.get_field_description("requires")}
requires: []
  # - requests>=2.25.1
  # - pyyaml~=5.4

{"" if json_schema else cls.get_field_description("includes")}
includes: []
  # - path/to/other/manifest.yaml

{"" if json_schema else cls.get_field_description("vars")}
vars:
  data_file: "data.json"
  debug_mode: "{{{{ env['DEBUG'] or 'False' }}}}"

{"" if json_schema else cls.get_field_description("imports")}
imports: |
  import json
  import os
  from pathlib import Path

{"" if json_schema else cls.get_field_description("functions")}
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
{"" if json_schema else cls.get_field_description("types")}
types:
  Filename: str = typer.Argument(..., help="Name of the file to process")
  Verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")

{"" if json_schema else cls.get_field_description("global_params")}
global_params:
  - verbose: Verbose

{"" if json_schema else cls.get_field_description("command_templates")}
command_templates:
  with_confirmation:
    params:
      - "yes": bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
    pre_run: |
      if not yes:
        typer.confirm("Are you sure you want to proceed?", abort=True)

{"" if json_schema else cls.get_field_description("commands")}
commands:
  hello:
    help: Greet the user
    params:
      - name: str = typer.Option("World", "--name", "-n", help="Name to greet")
    run: |
      print(f"Hello, {{name}}!")
      $ echo "i can also mix-and-match this command script to run shell commands"

  file.process:
    help: Process a file
    params:
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
    params: [filename: Filename]
    run: |
      if verbose:
        print(f"Deleting {{filename}}")
      os.remove(filename)
      print("File deleted successfully")

{"" if json_schema else cls.get_field_description("cli_options")}
cli_options:
  rich_help_panel: True

{"" if json_schema else cls.get_field_description("tests")}
tests:
  - hello --name Alice: assert 'Hello, Alice!' in result.output
  - file process test.txt: assert 'Processing test.txt' in result.output
"""
        return manifest

    @classmethod
    def get_raw_template(cls, cli_name: str, json_schema: bool) -> str:
        """
        Generate a raw YAML template for a CLI manifest.

        Parameters:
            cli_name (str): The name of the CLI to be used in the template
            json_schema (bool): Flag to include JSON schema reference comment

        Returns:
            str: A YAML-formatted template for a CLI manifest with default configuration
        """
        manifest = ""
        if json_schema:
            manifest += "# yaml-language-server: $schema=cliffy_schema.json\n"
        manifest += f"""manifestVersion: {LATEST_SCHEMA_VERSION}

name: {cli_name}
version: 0.1.0
help: A brief description of your CLI

requires: []

includes: []

vars: {{}}

imports: ""

functions: []

types: {{}}

global_params: []

command_templates: {{}}

commands: {{}}

cli_options: {{}}

tests: []
"""
        return manifest


class IncludeManifest(BaseModel):
    """Special model specifically to define the allowed named objects that
    can be merged with other manifests.
    """

    requires: list[str] = []
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
    import json

    if "--json-schema" in sys.argv:
        print(json.dumps(CLIManifest.model_json_schema(), indent=4))
        sys.exit()

    yaml_template = CLIManifest.get_raw_template(cli_name="mycli", json_schema=False)
    print(yaml_template)
