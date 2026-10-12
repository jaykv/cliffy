"""AI-powered commands: ``cli ai generate`` and ``cli ai ask``.

pydantic-ai is an optional dependency (``cliffy[ai]``) and slow to import, so it is only imported
when one of the commands actually talks to a model. Importing this module is cheap and always safe.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

import yaml
from click import Context, Group
from pydantic import ValidationError

from cliffy.helper import ManifestOrCLI, exit_err, out
from cliffy.homer import get_metadata
from cliffy.manifest import CLIManifest
from cliffy.rich import click

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.usage import RunUsage

MODEL_ENV_VAR = "CLIFFY_AI_MODEL"
INSTALL_HINT = "pip install 'cliffy[ai]'"

# Used when neither --model nor CLIFFY_AI_MODEL is given: the first provider with an API key in the
# environment wins. Where a provider publishes a rolling alias it is preferred over a dated model id.
PROVIDER_DEFAULTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("GOOGLE_API_KEY", "GEMINI_API_KEY"), "google:gemini-flash-latest"),
    (("ANTHROPIC_API_KEY",), "anthropic:claude-sonnet-5-5"),
    (("OPENAI_API_KEY",), "openai:gpt-5.4-mini"),
)
FALLBACK_MODEL = PROVIDER_DEFAULTS[0][1]

CLI_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
FENCED_BLOCK_PATTERN = re.compile(r"```[A-Za-z]*[ \t]*\n(.*?)```", re.DOTALL)

MANIFEST_RULES = """\
Rules for writing a manifest:
- `manifestVersion` is `v3`. `name`, `version` and `commands` are required.
- Typer is the CLI framework of the generated CLI, so `typer` is always available in run blocks.
- A command's `run` block is Python. A line starting with `$` is run as a shell command.
- Parameters are available in run blocks as variables named after the parameter.
- Parameter shorthand: `name: str!` is a required argument, `--name: str = "x"` is an option with a default, \
`--name|-n: str` adds a short flag. A Typer expression such as `name: str = typer.Option(...)` also works.
- Nested subcommands are joined with `.`, as in `db.create`. A command that has subcommands cannot run on its \
own, so never define a `run` block for a parent command.
- Anything the run blocks import goes in `imports`. Third-party packages also go in `requires`.
- Add an `examples` section listing example invocations of the CLI."""

GENERATE_OUTPUT_RULES = """\
Reply with the YAML manifest only: no explanations, no surrounding prose.
The manifest must be self-contained: do not use `includes`, and do not use the `types` section.
Your reply is validated against the schema. If it is rejected you will be told why; fix it and reply with the \
complete corrected manifest."""

HOW_IT_WORKS = """\
How cliffy works:
1. A CLI is defined in a YAML manifest.
2. `cli load <manifest>` parses the manifest, generates a Typer (or Click, with `use_click: true`) CLI and \
installs it as a script, so it can be run straight from the terminal.
3. Code in a run block that starts with `$` is translated to subprocess calls by PyBash.
4. `cli build` packages a CLI into a portable zipapp built with Shiv."""


class ManifestOutputError(ValueError):
    """A model reply that is not a usable CLI manifest. The message is sent back to the model."""


def default_model() -> str:
    """Pick the model to use when the user did not choose one."""
    for env_vars, model in PROVIDER_DEFAULTS:
        if any(os.environ.get(var) for var in env_vars):
            return model
    return FALLBACK_MODEL


def require_ai_extra() -> None:
    """Import pydantic-ai, or exit with an install hint when the ``ai`` extra is missing."""
    try:
        import pydantic_ai
    except ModuleNotFoundError as e:
        # only a missing pydantic-ai is an install problem; anything else is a real bug and must surface
        if e.name is None or e.name.partition(".")[0] != "pydantic_ai":
            raise
        exit_err(f"~ AI commands need the `ai` extra, which is not installed. Install it with: {INSTALL_HINT}")

    # keep pydantic-ai's first-run banner out of the command output
    pydantic_ai.BANNER_ENABLED = False


def resolve_model(model: str | None) -> Model:
    """Turn a ``provider:model`` name into a pydantic-ai model, exiting with a readable error if that fails."""
    require_ai_extra()
    from pydantic_ai.exceptions import UserError
    from pydantic_ai.models import infer_model

    name = model or default_model()
    api_keys = ", ".join(env_vars[0] for env_vars, _ in PROVIDER_DEFAULTS)
    hint = (
        f"Set the API key of a provider ({api_keys}, ...) or choose a model with --model or {MODEL_ENV_VAR}, "
        f"as `provider:model` (for example `{FALLBACK_MODEL}`)."
    )
    try:
        return infer_model(name)
    except UserError as e:
        # unknown provider or model name, or the provider's API key is not set
        reason = str(e).partition(" To try Pydantic AI")[0]  # drop pydantic-ai's pointer to its test model
        exit_err(f"~ cannot use AI model `{name}`: {reason}\n{hint}")
    except ImportError as e:
        # the provider's SDK is not installed (pydantic-ai-slim without that provider's extra)
        exit_err(f"~ cannot use AI model `{name}`: {e}\n{hint}")


def model_settings(max_tokens: int | None) -> ModelSettings | None:
    from pydantic_ai.settings import ModelSettings

    return ModelSettings(max_tokens=max_tokens) if max_tokens else None


def command_reference() -> str:
    """Describe cliffy's own commands, read from the live click group so it cannot go stale."""
    from cliffy.cli import ALIASES, cli

    lines: list[str] = []

    def walk(group: Group, prefix: str) -> None:
        for name in sorted(group.commands):
            command = group.commands[name]
            if command.hidden:
                continue
            if isinstance(command, Group):
                walk(command, f"{prefix} {name}")
                continue
            usage = " ".join(command.collect_usage_pieces(Context(command, info_name=name)))
            lines.append(f"- `{prefix} {name} {usage}`: {command.get_short_help_str(limit=200)}")

    walk(cli, "cli")
    aliases = ", ".join(f"`{alias}` = `{command}`" for alias, command in ALIASES.items())
    return "\n".join([*lines, f"Aliases: {aliases}"])


def manifest_reference() -> str:
    """The manifest documentation that ships with cliffy: annotated template and JSON schema."""
    return (
        "Annotated example manifest (the output of `cli init`). The comments describe each section:\n"
        f"```yaml\n{CLIManifest.get_template('mycli', json_schema=False)}```\n\n"
        "JSON schema of a manifest:\n"
        f"```json\n{json.dumps(CLIManifest.model_json_schema())}\n```"
    )


def generate_instructions(cli_name: str) -> str:
    return (
        "You write YAML manifests for `cliffy`, a tool that generates Python CLIs from YAML manifests.\n"
        f"Write a manifest for a CLI named `{cli_name}` that fulfils the description given by the user.\n\n"
        f"{MANIFEST_RULES}\n\n{GENERATE_OUTPUT_RULES}\n\n{manifest_reference()}"
    )


def ask_instructions() -> str:
    return (
        "You are an expert on `cliffy`, a tool that generates Python CLIs from YAML manifests.\n"
        "Answer the user's question using the reference below. If the reference does not cover it, say so "
        "instead of guessing. Show manifest snippets as YAML.\n\n"
        f"{HOW_IT_WORKS}\n\ncliffy commands:\n{command_reference()}\n\n{MANIFEST_RULES}\n\n{manifest_reference()}"
    )


def cli_reference(cli: IO[Any] | str | None) -> str:
    """Render the manifest given with ``--cli`` (a manifest file or the name of a loaded CLI) for the prompt."""
    if cli is None:
        return ""

    if isinstance(cli, str):
        metadata = get_metadata(cli) or exit_err(f"~ {cli} is not a loaded CLI or a manifest path")
        manifest = metadata.manifest
    else:
        content = cli.read()
        manifest = content.decode() if isinstance(content, bytes) else content

    return f"\n\nThe question is about this CLI manifest:\n```yaml\n{manifest.strip()}\n```"


def extract_yaml(text: str) -> str:
    """Strip the markdown code fence models tend to wrap YAML in."""
    if fenced := FENCED_BLOCK_PATTERN.search(text):
        text = fenced.group(1)
    return text.strip() + "\n"


def validate_manifest_yaml(text: str, cli_name: str) -> str:
    """Check that a model reply is a manifest cliffy can load and return it as clean YAML.

    Raises:
        ManifestOutputError: describing what is wrong, phrased so the model can fix it.
    """
    manifest_yaml = extract_yaml(text)
    try:
        data = yaml.safe_load(manifest_yaml)
    except yaml.YAMLError as e:
        raise ManifestOutputError(f"The reply is not valid YAML: {e}") from e

    if not isinstance(data, dict):
        raise ManifestOutputError("The reply must be a YAML mapping containing the manifest and nothing else.")

    try:
        manifest = CLIManifest.model_validate(data)
    except ValidationError as e:
        problems = "\n".join(
            f"- {'.'.join(str(part) for part in error['loc']) or '(manifest)'}: {error['msg']}"
            for error in e.errors(include_url=False)
        )
        raise ManifestOutputError(f"The manifest does not match the schema:\n{problems}") from e

    if "commands" not in data and not manifest.callbacks:
        # the schema allows a callbacks-only CLI, so a reply without `commands` passes its validation
        raise ManifestOutputError("The manifest does not match the schema:\n- commands: Field required")
    if manifest.name != cli_name:
        raise ManifestOutputError(f"The manifest `name` must be `{cli_name}`, not `{manifest.name}`.")
    if manifest.includes:
        raise ManifestOutputError("The manifest must be self-contained: remove `includes`.")

    # Jinja expressions are only rendered when the manifest is loaded (with the user's environment),
    # so the generated code can only be checked here for manifests that do not use them.
    if "{{" not in manifest_yaml and "{%" not in manifest_yaml:
        check_generated_code(manifest)

    return manifest_yaml


def check_generated_code(manifest: CLIManifest) -> None:
    """Generate the CLI for a manifest and make sure the result is valid Python. Nothing is executed."""
    from cliffy.commander import generate_cli
    from cliffy.commanders.click import ClickCommander
    from cliffy.commanders.typer import TyperCommander

    try:
        cli = generate_cli(manifest, commander_cls=ClickCommander if manifest.use_click else TyperCommander)
    except Exception as e:  # the commanders raise a variety of errors on manifests they cannot handle
        raise ManifestOutputError(f"cliffy could not generate a CLI from the manifest: {e}") from e

    try:
        compile(cli.code, f"{manifest.name}.py", "exec")
    except SyntaxError as e:
        raise ManifestOutputError(
            f"The CLI generated from the manifest is not valid Python: {e.msg} near `{(e.text or '').strip()}`. "
            "Check the run blocks, functions and imports."
        ) from e


def generate_manifest(
    description: str, cli_name: str, model: Model, *, max_tokens: int | None = None, retries: int = 2
) -> tuple[str, RunUsage]:
    """Ask a model for a manifest and return it once it validates.

    A reply that fails validation is sent back to the model with the reason, up to ``retries`` times.

    Raises:
        ManifestOutputError: if the model never produced a valid manifest.
        pydantic_ai.exceptions.AgentRunError: if the request itself failed.
    """
    from pydantic_ai import Agent, ModelRetry
    from pydantic_ai.exceptions import UnexpectedModelBehavior

    agent = Agent(
        model,
        output_type=str,
        instructions=generate_instructions(cli_name),
        model_settings=model_settings(max_tokens),
        retries=retries,
    )
    rejections: list[ManifestOutputError] = []

    def validate_output(output: str) -> str:
        try:
            return validate_manifest_yaml(output, cli_name)
        except ManifestOutputError as e:
            rejections.append(e)
            raise ModelRetry(str(e)) from e

    # registered with a call, not as a decorator: without the `ai` extra the type checker cannot see
    # pydantic-ai, and an untyped decorator would make this function untyped
    agent.output_validator(validate_output)

    try:
        result = agent.run_sync(description)
    except UnexpectedModelBehavior as e:
        if rejections:
            raise ManifestOutputError(
                f"the model did not produce a valid manifest ({len(rejections)} rejected). "
                f"Last problem:\n{rejections[-1]}"
            ) from e
        raise
    return result.output, result.usage


def ask_question(question: str, model: Model, *, max_tokens: int | None = None) -> tuple[str, RunUsage]:
    """Ask a model a question about cliffy, grounded in the reference built from the installed package."""
    from pydantic_ai import Agent

    agent = Agent(model, output_type=str, instructions=ask_instructions(), model_settings=model_settings(max_tokens))
    result = agent.run_sync(question)
    return result.output, result.usage


def report_usage(usage: RunUsage) -> None:
    # on stderr, so that redirecting stdout captures the answer only
    out(f"\ntoken usage: {usage.input_tokens} in, {usage.output_tokens} out, {usage.requests} request(s)", err=True)


model_option = click.option(
    "--model",
    "-m",
    envvar=MODEL_ENV_VAR,
    show_envvar=True,
    default=None,
    help="Model to use, as `provider:model`. See https://pydantic.dev/docs/ai/models/overview/. "
    f"Defaults to a model of the first provider with an API key set, else {FALLBACK_MODEL}.",
)
max_tokens_option = click.option(
    "--max-tokens", type=click.IntRange(min=1), default=None, help="Maximum number of tokens in a model response."
)
preview_option = click.option(
    "--preview", is_flag=True, default=False, help="Print the prompt instead of sending it. Needs no model."
)


@click.group(help="AI-powered commands. Requires the `ai` extra: " + INSTALL_HINT)
def ai() -> None:
    pass


@preview_option
@max_tokens_option
@model_option
@click.option(
    "--retries",
    type=click.IntRange(min=0),
    default=2,
    show_default=True,
    help="How often to send an invalid manifest back to the model to be fixed.",
)
@click.option("--force", "-f", is_flag=True, default=False, help="Overwrite the manifest file if it exists.")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
    default=Path(),
    show_default=True,
    help="Output directory",
)
@click.argument("cli_name", required=True)
@click.argument("description", required=True)
def generate(
    cli_name: str,
    description: str,
    output_dir: Path,
    force: bool,
    retries: int,
    model: str | None,
    max_tokens: int | None,
    preview: bool,
) -> None:
    if not CLI_NAME_PATTERN.fullmatch(cli_name):
        exit_err(f"~ invalid CLI name `{cli_name}`: use letters, digits, `-` and `_` only")

    if preview:
        out(generate_instructions(cli_name))
        out(f"\n{description}")
        return

    manifest_path = output_dir / f"{cli_name}.yaml"
    if manifest_path.exists() and not force:
        exit_err(f"~ {manifest_path} already exists, pass --force to overwrite it")

    ai_model = resolve_model(model)
    from pydantic_ai.exceptions import AgentRunError

    try:
        manifest, usage = generate_manifest(description, cli_name, ai_model, max_tokens=max_tokens, retries=retries)
    except ManifestOutputError as e:
        exit_err(f"~ no manifest written: {e}")
    except AgentRunError as e:
        exit_err(f"~ request to `{ai_model.model_name}` failed: {e}")

    manifest_path.write_text(manifest)
    out(f"✨ {manifest_path}", fg="green")
    out("$", fg="magenta", nl=False)
    out(f" cli load {manifest_path}")
    report_usage(usage)


@preview_option
@max_tokens_option
@model_option
@click.option(
    "--cli", type=ManifestOrCLI(), default=None, help="Loaded CLI or manifest to include in the prompt as reference."
)
@click.argument("prompt", required=True)
def ask(prompt: str, cli: IO[Any] | str | None, model: str | None, max_tokens: int | None, preview: bool) -> None:
    question = prompt + cli_reference(cli)

    if preview:
        out(ask_instructions())
        out(f"\n{question}")
        return

    ai_model = resolve_model(model)
    from pydantic_ai.exceptions import AgentRunError

    try:
        answer, usage = ask_question(question, ai_model, max_tokens=max_tokens)
    except AgentRunError as e:
        exit_err(f"~ request to `{ai_model.model_name}` failed: {e}")

    out(answer)
    report_usage(usage)


ai.command("generate", help="Generate a CLI manifest based on a description.")(generate)
ai.command("ask", help="Ask a question about cliffy or a specific CLI manifest.")(ask)
