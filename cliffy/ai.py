from pathlib import Path
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits
from typing_extensions import TypedDict, Annotated
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName
import click
from cliffy.helper import out
from cliffy.manifest import CLIManifest
import json
from pydantic import Field


class ParamBlockDict(TypedDict):
    name: Annotated[str, Field(default="", description="Parameter name. Prefix with `--` to indicate an option.")]
    type: Annotated[
        str,
        Field(
            default="",
            description="Parameter type (e.g., 'str', 'int', 'bool', or a custom type defined in the manifest's 'types' section).",
        ),
    ]
    default: Annotated[str, Field(default="", description="Default parameter value.")]
    help: Annotated[str, Field(default="", description="Parameter description.")]
    short: Annotated[str, Field(default="", description="Short option alias. i.e. '-v' for verbose.")]
    required: Annotated[bool, Field(default=False, description="Whether the parameter is required.")]


class CommandTemplateDict(TypedDict):
    params: Annotated[
        list[ParamBlockDict],
        Field(
            default=[],
            description="A list of parameters for the command template.  These parameters will be applied to any command that uses this template.",
        ),
    ]
    pre_run: Annotated[
        str,
        Field(
            default="",
            description="Script to run before the command's run and pre-run block. This script will be applied to any command that uses this template.",
        ),
    ]
    post_run: Annotated[
        str,
        Field(
            default="",
            description="Script to run after the command's run and post-run block. This script will be applied to any command that uses this template.",
        ),
    ]
    # config: Annotated[NotRequired[CommandConfig], Field(
    #     default=None,
    #     description="Additional configuration options for commands using this template. This allows customization of help text, context settings, and other Typer command parameters.",
    # )]


class CommandDict(TypedDict):
    """
    Defines a single command within the CLI. It specifies the command's execution logic,
    parameters, and configuration.
    """

    run: Annotated[
        str, Field(default="", description="Script to run. Parameters can be referenced directly by their name.")
    ]
    help: Annotated[str, Field(default="", description="A description of the command, displayed in the help output.")]
    params: Annotated[
        list[ParamBlockDict],
        Field(
            default=[],
            description="A list of parameters for the command.\nThere are three ways to define a param: \n(generic) 1. A string as param definition. Gets appended to the command params signature.\n(implicit) 2. A mapping with the param name as the key and the type as the value. Custom types are accepted here. Same as the implicit v1 params syntax. \n(explicit) 3. A mapping with the following keys: `name` (required), `type` (required), `default` (None by default), `help` (Optional), `short` (Optional), `required` (False by default).",
        ),
    ]
    template: Annotated[
        str,
        Field(
            default="",
            description="A reference to a command template defined in the `command_templates` section of the manifest. This allows for reusable command definitions.",
        ),
    ]
    pre_run: Annotated[
        str,
        Field(
            default="",
            description="Script to run before the command's run block. This can be used for setup tasks or preconditions. Parameters can be referenced directly by their name.",
        ),
    ]
    post_run: Annotated[
        str,
        Field(
            default="",
            description="Script to run after the command's run block. This can be used for cleanup tasks or post-processing. Parameters can be referenced directly by their name.",
        ),
    ]
    aliases: Annotated[
        list[str],
        Field(
            default=[],
            description="A list of aliases for the command. These aliases can be used to invoke the command with a different name.",
        ),
    ]
    name: Annotated[
        str,
        Field(
            default="",
            description="The name of the command. This is generally derived from the key in the `commands` section of the manifest, but can be explicitly set here.",
        ),
    ]
    # config: Optional[CommandConfig] = Field(
    #     default=None,
    #     description="An optional `CommandConfig` object that provides additional configuration options for the command, such as context settings, help text customization, and visibility.",
    # )


class CLIManifestAI(CLIManifest):
    vars: list[str] = Field(default=[], description=CLIManifest.get_field_description("vars"))
    params: list[str] = Field(default=[], description=CLIManifest.get_field_description("params"))
    command_templates: list[CommandTemplateDict] = Field(
        default=[], description=CLIManifest.get_field_description("command_templates")
    )
    examples: list[str] = Field(default=[], description=CLIManifest.get_field_description("examples"))
    commands: list[CommandDict] = Field(default=[])
    tests: list[str] = Field(default=[], description=CLIManifest.get_field_description("tests"))
    global_params: list[str] = Field(default=[], description=CLIManifest.get_field_description("global_params"))
    types: list[str] = Field(default=[])
    imports: str = Field(default="", description=CLIManifest.get_field_description("imports"))
    functions: list[str] = Field(default=[], description=CLIManifest.get_field_description("functions"))
    cli_options: str = Field(default="", description=CLIManifest.get_field_description("cli_options"))


@click.group()
def ai() -> None:
    pass


@click.option("--max-tokens", type=int, help="The maximum number of tokens to generate before stopping.", default=None)
@click.option("--model", "-m", default="anthropic:claude-3-5-sonnet-latest", show_default=True)
@click.option("--description", "-d", required=True)
@click.argument("cli_name", required=True)
def generate(cli_name: str, description: str, model: KnownModelName, max_tokens: int):
    SYSTEM_PROMPT = (
        """You are a YAML manifest generator for CLIs. 
Here is the json schema for the YAML to generate:
```json"""
        + json.dumps(CLIManifest.model_json_schema())
        + """```
Typer is the CLI framework used for Python. 
Due to a feature limitation, parent command cannot be triggered if they have subcommands. 
Do not write a group command definition for the parent if it has a subcommand.
Parameters can be used in the run scripts by referencing the parameter name directly.

Use Python and Typer features and imports as needed to craft the best CLI for the following listed CLI requirements. 
Always provide `examples` section to list example commands for the CLI.
"""
    )

    model_settings = ModelSettings(max_tokens=max_tokens) if max_tokens else None
    agent = Agent(model, system_prompt=SYSTEM_PROMPT, model_settings=model_settings)

    usage_limits = UsageLimits(total_tokens_limit=max_tokens) if max_tokens else None

    result = agent.run_sync(description, usage_limits=usage_limits)

    Path(f"{cli_name}.yaml").write_text(result.data)
    out(f"+ {cli_name}.yaml")
    out("\ntoken usage:")
    out("------------")
    out(f"Request: {result.usage().request_tokens}")
    out(f"Response: {result.usage().response_tokens}")


ai.command("generate")(generate)
