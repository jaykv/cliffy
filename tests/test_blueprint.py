import json
import textwrap
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pydantic import Field

from cliffy.blueprint import (
    Blueprint,
    BlueprintError,
    build_manifest,
    installed_blueprints,
    normalize_reference,
    resolve_blueprint,
)
from cliffy.cli import cli
from cliffy.homer import get_metadata
from cliffy.manifest import CLIManifest
from cliffy.reloader import Reloader
from cliffy.transformer import Transformer

EXAMPLES = Path(__file__).parent.parent / "examples" / "blueprints"
# pytest imports this file as a top-level module, so the blueprints below are importable by reference
SHOUT = f"{__name__}:Shout"

GREETER_BLUEPRINT = '''
from pydantic import Field

from cliffy.blueprint import Blueprint


class Greeter(Blueprint):
    """Greeter: one command per greeting

    More details that are not part of the description.
    """

    name: str
    greetings: dict[str, str] = Field(min_length=1)

    def to_manifest(self):
        commands = {key: f"print({text!r})" for key, text in self.greetings.items()}
        return {"name": self.name, "version": "1.0.0", "commands": commands}
'''


class Shout(Blueprint):
    """Shout: prints every word in uppercase"""

    name: str
    words: list[str] = Field(min_length=1)

    @classmethod
    def pre_validate(cls, raw: dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw.get("words"), str):
            raw = {**raw, "words": raw["words"].split()}
        return raw

    def to_manifest(self) -> CLIManifest:
        commands = {word: f"print({word.upper()!r})" for word in self.words}
        return CLIManifest(name=self.name, version="1.0.0", commands=commands)

    def post_manifest(self, manifest: CLIManifest) -> CLIManifest:
        manifest.help = f"{len(self.words)} words"
        return manifest

    def post_codegen(self, code: str) -> str:
        return code + "\n# shouted\n"


class Broken(Blueprint):
    name: str

    def to_manifest(self) -> dict[str, Any]:
        return {"name": self.name}


class Crashing(Blueprint):
    name: str

    def to_manifest(self) -> CLIManifest:
        raise RuntimeError("boom")


@pytest.fixture
def greeter(tmp_path):
    """A blueprint file and a spec that selects it with a relative `blueprint:` key."""
    (tmp_path / "greeter.py").write_text(GREETER_BLUEPRINT)
    spec = tmp_path / "specs" / "hi.yaml"
    spec.parent.mkdir()
    spec.write_text("blueprint: ../greeter.py\nname: bp-hi\ngreetings:\n  hello: hello there\n  bye: see you\n")
    return spec


def add_plugin(directory: Path, dist: str, entry_points: dict[str, str]) -> None:
    """Install a fake distribution that registers blueprints, the way a real package would."""
    # like a wheel does, the directory uses the normalized name (importlib.metadata splits it on the first "-")
    dist_info = directory / f"{dist.replace('-', '_')}-1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {dist}\nVersion: 1.0\n")
    lines = "".join(f"{name} = {target}\n" for name, target in entry_points.items())
    (dist_info / "entry_points.txt").write_text(f"[cliffy.blueprints]\n{lines}")


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    (plugin_dir / "bp_greeter_plugin.py").write_text(GREETER_BLUEPRINT)
    add_plugin(plugin_dir, "bp-greeter-plugin", {"greeter": "bp_greeter_plugin:Greeter"})
    monkeypatch.syspath_prepend(str(plugin_dir))
    return plugin_dir


def test_blueprint_base_is_abstract():
    with pytest.raises(TypeError):
        Blueprint()  # type: ignore[abstract]


def test_build_manifest_runs_hooks_in_order():
    spec, manifest = build_manifest(Shout, {"blueprint": "ignored", "name": "shout", "words": "a b"})

    assert isinstance(spec, Shout)
    assert spec.words == ["a", "b"]
    assert manifest.name == "shout"
    assert manifest.help == "2 words"
    assert set(manifest.commands) == {"a", "b"}


def test_build_manifest_reports_spec_errors_against_the_spec():
    with pytest.raises(BlueprintError) as error:
        build_manifest(Shout, {"name": "shout", "words": [], "wrods": ["a"]}, source="shout.yaml")

    message = str(error.value)
    assert "shout.yaml is not a valid Shout spec" in message
    assert "words: List should have at least 1 item" in message
    assert "wrods: Extra inputs are not permitted" in message


def test_build_manifest_reports_nested_locations():
    blueprint_cls = resolve_blueprint(str(EXAMPLES / "mcp_tools.py"))
    raw = {"name": "x", "tools": [{"name": "ok", "description": "d", "run": "return 1", "parameters": [{}]}]}
    with pytest.raises(BlueprintError, match=r"tools\[0\]\.parameters\[0\]\.name: Field required"):
        build_manifest(blueprint_cls, raw)


def test_build_manifest_reports_invalid_manifest_from_blueprint():
    with pytest.raises(BlueprintError) as error:
        build_manifest(Broken, {"name": "broken"})

    assert "blueprint Broken produced an invalid cliffy manifest" in str(error.value)
    assert "version: Field required" in str(error.value)


def test_build_manifest_reports_crashing_blueprint():
    with pytest.raises(BlueprintError, match="blueprint Crashing failed to transform spec: RuntimeError: boom"):
        build_manifest(Crashing, {"name": "crash"})


def test_describe_and_json_schema():
    assert Shout.describe() == "Shout: prints every word in uppercase"
    assert Broken.describe() == ""

    schema = Shout.spec_json_schema()
    assert schema["required"] == ["name", "words"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["blueprint"]["type"] == "string"
    assert "blueprint" not in Shout.model_json_schema()["properties"]


def test_resolve_file(greeter):
    blueprint_cls = resolve_blueprint("greeter.py", base_dir=greeter.parent.parent)
    assert blueprint_cls.__name__ == "Greeter"
    assert blueprint_cls.describe() == "Greeter: one command per greeting"

    assert resolve_blueprint(f"{greeter.parent.parent / 'greeter.py'}:Greeter").__name__ == "Greeter"


def test_resolve_file_errors(tmp_path):
    with pytest.raises(BlueprintError, match="blueprint file not found"):
        resolve_blueprint("missing.py", base_dir=tmp_path)

    (tmp_path / "empty.py").write_text("x = 1\n")
    with pytest.raises(BlueprintError, match="no blueprint found"):
        resolve_blueprint(str(tmp_path / "empty.py"))

    (tmp_path / "broken.py").write_text("import module_that_does_not_exist_xyz\n")
    with pytest.raises(BlueprintError, match=r"could not import blueprint file .*ModuleNotFoundError"):
        resolve_blueprint(str(tmp_path / "broken.py"))

    (tmp_path / "two.py").write_text(GREETER_BLUEPRINT + "\n\nclass Second(Greeter):\n    pass\n")
    with pytest.raises(BlueprintError, match=r"defines more than one blueprint \(Greeter, Second\)"):
        resolve_blueprint(str(tmp_path / "two.py"))
    assert resolve_blueprint(f"{tmp_path / 'two.py'}:Second").__name__ == "Second"

    with pytest.raises(BlueprintError, match="has no attribute `Missing`"):
        resolve_blueprint(f"{tmp_path / 'two.py'}:Missing")


def test_resolve_module_reference():
    assert resolve_blueprint(SHOUT) is Shout

    with pytest.raises(BlueprintError, match="defines more than one blueprint"):
        resolve_blueprint(__name__)

    with pytest.raises(BlueprintError, match="is not a blueprint"):
        resolve_blueprint(f"{__name__}:EXAMPLES")

    with pytest.raises(BlueprintError, match="is not a blueprint"):
        resolve_blueprint("cliffy.blueprint:Blueprint")

    with pytest.raises(BlueprintError, match=r"no blueprint found in `cliffy\.manifest`"):
        resolve_blueprint("cliffy.manifest")


def test_resolve_not_found_lists_installed(plugin):
    with pytest.raises(BlueprintError) as error:
        resolve_blueprint("no_such_blueprint_xyz")

    assert "blueprint `no_such_blueprint_xyz` not found" in str(error.value)
    assert "installed: greeter" in str(error.value)

    with pytest.raises(BlueprintError, match="empty blueprint reference"):
        resolve_blueprint("  ")


def test_resolve_installed_plugin(plugin):
    installed = {blueprint.name: blueprint for blueprint in installed_blueprints()}
    assert installed["greeter"].target == "bp_greeter_plugin:Greeter"
    assert installed["greeter"].package == "bp-greeter-plugin"

    assert resolve_blueprint("greeter").__name__ == "Greeter"


def test_resolve_ambiguous_plugin(plugin):
    add_plugin(plugin, "bp-other-plugin", {"greeter": "bp_greeter_plugin"})

    with pytest.raises(BlueprintError) as error:
        resolve_blueprint("greeter")

    assert "blueprint `greeter` is ambiguous" in str(error.value)
    assert "bp-greeter-plugin (bp_greeter_plugin:Greeter)" in str(error.value)
    assert "bp-other-plugin (bp_greeter_plugin)" in str(error.value)
    # a full reference still works
    assert resolve_blueprint("bp_greeter_plugin:Greeter").__name__ == "Greeter"


def test_resolve_plugin_that_fails_to_load(plugin):
    add_plugin(plugin, "bp-stale-plugin", {"stale": "bp_missing_module_xyz:Nope"})

    with pytest.raises(BlueprintError, match="could not load blueprint `stale`"):
        resolve_blueprint("stale")


def test_normalize_reference(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = tmp_path.resolve()

    assert normalize_reference("bp.py") == str(resolved / "bp.py")
    assert normalize_reference("sub/bp.py:Cls") == f"{resolved / 'sub' / 'bp.py'}:Cls"
    assert normalize_reference("bp.py", base_dir=tmp_path / "specs") == str(resolved / "specs" / "bp.py")
    assert normalize_reference("package.module:Cls") == "package.module:Cls"
    assert normalize_reference(" plugin-name ") == "plugin-name"


def test_transformer_applies_blueprint_from_file_key(greeter):
    with open(greeter) as spec:
        T = Transformer(spec)

    assert T.cli.name == "bp-hi"
    assert T.cli.blueprint == str((greeter.parent.parent / "greeter.py").resolve())
    assert isinstance(T.manifest, CLIManifest)
    assert set(T.manifest.commands) == {"hello", "bye"}
    assert "print('hello there')" in T.cli.code


def test_transformer_option_overrides_file_key_and_runs_post_codegen(tmp_path):
    spec_path = tmp_path / "shout.yaml"
    spec_path.write_text("blueprint: does-not-exist\nname: bp-shout\nwords: [hey]\n")

    with open(spec_path) as spec:
        T = Transformer(spec, blueprint=SHOUT)

    assert T.cli.blueprint == SHOUT
    assert T.cli.code.endswith("\n# shouted\n")
    assert "print('HEY')" in T.cli.code


def test_transformer_renders_jinja_before_the_blueprint(tmp_path):
    spec_path = tmp_path / "shout.yaml"
    spec_path.write_text("name: bp-shout\nwords: [\"{{ 'template' ~ 'd' }}\"]\n")

    with open(spec_path) as spec:
        T = Transformer(spec, blueprint=SHOUT)

    assert "print('TEMPLATED')" in T.cli.code


@pytest.mark.parametrize(
    ("content", "blueprint", "expected"),
    [
        ("blueprint: nope_xyz\nname: x\n", None, "blueprint `nope_xyz` not found"),
        ("blueprint: 12\nname: x\n", None, "`blueprint` must be a blueprint reference"),
        ("name: x\nwords: []\n", SHOUT, "is not a valid Shout spec"),
        ("name: x\n", f"{__name__}:Broken", "produced an invalid cliffy manifest"),
    ],
)
def test_transformer_blueprint_errors_exit_with_a_message(tmp_path, capsys, content, blueprint, expected):
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(content)

    with open(spec_path) as spec, pytest.raises(SystemExit) as exit_info:
        Transformer(spec, blueprint=blueprint)

    assert exit_info.value.code == 1
    assert expected in capsys.readouterr().err


def test_plain_manifest_is_untouched_without_blueprint():
    with open("examples/hello.yaml") as manifest:
        T = Transformer(manifest)

    assert T.blueprint is None
    assert T.cli.blueprint is None


def test_cli_render_run_and_validate_with_blueprint(greeter):
    runner = CliRunner()

    rendered = runner.invoke(cli, ["render", str(greeter)])
    assert rendered.exit_code == 0
    assert "print('see you')" in rendered.output

    ran = runner.invoke(cli, ["run", str(greeter), "--", "hello"])
    assert ran.exit_code == 0
    assert "hello there" in ran.output

    assert runner.invoke(cli, ["validate", str(greeter)]).exit_code == 0

    invalid = runner.invoke(cli, ["validate", str(greeter), "--blueprint", SHOUT])
    assert invalid.exit_code == 1
    assert "is not a valid Shout spec" in invalid.output


def test_cli_load_remembers_blueprint_for_update_and_info(greeter):
    runner = CliRunner()
    spec = greeter.with_name("loaded.yaml")
    spec.write_text("name: bp-loaded\nwords: [one]\n")

    loaded = runner.invoke(cli, ["load", str(spec), "--blueprint", SHOUT])
    assert loaded.exit_code == 0, loaded.output
    metadata = get_metadata("bp-loaded")
    assert metadata is not None
    assert metadata.blueprint == SHOUT

    info = runner.invoke(cli, ["info", "bp-loaded"])
    assert f"blueprint: {SHOUT}" in info.output

    # `update` has no --blueprint option: it has to reuse the one given to `load`
    spec.write_text("name: bp-loaded\nwords: [one, two]\n")
    updated = runner.invoke(cli, ["update", "bp-loaded"])
    assert updated.exit_code == 0, updated.output
    assert "Reloaded bp-loaded" in updated.output

    assert runner.invoke(cli, ["remove", "bp-loaded"]).exit_code == 0


def test_reloader_reloads_with_blueprint(tmp_path):
    spec = tmp_path / "reloaded.yaml"
    spec.write_text("name: bp-reloaded\nwords: [one]\n")

    Reloader.reload(str(spec), False, (), blueprint=SHOUT)

    metadata = get_metadata("bp-reloaded")
    assert metadata is not None
    assert metadata.blueprint == SHOUT
    assert CliRunner().invoke(cli, ["remove", "bp-reloaded"]).exit_code == 0


def test_cli_test_with_blueprint(tmp_path):
    (tmp_path / "tested.py").write_text(
        textwrap.dedent(
            """
            from cliffy.blueprint import Blueprint


            class Tested(Blueprint):
                name: str

                def to_manifest(self):
                    return {
                        "name": self.name,
                        "version": "1.0.0",
                        "commands": {"ping": "print('pong')"},
                        "tests": [{"ping": "assert result.output == 'pong\\\\n'"}],
                    }
            """
        )
    )
    spec = tmp_path / "tested.yaml"
    spec.write_text("name: bp-tested\n")

    result = CliRunner().invoke(cli, ["test", str(spec), "-b", str(tmp_path / "tested.py")])
    assert "All tests passed" in result.output
    assert result.exit_code == 0


def test_cli_docs_with_blueprint(greeter):
    result = CliRunner().invoke(cli, ["docs", str(greeter), "-o", str(greeter.parent)])
    assert result.exit_code == 0, result.output
    assert "see you" in (greeter.parent / "bp-hi.md").read_text() or "bye" in (greeter.parent / "bp-hi.md").read_text()


def test_cli_blueprint_list(plugin):
    runner = CliRunner()
    for command in (["blueprint", "list"], ["blueprints"]):
        result = runner.invoke(cli, command)
        assert result.exit_code == 0
        assert "greeter" in result.output
        assert "bp-greeter-plugin" in result.output
        assert "per greeting" in result.output


def test_cli_blueprint_list_shows_broken_plugins(plugin):
    add_plugin(plugin, "bp-stale-plugin", {"stale": "bp_missing_module_xyz:Nope"})

    result = CliRunner().invoke(cli, ["blueprint", "list"])
    assert result.exit_code == 0
    assert "stale" in result.output
    assert "error" in result.output


def test_cli_blueprint_schema(tmp_path):
    runner = CliRunner()

    printed = runner.invoke(cli, ["blueprint", "schema", SHOUT])
    assert printed.exit_code == 0
    assert json.loads(printed.output)["required"] == ["name", "words"]

    output = tmp_path / "shout.schema.json"
    written = runner.invoke(cli, ["blueprint", "schema", SHOUT, "-o", str(output)])
    assert written.exit_code == 0
    assert json.loads(output.read_text())["properties"]["blueprint"]["type"] == "string"

    missing = runner.invoke(cli, ["blueprint", "schema", "nope_xyz"])
    assert missing.exit_code == 1
    assert "not found" in missing.output


@pytest.mark.parametrize("example", ["tasks", "mcp_tools"])
def test_example_schema_is_up_to_date(example):
    """The schema files next to the examples give editor completion; they must match the blueprints."""
    blueprint_cls = resolve_blueprint(str(EXAMPLES / f"{example}.py"))
    committed = json.loads((EXAMPLES / f"{example}.schema.json").read_text())
    assert committed == blueprint_cls.spec_json_schema()


@pytest.mark.parametrize(
    ("spec", "args", "expected"),
    [
        ("tasks", ["greet"], "hello from tasks"),
        ("tasks", ["check"], "linting\ntesting"),
        ("tasks", ["--version"], "tasks, 0.1.0"),
        ("text-tools", ["format-text", " hi there ", "--uppercase", "--trim"], "HI THERE\n"),
        ("text-tools", ["count-words", "one two three"], '"words": 3'),
        ("text-tools", ["extract-entities", "a@b.io on 1/2/2026", "--entity-types", "emails"], "a@b.io"),
        ("text-tools", ["repeat", "ab", "--times", "3", "--separator", "-"], "ab-ab-ab"),
        ("text-tools", ["tools"], '"name": "extract_entities"'),
    ],
)
def test_example_specs_run(capfd, spec, args, expected):
    result = CliRunner().invoke(cli, ["run", str(EXAMPLES / f"{spec}.yaml"), "--", *args])

    assert result.exit_code == 0, result.output
    # task lines run in subprocesses, their output is only visible on the real stdout
    assert expected in result.output + capfd.readouterr().out


@pytest.mark.parametrize("spec", ["tasks", "text-tools"])
def test_example_specs_validate(spec):
    result = CliRunner().invoke(cli, ["validate", str(EXAMPLES / f"{spec}.yaml")])
    assert result.exit_code == 0, result.output


def test_example_spec_tests_pass():
    result = CliRunner().invoke(cli, ["test", str(EXAMPLES / "text-tools.yaml")])
    assert "All tests passed" in result.output
    assert result.exit_code == 0


def test_example_mcp_blueprint_rejects_bad_specs():
    blueprint_cls = resolve_blueprint(str(EXAMPLES / "mcp_tools.py"))
    tool = {"description": "d", "run": "return 1"}

    with pytest.raises(BlueprintError, match="`serve` is a reserved name"):
        build_manifest(blueprint_cls, {"name": "x", "tools": {"serve": tool}})

    with pytest.raises(BlueprintError, match="duplicate tool names: same"):
        build_manifest(blueprint_cls, {"name": "x", "tools": [{"name": "same", **tool}, {"name": "same", **tool}]})

    required_flag = {**tool, "parameters": [{"name": "flag", "type": "boolean", "required": True}]}
    with pytest.raises(BlueprintError, match="a boolean parameter is a flag and cannot be required"):
        build_manifest(blueprint_cls, {"name": "x", "tools": {"ok": required_flag}})
