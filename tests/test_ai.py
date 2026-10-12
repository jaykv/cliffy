"""Tests for ``cli ai``. Every model here is a pydantic-ai test or function model: nothing touches the network."""

import subprocess
import sys

import pytest
import yaml
from click.testing import CliRunner
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from cliffy import ai as cliffy_ai
from cliffy.ai import ManifestOutputError, ai, default_model, validate_manifest_yaml
from cliffy.cli import cli
from cliffy.manifest import CLIManifest

API_KEY_VARS = [var for env_vars, _ in cliffy_ai.PROVIDER_DEFAULTS for var in env_vars]

VALID_MANIFEST = """\
manifestVersion: v3
name: greeter
version: 0.1.0
help: Greets people
commands:
  hello:
    help: Say hello
    params: [name: str!]
    run: |
      print(f"Hello, {name}!")
examples:
  - greeter hello World
"""

BROKEN_PYTHON_MANIFEST = VALID_MANIFEST.replace('print(f"Hello, {name}!")', "print(f'Hello, {name}!'")


class ScriptedModel:
    """Function model that replies with the given texts in order and records what it was sent."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.requests: list[list[ModelMessage]] = []
        self.instructions: list[str | None] = []
        self.model = FunctionModel(self._respond)

    def _respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.requests.append(messages)
        self.instructions.append(info.instructions)
        return ModelResponse(parts=[TextPart(self.replies[min(len(self.requests), len(self.replies)) - 1])])

    def parts(self, part_type: type) -> list[str]:
        """Content of all parts of a type in the last request, i.e. the whole conversation so far."""
        return [
            str(part.content) for message in self.requests[-1] for part in message.parts if isinstance(part, part_type)
        ]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def no_ambient_ai_config(monkeypatch):
    """Keep the developer's own API keys and model choice out of the tests."""
    for var in [*API_KEY_VARS, cliffy_ai.MODEL_ENV_VAR]:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def scripted(monkeypatch):
    """Make the commands use a scripted model, whatever model name they are given."""

    def install(*replies: str) -> ScriptedModel:
        model = ScriptedModel(*replies)
        monkeypatch.setattr(cliffy_ai, "resolve_model", lambda name: model.model)
        return model

    return install


# --- import cost and the optional extra ---------------------------------------------------------


def test_importing_cliffy_does_not_import_pydantic_ai():
    code = (
        "import sys, cliffy, cliffy.ai, cliffy.cli, cliffy.run\n"
        "loaded = sorted(name for name in sys.modules if name.partition('.')[0] == 'pydantic_ai')\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_ai_group_is_registered_on_the_main_cli(runner):
    result = runner.invoke(cli, ["ai", "--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "ask" in result.output


@pytest.mark.parametrize("args", [["ask", "What is cliffy?"], ["generate", "greeter", "Greets people"]])
def test_missing_extra_is_reported(runner, monkeypatch, isolated_fs, args):
    monkeypatch.setitem(sys.modules, "pydantic_ai", None)  # makes `import pydantic_ai` fail
    result = runner.invoke(ai, args)
    assert result.exit_code == 1
    assert "cliffy[ai]" in result.output
    assert not (isolated_fs / "greeter.yaml").exists()


def test_unrelated_import_errors_are_not_mistaken_for_a_missing_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "pydantic_ai", None)
    monkeypatch.setattr(
        "builtins.__import__", lambda *args, **kwargs: (_ for _ in ()).throw(ModuleNotFoundError(name="httpx"))
    )
    with pytest.raises(ModuleNotFoundError):
        cliffy_ai.require_ai_extra()


def test_preview_needs_neither_the_extra_nor_a_model(runner, monkeypatch):
    monkeypatch.setitem(sys.modules, "pydantic_ai", None)
    result = runner.invoke(ai, ["generate", "greeter", "Greets people", "--preview"])
    assert result.exit_code == 0
    assert "CLI named `greeter`" in result.output
    assert "Greets people" in result.output

    result = runner.invoke(ai, ["ask", "How do aliases work?", "--preview"])
    assert result.exit_code == 0
    assert "How do aliases work?" in result.output


# --- model selection ----------------------------------------------------------------------------


def test_default_model_without_any_api_key():
    assert default_model() == cliffy_ai.FALLBACK_MODEL


@pytest.mark.parametrize(("env_vars", "model"), cliffy_ai.PROVIDER_DEFAULTS)
def test_default_model_follows_the_api_key_that_is_set(monkeypatch, env_vars, model):
    for var in env_vars:
        monkeypatch.setenv(var, "dummy")
        assert default_model() == model
        monkeypatch.delenv(var)


def test_default_models_have_a_provider_prefix():
    for _, model in cliffy_ai.PROVIDER_DEFAULTS:
        provider, _, name = model.partition(":")
        assert provider and name


def test_missing_api_key_is_reported(runner):
    result = runner.invoke(ai, ["ask", "What is cliffy?"])
    assert result.exit_code == 1
    assert cliffy_ai.FALLBACK_MODEL in result.output
    assert "GOOGLE_API_KEY" in result.output
    assert cliffy_ai.MODEL_ENV_VAR in result.output
    assert "Traceback" not in result.output


def test_unknown_model_is_reported(runner):
    result = runner.invoke(ai, ["ask", "What is cliffy?", "-m", "not-a-model"])
    assert result.exit_code == 1
    assert "cannot use AI model `not-a-model`" in result.output


def test_model_flag_selects_the_model(runner):
    result = runner.invoke(ai, ["ask", "What is cliffy?", "-m", "test"])
    assert result.exit_code == 0
    assert "success (no tool calls)" in result.output


def test_model_env_var_selects_the_model(runner, monkeypatch):
    monkeypatch.setenv(cliffy_ai.MODEL_ENV_VAR, "test")
    result = runner.invoke(ai, ["ask", "What is cliffy?"])
    assert result.exit_code == 0
    assert "success (no tool calls)" in result.output


def test_model_flag_wins_over_env_var(runner, monkeypatch):
    monkeypatch.setenv(cliffy_ai.MODEL_ENV_VAR, "not-a-model")
    result = runner.invoke(ai, ["ask", "What is cliffy?", "-m", "test"])
    assert result.exit_code == 0


def test_resolve_model_returns_a_pydantic_ai_model():
    assert isinstance(cliffy_ai.resolve_model("test"), TestModel)


# --- ai generate --------------------------------------------------------------------------------


def test_generate_writes_a_validated_manifest(runner, scripted, isolated_fs):
    model = scripted(VALID_MANIFEST)
    result = runner.invoke(ai, ["generate", "greeter", "Greets people"])

    assert result.exit_code == 0, result.output
    assert "greeter.yaml" in result.output
    assert "token usage:" in result.output
    written = (isolated_fs / "greeter.yaml").read_text()
    assert written == VALID_MANIFEST
    assert CLIManifest.model_validate(yaml.safe_load(written)).name == "greeter"

    assert len(model.requests) == 1
    assert model.parts(UserPromptPart) == ["Greets people"]
    instructions = model.instructions[0]
    assert instructions is not None
    assert "CLI named `greeter`" in instructions
    assert '"title": "CLIManifest"' in instructions


def test_generated_manifest_loads_as_a_cli(runner, scripted, isolated_fs):
    scripted(VALID_MANIFEST)
    assert runner.invoke(ai, ["generate", "greeter", "Greets people"]).exit_code == 0

    result = runner.invoke(cli, ["run", "greeter.yaml", "--", "hello", "World"])
    assert result.exit_code == 0, result.output
    assert "Hello, World!" in result.output


def test_generate_strips_markdown_fences(runner, scripted, isolated_fs):
    scripted(f"Here is your manifest:\n\n```yaml\n{VALID_MANIFEST}```\n\nEnjoy!")
    result = runner.invoke(ai, ["generate", "greeter", "Greets people"])

    assert result.exit_code == 0, result.output
    assert (isolated_fs / "greeter.yaml").read_text() == VALID_MANIFEST


def test_generate_writes_to_output_dir(runner, scripted, tmp_path):
    scripted(VALID_MANIFEST)
    result = runner.invoke(ai, ["generate", "greeter", "Greets people", "-o", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "greeter.yaml").read_text() == VALID_MANIFEST


def test_generate_sends_validation_errors_back_to_the_model(runner, scripted, isolated_fs):
    model = scripted("commands: {}", VALID_MANIFEST)
    result = runner.invoke(ai, ["generate", "greeter", "Greets people"])

    assert result.exit_code == 0, result.output
    assert (isolated_fs / "greeter.yaml").read_text() == VALID_MANIFEST
    assert len(model.requests) == 2
    (feedback,) = model.parts(RetryPromptPart)
    assert "does not match the schema" in feedback
    assert "- name: Field required" in feedback
    assert "- version: Field required" in feedback


def test_generate_gives_up_after_retries_and_writes_nothing(runner, scripted, isolated_fs):
    model = scripted("this is not a manifest")
    result = runner.invoke(ai, ["generate", "greeter", "Greets people", "--retries", "1"])

    assert result.exit_code == 1
    assert "no manifest written" in result.output
    assert "must be a YAML mapping" in result.output
    assert "Traceback" not in result.output
    assert len(model.requests) == 2
    assert not (isolated_fs / "greeter.yaml").exists()


def test_generate_without_retries_asks_once(runner, scripted, isolated_fs):
    model = scripted("this is not a manifest")
    result = runner.invoke(ai, ["generate", "greeter", "Greets people", "--retries", "0"])

    assert result.exit_code == 1
    assert len(model.requests) == 1
    assert not (isolated_fs / "greeter.yaml").exists()


def test_generate_with_the_builtin_test_model_fails_cleanly(runner, isolated_fs):
    result = runner.invoke(ai, ["generate", "greeter", "Greets people", "-m", "test"])

    assert result.exit_code == 1
    assert "no manifest written" in result.output
    assert not (isolated_fs / "greeter.yaml").exists()


def test_generate_refuses_to_overwrite_without_force(runner, scripted, isolated_fs):
    model = scripted(VALID_MANIFEST)
    existing = isolated_fs / "greeter.yaml"
    existing.write_text("mine")

    result = runner.invoke(ai, ["generate", "greeter", "Greets people"])
    assert result.exit_code == 1
    assert "already exists" in result.output
    assert existing.read_text() == "mine"
    assert model.requests == []  # refused before spending any tokens

    result = runner.invoke(ai, ["generate", "greeter", "Greets people", "--force"])
    assert result.exit_code == 0, result.output
    assert existing.read_text() == VALID_MANIFEST


@pytest.mark.parametrize("name", ["../escape", "has space", "", "-leading-dash", "a/b"])
def test_generate_rejects_unsafe_cli_names(runner, scripted, isolated_fs, name):
    model = scripted(VALID_MANIFEST)
    result = runner.invoke(ai, ["generate", "--", name, "Greets people"])

    assert result.exit_code == 1
    assert "invalid CLI name" in result.output
    assert model.requests == []
    assert list(isolated_fs.iterdir()) == []


def test_generate_reports_a_failed_request(runner, monkeypatch, isolated_fs):
    def unauthorized(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise ModelHTTPError(status_code=401, model_name="function", body={"error": "invalid api key"})

    monkeypatch.setattr(cliffy_ai, "resolve_model", lambda name: FunctionModel(unauthorized))
    result = runner.invoke(ai, ["generate", "greeter", "Greets people"])

    assert result.exit_code == 1
    assert "failed: status_code: 401" in result.output
    assert "Traceback" not in result.output
    assert not (isolated_fs / "greeter.yaml").exists()


def test_generate_passes_max_tokens_to_the_model(runner, monkeypatch, isolated_fs):
    seen: list[object] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info.model_settings)
        return ModelResponse(parts=[TextPart(VALID_MANIFEST)])

    monkeypatch.setattr(cliffy_ai, "resolve_model", lambda name: FunctionModel(respond))
    result = runner.invoke(ai, ["generate", "greeter", "Greets people", "--max-tokens", "1234"])

    assert result.exit_code == 0, result.output
    assert seen == [{"max_tokens": 1234}]


# --- manifest validation ------------------------------------------------------------------------


def test_validate_accepts_a_valid_manifest():
    assert validate_manifest_yaml(VALID_MANIFEST, "greeter") == VALID_MANIFEST


@pytest.mark.parametrize(
    ("reply", "problem"),
    [
        ("key: [unclosed", "not valid YAML"),
        ("- just\n- a list", "must be a YAML mapping"),
        ("name: greeter\nversion: 0.1.0", "- commands: Field required"),
        (VALID_MANIFEST.replace("manifestVersion: v3", "manifestVersion: v2"), "v2 schema is deprecated"),
        (VALID_MANIFEST.replace("name: greeter", "name: other"), "`name` must be `greeter`"),
        (VALID_MANIFEST + "includes: [other.yaml]\n", "remove `includes`"),
        (BROKEN_PYTHON_MANIFEST, "not valid Python"),
    ],
)
def test_validate_explains_what_is_wrong(reply, problem):
    with pytest.raises(ManifestOutputError, match=problem):
        validate_manifest_yaml(reply, "greeter")


def test_validate_does_not_render_or_compile_jinja_manifests():
    manifest = VALID_MANIFEST.replace('print(f"Hello, {name}!")', "{% if x %}print(name){% endif %}")
    assert validate_manifest_yaml(manifest, "greeter") == manifest


def test_validate_accepts_the_init_template():
    template = CLIManifest.get_raw_template("greeter", json_schema=False)
    assert validate_manifest_yaml(template, "greeter").strip() == template.strip()


# --- ai ask -------------------------------------------------------------------------------------


def test_ask_prints_the_answer(runner, scripted):
    model = scripted("Use a `.` between the group and the subcommand.")
    result = runner.invoke(ai, ["ask", "How do I nest commands?"])

    assert result.exit_code == 0, result.output
    assert "Use a `.` between the group and the subcommand." in result.stdout
    assert "token usage:" in result.stderr
    assert "token usage:" not in result.stdout
    assert model.parts(UserPromptPart) == ["How do I nest commands?"]


def test_ask_is_grounded_in_the_shipped_schema_and_commands(runner, scripted):
    model = scripted("answer")
    assert runner.invoke(ai, ["ask", "How do I nest commands?"]).exit_code == 0

    instructions = model.instructions[0]
    assert instructions is not None
    # the real JSON schema, field by field
    for field in CLIManifest.model_fields:
        assert f'"{field}"' in instructions
    # the annotated template that `cli init` writes
    assert CLIManifest.get_template("mycli", json_schema=False) in instructions
    # every public cliffy command, read from the click group
    for name, command in cli.commands.items():
        if not command.hidden and name != "ai":
            assert f"`cli {name} " in instructions
    assert "`cli ai generate [OPTIONS] CLI_NAME DESCRIPTION`" in instructions
    assert "`rm` = `remove`" in instructions


def test_ask_includes_a_manifest_file_as_reference(runner, scripted, isolated_fs):
    model = scripted("answer")
    (isolated_fs / "greeter.yaml").write_text(VALID_MANIFEST)
    result = runner.invoke(ai, ["ask", "What does hello do?", "--cli", "greeter.yaml"])

    assert result.exit_code == 0, result.output
    (prompt,) = model.parts(UserPromptPart)
    assert prompt.startswith("What does hello do?")
    assert VALID_MANIFEST.strip() in prompt


def test_ask_includes_a_loaded_cli_as_reference(runner, scripted, isolated_fs):
    manifest = VALID_MANIFEST.replace("greeter", "aiasktestcli")
    (isolated_fs / "aiasktestcli.yaml").write_text(manifest)
    assert runner.invoke(cli, ["load", "aiasktestcli.yaml"]).exit_code == 0
    try:
        model = scripted("answer")
        result = runner.invoke(ai, ["ask", "What does hello do?", "--cli", "aiasktestcli"])
    finally:
        runner.invoke(cli, ["rm", "aiasktestcli"])

    assert result.exit_code == 0, result.output
    (prompt,) = model.parts(UserPromptPart)
    assert manifest.strip() in prompt


def test_ask_rejects_a_cli_that_is_not_loaded(runner, scripted):
    model = scripted("answer")
    result = runner.invoke(ai, ["ask", "What does hello do?", "--cli", "no-such-cli-loaded"])

    assert result.exit_code == 1
    assert "no-such-cli-loaded is not a loaded CLI" in result.output
    assert model.requests == []


def test_ask_reports_a_failed_request(runner, monkeypatch):
    def overloaded(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise ModelHTTPError(status_code=529, model_name="function", body={"error": "overloaded"})

    monkeypatch.setattr(cliffy_ai, "resolve_model", lambda name: FunctionModel(overloaded))
    result = runner.invoke(ai, ["ask", "What is cliffy?"])

    assert result.exit_code == 1
    assert "failed: status_code: 529" in result.output
    assert "Traceback" not in result.output
