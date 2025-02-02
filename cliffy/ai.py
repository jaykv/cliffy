from pathlib import Path
from typing import Optional
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName
from cliffy.rich import click
from cliffy.helper import out, ManifestOrCLI
from cliffy.manifest import CLIManifest
from cliffy.transformer import Transformer
from cliffy.homer import get_metadata
import json
from io import TextIOWrapper


@click.group(help="AI-powered commands")
def ai() -> None:
    pass


@click.option("--max-tokens", type=int, help="The maximum number of tokens to generate before stopping.", default=None)
@click.option(
    "--model",
    "-m",
    help="AI model to use. See https://ai.pydantic.dev/models/ for supported models.",
    default="gemini-2.0-flash-exp",
    show_default=True,
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    default=Path(),
    show_default=True,
    help="Output directory",
)
@click.argument("cli_name", required=True)
@click.argument("description", required=True)
def generate(cli_name: str, description: str, model: KnownModelName, max_tokens: int, output_dir: Path) -> None:
    SYSTEM_PROMPT = f"""You are a YAML manifest generator for CLIs. 
Here is the json schema for the YAML to generate:
```json{json.dumps(CLIManifest.model_json_schema())}```
Typer is the CLI framework used. 
Nested commands are joined by a "."
Due to a feature limitation, parent command cannot be triggered if they have subcommands. 
Do not write a group command definition for the parent if it has a subcommand.
Do not use types section at all.
Parameters can be used in the run scripts by referencing the parameter name directly.
Always provide `examples` section to list example commands for the CLI.
Use Python and Typer features and imports as needed to craft the best CLI for the following listed CLI requirements. 
"""

    model_settings = ModelSettings(max_tokens=max_tokens) if max_tokens else None
    agent = Agent(model, system_prompt=SYSTEM_PROMPT, model_settings=model_settings)

    usage_limits = UsageLimits(total_tokens_limit=max_tokens) if max_tokens else None

    result = agent.run_sync(description, usage_limits=usage_limits)

    manifest = result.data.strip().removeprefix("```yaml").removesuffix("```").strip()
    (output_dir / Path(f"{cli_name}.yaml")).write_text(manifest)
    out(f"+ {cli_name}.yaml")
    out("\ntoken usage:")
    out("------------")
    out(f"request: {result.usage().request_tokens}")
    out(f"response: {result.usage().response_tokens}")


@click.option("--max-tokens", type=int, help="The maximum number of tokens to generate before stopping.", default=None)
@click.option("--model", "-m", help="LLM model to use.", default="gemini-2.0-flash-exp", show_default=True)
@click.option(
    "--cli", type=ManifestOrCLI(), help="Loaded CLI or manifest to include in prompt as reference.", default=None
)
@click.argument("prompt", required=True)
def ask(cli: Optional[ManifestOrCLI], prompt: str, model: KnownModelName, max_tokens: int) -> None:
    SYSTEM_PROMPT = f"""You are an expert of `cliffy`- a YAML manifest to Typer CLI generator.

## Cliffy Usage
`cli <command>`

| Command | Description |
|---|---|
| `init <cli name>`| Generate a template CLI manifest for a new CLI |
| `load <manifest>` | Add a new CLI based on the manifest |
| `render <manifest>` | View generated CLI script for a manifest |
| `list, ls` | Output a list of loaded CLIs |
| `update <cli name>`| Reload a loaded CLI |
| `remove <cli name>, rm <cli name>` | Remove a loaded CLI |
| `run <manifest> -- \<args>`| Runs a CLI manifest command in isolation|
| `build <cli name or manifest>` | Build a CLI manifest or a loaded CLI into a self-contained zipapp |
| `info <cli name>` | Display CLI metadata |
| `dev <manifest>` | Start hot-reloader for a manifest for active development |
| `test <manifest>` | Run tests defined in a manifest |
| `validate <manifest>` | Validate the syntax and structure of a CLI manifest |

## How it works
1. Define CLI manifests in YAML files
2. Run `cli` commands to load, build, and manage CLIs
3. When loaded, cliffy parses the manifest and generates a Typer CLI that is deployed directly as a script
4. Any code starting with `$` will translate to subprocess calls via PyBash
5. Run loaded CLIs straight from the terminal
6. When ready to share, run `build` to generate portable zipapps built with [Shiv](https://github.com/linkedin/shiv)

Here is the model json schema for CLI manifest:
```json{json.dumps(CLIManifest.model_json_schema())}```
Typer is the CLI framework used. 
Due to a feature limitation, parent command cannot be triggered if they have subcommands. 
Do not write a group command definition for the parent if it has a subcommand.
Parameters can be used in the run scripts by referencing the parameter name directly.
Always provide `examples` section to list example commands for the CLI.
Use Python and Typer features and imports as needed to craft the best CLI for the following listed CLI requirements. 
"""
    model_settings = ModelSettings(max_tokens=max_tokens) if max_tokens else None
    agent = Agent(model, system_prompt=SYSTEM_PROMPT, model_settings=model_settings)

    usage_limits = UsageLimits(total_tokens_limit=max_tokens) if max_tokens else None

    reference = ""
    if cli:
        reference += "Here is the CLI manifest to use as reference:"
        reference += "```yaml"
        if isinstance(cli, TextIOWrapper):
            reference += str(Transformer(cli).manifest.model_dump(mode="json"))
        elif isinstance(cli, str):
            metadata = get_metadata(cli)
            reference += metadata.manifest if metadata else ""
        reference += "```"

    result = agent.run_sync(reference + prompt, usage_limits=usage_limits)
    out(result.data)
    out("\ntoken usage:")
    out("------------")
    out(f"request: {result.usage().request_tokens}")
    out(f"response: {result.usage().response_tokens}")


ai.command("generate", help="Generate a CLI manifest based on a description.")(generate)
ai.command("ask", help="Ask a question about cliffy or a specific CLI manifest.")(ask)
