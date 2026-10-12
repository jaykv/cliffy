import keyword
import re
import sys
from collections.abc import ItemsView, Iterator
from datetime import datetime
from functools import cached_property
from typing import Any, Self

from pydantic import BaseModel, Field, RootModel, ValidationInfo, field_validator, model_validator

from .helper import CLI_NAME_PATTERN, GENERATED_NAMES, wrap_as_comment

LATEST_SCHEMA_VERSION = "v3"
MIGRATION_GUIDE = "https://jaykv.github.io/cliffy/project/migration/"
# schema version -> the cliffy release that stopped reading it
DEPRECATED_SCHEMA_VERSIONS = {"v1": "0.4.0", "v2": "0.5.0"}


def manifest_version_problem(value: object) -> str | None:
    """Why a `manifestVersion` value cannot be used and what to change, or None when it is the current version."""
    version = str(value).strip()
    if version == LATEST_SCHEMA_VERSION:
        return None

    use_latest = f"set `manifestVersion: {LATEST_SCHEMA_VERSION}` or remove the line"
    if version in DEPRECATED_SCHEMA_VERSIONS:
        return (
            f"The {version} schema is deprecated since cliffy {DEPRECATED_SCHEMA_VERSIONS[version]} and is no longer "
            f"read. Update the manifest to the {LATEST_SCHEMA_VERSION} schema ({MIGRATION_GUIDE}), then {use_latest}."
        )
    return (
        f"Unrecognized manifest version `{version}`. This version of cliffy reads `{LATEST_SCHEMA_VERSION}` "
        f"manifests: {use_latest}."
    )


class Example(BaseModel):
    command: str
    description: str | None = None


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
        parsed_type = self.raw_type.split("=", 1)[0].strip()
        return parsed_type.rstrip("!")

    @property
    def required(self) -> bool:
        return self.raw_type.endswith("!")

    @property
    def default(self) -> str | None:
        # only the first `=` separates type and default: the default itself may contain one
        return self.raw_type.split("=", 1)[1].strip() if "=" in self.raw_type else None

    @property
    def short(self) -> str | None:
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


ParamBlock = CommandParam | SimpleCommandParam | GenericCommandParam
# a string, a number or a boolean; or `{expression}` (a one-key mapping without a value) for a Python expression.
# bool is listed before int: in Python a bool is an int, and `true` has to stay a boolean.
VarBlock = str | bool | int | float | dict[str, None]


class CommandConfig(BaseModel):
    """Configuration options for a Cliffy command."""

    context_settings: dict[Any, Any] = Field(
        default={},
        description="Settings passed to the Click context of the command, for example `help_option_names` "
        "or `max_content_width`.",
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
        description="Name of the panel this command is listed under in rich help output.",
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

    run: RunBlock | RunBlockList = Field(
        default=RunBlock(root=""),
    )
    help: str = Field(default="", description="A description of the command, displayed in the help output.")
    params: list[ParamBlock] = Field(
        default=[],
        description="The parameters of the command. Each entry takes one of three forms: "
        "a shorthand mapping of the param name to its type, such as `name: str!` or `--count: int = 1`; "
        "an explicit mapping with the keys `name` and `type` and optionally `default`, `help`, `short` and `required`; "
        "or a string that is copied into the generated code as written "
        "(a signature entry for Typer, a decorator for Click).",
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
    config: CommandConfig | None = Field(
        default=None,
        description="An optional `CommandConfig` object that provides additional configuration options for the command, such as context settings, help text customization, and visibility.",
    )


CommandBlock = Command | RunBlock | RunBlockList


class CommandTemplate(BaseModel):
    """
    Defines a reusable template for command definitions.  Templates allow you to define
    common parameters, pre-run/post-run scripts, and configuration options that can be
    applied to multiple commands.
    """

    params: list[ParamBlock] = Field(
        default=[],
        description="A list of parameters for the command template. These parameters will be applied to any command that uses this template.",
    )
    pre_run: PreRunBlock = Field(
        default=PreRunBlock(root=""),
        description="Script to run before the command's run and pre-run block. This script will be applied to any command that uses this template.",
    )
    post_run: PostRunBlock = Field(
        default=PostRunBlock(root=""),
        description="Script to run after the command's run and post-run block. This script will be applied to any command that uses this template.",
    )
    config: CommandConfig | None = Field(
        default=None,
        description="Additional configuration options for commands using this template. This allows customization of help text, context settings, and other Typer command parameters.",
    )


class Callback(BaseModel):
    """
    Code that runs before the commands of the CLI, or of one command group. A callback can declare its own
    params, which become options of the CLI (or group) itself, i.e. `mycli --verbose command`.
    The Typer/Click context is available in the run block as `ctx`.
    """

    run: RunBlock = Field(..., description="Code to run before the invoked command. `ctx` holds the context.")
    group: str = Field(
        default="",
        description="Command group the callback belongs to, i.e. `db` or `db.tables`. Leave empty for the CLI itself.",
    )
    params: list[ParamBlock] = Field(
        default=[],
        description="Params of the CLI (or group) itself, given before the command name. Same syntax as command params.",
    )
    invoke_without_command: bool = Field(
        default=False,
        description="Also run the callback when the CLI (or group) is invoked without a command, instead of showing the help.",
    )


class CLIManifest(BaseModel):
    manifestVersion: str = LATEST_SCHEMA_VERSION
    name: str = Field(..., description="The name of the CLI, used when invoking from command line.")
    version: str = Field(..., description="CLI version")
    help: str = Field(default="", description="Brief description of the CLI")
    use_click: bool = Field(default=False, description="Generate CLI to Click instead of Typer")
    requires: list[str] = Field(
        default=[],
        description="Python packages the CLI needs, as requirement specifiers such as `rich` or `tabulate>=0.9.0`. "
        "Checked when the manifest is loaded and bundled by `cli build`.",
    )
    includes: list[str] = Field(
        default=[],
        description="Paths of other manifest files to merge into this one, relative to this file. "
        "Keys set in this manifest win over included ones and lists are combined. "
        "When two included files set the same key, the first one listed wins.",
    )

    vars: dict[str, VarBlock] = Field(
        default_factory=dict,
        description="Variables for the manifest. Each one can be used anywhere in the file as `{{ name }}` "
        "and is also defined as a module-level Python variable in the generated CLI. "
        "A value is a string, a number, a boolean, or a Python expression written as `{expression}`. "
        "String values are Jinja2 templates: they can use other vars, and `env` gives access to environment variables.",
    )
    imports: str | list[str] = Field(
        default=[],
        description="String block or list of strings containing any module imports. "
        "These can be used to import any python modules that the CLI depends on.",
    )
    functions: str | list[str] = Field(
        default=[],
        description="String block or list of helper function definitions. "
        "These functions should be defined as strings that can be executed by the Python interpreter.",
    )

    types: dict[str, str] = Field(
        default_factory=dict,
        description="A mapping containing any shared type definitions. "
        "These types can be referenced by name in the params section to provide type annotations "
        "for args and options defined in the params section. "
        "A value is a plain type such as `int`, optionally with a default (`int = 5`), or a complete definition: "
        "`str = typer.Option(...)` for Typer, a decorator such as `@click.option(...)` for Click.",
    )

    global_params: list[ParamBlock] = Field(default=[], description="Parameters applied to all commands")

    command_templates: dict[str, CommandTemplate] = Field(
        default_factory=dict, description="Reusable command templates"
    )

    commands: dict[str, CommandBlock] | list[Command] = Field(
        default_factory=dict,
        description="The commands of the CLI, keyed by name. "
        "In a key, `.` separates groups, `|` separates aliases and a leading `(*)` adds the command to every group.",
    )

    callbacks: list[Callback] = Field(
        default=[],
        description="Code that runs before any command of the CLI, or of one command group. "
        "Callbacks for the same target run in the order given and their params are combined. "
        "The built-in --version and --aliases options are kept.",
    )

    cli_options: dict[str, Any] = Field(default_factory=dict, description="Additional CLI configuration options")

    tests: list[str | dict[str, str]] = Field(default=[], description="Test cases for commands")

    examples: list[str | Example] = Field(
        default=[], description="Example command usages to display in generated CLI docs."
    )

    @field_validator("name", mode="after")
    @classmethod
    def is_safe_name(cls, value: str) -> str:
        """The name becomes a module name, a script file name and a metadata file name."""
        if not CLI_NAME_PATTERN.fullmatch(value):
            raise ValueError(
                f"Invalid CLI name {value!r}. Use letters, digits, `_` and `-` only, starting with a letter or `_`."
            )
        return value

    @field_validator("vars", mode="after")
    @classmethod
    def var_names_are_identifiers(cls, value: dict[str, Any]) -> dict[str, Any]:
        """A var becomes a module-level Python variable of the generated CLI."""
        for name, var in value.items():
            if isinstance(var, dict) and len(var) != 1:
                raise ValueError(
                    f"vars.{name}: a Python expression is written as `{{expression}}`, one expression in braces. "
                    f"Found {len(var)}."
                )
            if name.isidentifier() and not keyword.iskeyword(name) and name not in GENERATED_NAMES:
                continue

            if name in GENERATED_NAMES:
                problem = "is a name the generated CLI uses itself"
            elif keyword.iskeyword(name):
                problem = "is a Python keyword"
            else:
                problem = "is not a valid Python identifier"
            suggestion = re.sub(r"\W", "_", name)
            if not suggestion.isidentifier() or keyword.iskeyword(suggestion) or suggestion in GENERATED_NAMES:
                suggestion = f"{suggestion}_" if suggestion.isidentifier() else f"_{suggestion}"
            raise ValueError(
                f"vars.{name}: `{name}` {problem}. A var becomes a Python variable, so use letters, digits and `_` "
                f"only, i.e. `{suggestion}`."
            )
        return value

    @field_validator("manifestVersion", mode="after")
    @classmethod
    def is_v3(cls, value: str) -> str:
        if problem := manifest_version_problem(value):
            raise ValueError(problem)
        return value

    @model_validator(mode="after")
    def callback_groups_exist(self) -> Self:
        if not self.callbacks:
            return self

        names = self.commands if isinstance(self.commands, dict) else [command.name for command in self.commands]
        groups: set[str] = set()
        for name in names:
            parts = name.split("|")[0].strip().split(".")
            groups.update(".".join(parts[:depth]) for depth in range(1, len(parts)))

        for callback in self.callbacks:
            if callback.group and callback.group not in groups:
                known = ", ".join(sorted(groups)) or "none"
                raise ValueError(
                    f"callback group `{callback.group}` does not match any command group (groups: {known})"
                )
        return self

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
            str: A YAML-formatted template for a CLI manifest with default configuration. It has one command
                and one test, so that it runs and passes `cli test` as written.
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

commands:
  hello: print("Hello!")

cli_options: {{}}

tests:
  - hello: assert result_text == "Hello!"
"""
        return manifest


class IncludeManifest(BaseModel):
    """Special model specifically to define the allowed named objects that
    can be merged with other manifests.
    """

    requires: list[str] = []
    commands: dict[str, CommandBlock] = {}
    vars: dict[str, VarBlock] = {}
    imports: str | list[str] = []
    functions: list[str] = []
    types: dict[str, str] = {}
    cli_options: dict[str, str] = {}
    tests: list[str | dict[str, str]] = []


class CLIMetadata(BaseModel):
    """Metadata model"""

    cli_name: str
    runner_path: str
    version: str
    loaded: datetime
    manifest: str
    requires: list[str]
    blueprint: str | None = None


if __name__ == "__main__":
    import json

    if "--json-schema" in sys.argv:
        print(json.dumps(CLIManifest.model_json_schema(), indent=4))
        sys.exit()

    yaml_template = CLIManifest.get_raw_template(cli_name="mycli", json_schema=False)
    print(yaml_template)
