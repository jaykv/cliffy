import glob
import os
import re
import tempfile

import pytest
import yaml

from cliffy.transformer import Transformer


def test_load_manifest_basic():
    test_manifest = {"name": "test-cli", "version": "1.0.0", "commands": {}}
    manifest_content = yaml.dump(test_manifest)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(manifest_content.encode())
        temp_file.flush()
        result = Transformer.load_manifest(temp_file)
        assert result["name"] == "test-cli"
        assert result["version"] == "1.0.0"


def test_load_manifest_with_vars():
    manifest_with_vars = {
        "vars": {"app_name": "test-app", "app_version": "2.0.0"},
        "name": "{{ app_name }}",
        "version": "{{ app_version }}",
    }
    manifest_content = yaml.dump(manifest_with_vars)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(manifest_content.encode())
        temp_file.flush()
        result = Transformer.load_manifest(temp_file)
        assert result["name"] == "test-app"
        assert result["version"] == "2.0.0"


def test_load_manifest_with_env_vars():
    os.environ["TEST_VAR"] = "test-value"
    manifest_with_env = {"vars": {"env_var": "{{ env.TEST_VAR }}"}, "name": "{{ env_var }}"}
    manifest_content = yaml.dump(manifest_with_env)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(manifest_content.encode())
        temp_file.flush()
        result = Transformer.load_manifest(temp_file)
        assert result["name"] == "test-value"


def test_load_manifest_invalid_yaml():
    invalid_manifest = "invalid: yaml: content:"
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(invalid_manifest.encode())
        temp_file.flush()
        with pytest.raises(SystemExit):
            Transformer.load_manifest(temp_file)


def test_resolve_includes():
    include_manifest = {"name": "include-cli", "version": "1.0.0", "commands": {"test-command": "print('hello')"}}

    with tempfile.NamedTemporaryFile(mode="w") as include_file:
        yaml.dump(include_manifest, include_file)
        include_file.flush()

        main_manifest = {"name": "main-cli", "includes": [include_file.name], "commands": {}}

        with tempfile.NamedTemporaryFile(mode="w") as main_file:
            yaml.dump(main_manifest, main_file)
            main_file.flush()

            with open(main_file.name) as f:
                transformer = Transformer(f, validate_requires=False)
                assert transformer.includes_config["name"] == "include-cli"
                assert transformer.includes_config["version"] == "1.0.0"
                assert "test-command" in transformer.manifest.commands


def load(path, **kwargs) -> Transformer:
    with open(path, encoding="utf-8") as f:
        return Transformer(f, validate_requires=False, **kwargs)


@pytest.mark.parametrize("content", ["", "# only a comment\n", "- a\n- b\n", "just text\n"])
def test_manifest_must_be_a_mapping(tmp_path, capsys, content):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(content)

    with pytest.raises(SystemExit):
        load(manifest_path)

    assert "must be a YAML mapping" in capsys.readouterr().err


def test_empty_vars_section(tmp_path, capsys):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text("name: t\nversion: '1'\nvars:\ncommands:\n  a: print(1)\n")

    # a validation error, not a TypeError traceback
    with pytest.raises(SystemExit):
        load(manifest_path)

    assert "error validating" in capsys.readouterr().err


def test_environment_values_are_not_rendered_as_templates(tmp_path, monkeypatch):
    # every value of os.environ used to be rendered by Jinja on each load: template syntax in any
    # environment variable ran as a template, and broke the load if it was not valid Jinja
    monkeypatch.delenv("CLIFFY_PWNED", raising=False)
    monkeypatch.setenv("CLIFFY_EVIL", "{{ cycler.__init__.__globals__.os.environ.__setitem__('CLIFFY_PWNED', '1') }}")
    monkeypatch.setenv("CLIFFY_ZSH_PROMPT", "%{%F{red}%}")
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text("name: t\nversion: '1'\ncommands:\n  a: print(1)\n")

    assert load(manifest_path).manifest.name == "t"
    assert "CLIFFY_PWNED" not in os.environ


def test_env_is_available_in_the_whole_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIFFY_GREETING", "{{ 7 * 7 }} hello")
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        "name: t\nversion: '1'\n"
        "vars:\n  from_vars: \"{{ env['CLIFFY_GREETING'] }}\"\n"
        "help: \"{{ env['CLIFFY_GREETING'] }} / {{ env.CLIFFY_GREETING }} / {{ from_vars }}\"\n"
        "commands:\n  a: print(1)\n"
    )

    # the value is used as it is: once in `vars`, and (new) anywhere else in the manifest
    assert load(manifest_path).manifest.help == "{{ 7 * 7 }} hello / {{ 7 * 7 }} hello / {{ 7 * 7 }} hello"


def test_includes_are_resolved_next_to_the_manifest(tmp_path, monkeypatch):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "shared.yaml").write_text("commands:\n  shared: print('shared')\n")
    (manifest_dir / "main.yaml").write_text(
        "name: t\nversion: '1'\nincludes: [shared.yaml]\ncommands:\n  a: print(1)\n"
    )
    monkeypatch.chdir(tmp_path)

    assert "shared" in load(manifest_dir / "main.yaml").manifest.commands


def test_includes_relative_to_working_directory_still_work(tmp_path, monkeypatch):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (tmp_path / "shared.yaml").write_text("commands:\n  shared: print('shared')\n")
    (manifest_dir / "main.yaml").write_text(
        "name: t\nversion: '1'\nincludes: [shared.yaml]\ncommands:\n  a: print(1)\n"
    )
    monkeypatch.chdir(tmp_path)

    assert "shared" in load(manifest_dir / "main.yaml").manifest.commands


def test_missing_include(tmp_path, capsys):
    manifest_path = tmp_path / "main.yaml"
    manifest_path.write_text("name: t\nversion: '1'\nincludes: [nope.yaml]\ncommands:\n  a: print(1)\n")

    with pytest.raises(SystemExit):
        load(manifest_path)

    assert "includes `nope.yaml`, which does not exist" in capsys.readouterr().err


def test_includes_are_merged_in_the_order_given(tmp_path):
    # the first manifest that defines a command wins. A set() made the winner depend on the hash seed.
    names = [f"include{i}.yaml" for i in range(8)]
    for i, name in enumerate(names):
        (tmp_path / name).write_text(f"commands:\n  who: print('{i}')\n")
    manifest_path = tmp_path / "main.yaml"
    manifest_path.write_text(f"name: t\nversion: '1'\nincludes: {names + names[:2]}\ncommands:\n  a: print(1)\n")

    T = load(manifest_path)

    assert T.includes_config["commands"]["who"] == "print('0')"


def test_circular_includes(tmp_path, capsys):
    (tmp_path / "main.yaml").write_text("name: t\nversion: '1'\nincludes: [a.yaml]\ncommands:\n  a: print(1)\n")
    (tmp_path / "a.yaml").write_text("includes: [b.yaml]\ncommands:\n  b: print(1)\n")
    (tmp_path / "b.yaml").write_text("includes: [a.yaml]\ncommands:\n  c: print(1)\n")

    with pytest.raises(SystemExit):
        load(tmp_path / "main.yaml")

    assert "circular include" in capsys.readouterr().err


def test_include_shared_by_two_includes_is_not_a_cycle(tmp_path):
    (tmp_path / "main.yaml").write_text(
        "name: t\nversion: '1'\nincludes: [a.yaml, b.yaml]\ncommands:\n  main: print(1)\n"
    )
    (tmp_path / "a.yaml").write_text("includes: [common.yaml]\ncommands:\n  a: print(1)\n")
    (tmp_path / "b.yaml").write_text("includes: [common.yaml]\ncommands:\n  b: print(1)\n")
    (tmp_path / "common.yaml").write_text("commands:\n  common: print(1)\n")

    assert set(load(tmp_path / "main.yaml").manifest.commands) == {"main", "a", "b", "common"}


@pytest.mark.parametrize("name", ["../../evil", "a/b", "my cli", "a.b", "-rf", "x\nimport os", "", "$(id)"], ids=repr)
def test_cli_name_must_be_a_safe_file_name(tmp_path, capsys, name):
    # the name is used in the path of the generated module, of the script in the interpreter's
    # bin directory and of the metadata file, and in the import line of that script
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.dump({"name": name, "version": "1", "commands": {"a": "print(1)"}}))

    with pytest.raises(SystemExit):
        load(manifest_path)

    assert "error validating" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["hello", "nested-cli", "my_cli", "_private", "cli2"])
def test_cli_name_valid(tmp_path, name):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.dump({"name": name, "version": "1", "commands": {"a": "print(1)"}}))

    assert load(manifest_path).cli.name == name


def write_requires_manifest(tmp_path, requires: list[str]):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.dump({"name": "t", "version": "1", "requires": requires, "commands": {"a": "print(1)"}})
    )
    return manifest_path


@pytest.mark.parametrize(
    "requirement",
    [
        "PyYAML>=6",  # KeyError: name was lowercased for the lookup only
        "pyyaml>=5,<99",  # InvalidVersion: only one specifier was understood
        "click~=8.0",  # reported as missing: `~=` was not understood
        "typer[all]>=0.9",  # reported as missing: extras were part of the name
        "rich_click",  # reported as missing: `_` and `-` are the same in package names
        "Jinja2",
        "pywin32>=1; sys_platform == 'no-such-platform'",
    ],
)
def test_requires_met(tmp_path, requirement):
    with open(write_requires_manifest(tmp_path, [requirement])) as f:
        assert Transformer(f).cli.requires == [requirement]


@pytest.mark.parametrize(
    "requirement, expected_error",
    [
        ("no-such-package-for-cliffy", "not installed"),
        ("PyYAML<1.0.0", "found version `"),
        ("click>=8,<8.1", "found version `"),
        ("not a requirement !!", "invalid requirement"),
    ],
)
def test_requires_unmet(tmp_path, capsys, requirement, expected_error):
    with open(write_requires_manifest(tmp_path, [requirement])) as f, pytest.raises(SystemExit):
        Transformer(f)

    error = capsys.readouterr().err
    assert f"requires `{requirement}` to be installed\n    {expected_error}" in error


MANIFEST_BODY = "name: t\nversion: '1'\ncommands:\n  a: print(1)\n"
SPEC_BLUEPRINT = (
    "from cliffy.blueprint import Blueprint\n\n\n"
    "class Spec(Blueprint):\n"
    "    name: str\n\n"
    "    def to_manifest(self):\n"
    "        return {'name': self.name, 'version': '1', 'commands': {'a': 'print(1)'}}\n"
)


@pytest.mark.parametrize(
    "version, expected_error",
    [
        ("v1", "v1 schema is deprecated"),
        ("v2", "v2 schema is deprecated"),
        ("v4", "Unrecognized manifest version `v4`"),
        ("3", "Unrecognized manifest version `3`"),
    ],
)
@pytest.mark.parametrize("where", ["manifest", "include", "blueprint_spec"])
def test_unsupported_manifest_version_is_an_error(tmp_path, capsys, where, version, expected_error):
    # the key was removed before validation, so `manifestVersion: v1` loaded as if it was v3
    manifest_path = tmp_path / "main.yaml"
    if where == "manifest":
        manifest_path.write_text(f"manifestVersion: {version}\n" + MANIFEST_BODY)
    elif where == "include":
        (tmp_path / "shared.yaml").write_text(f"manifestVersion: {version}\ncommands:\n  b: print(2)\n")
        manifest_path.write_text("includes: [shared.yaml]\n" + MANIFEST_BODY)
    else:
        (tmp_path / "spec.py").write_text(SPEC_BLUEPRINT)
        manifest_path.write_text(f"blueprint: spec.py\nmanifestVersion: {version}\nname: t\n")

    with pytest.raises(SystemExit):
        load(manifest_path)

    error = capsys.readouterr().err
    assert expected_error in error
    assert "manifestVersion: v3" in error
    assert ("shared.yaml" if where == "include" else "main.yaml") in error


@pytest.mark.parametrize("where", ["manifest", "include", "blueprint_spec"])
def test_current_manifest_version_is_accepted(tmp_path, where):
    manifest_path = tmp_path / "main.yaml"
    if where == "manifest":
        manifest_path.write_text("manifestVersion: v3\n" + MANIFEST_BODY)
    elif where == "include":
        (tmp_path / "shared.yaml").write_text("manifestVersion: v3\ncommands:\n  b: print(2)\n")
        manifest_path.write_text("includes: [shared.yaml]\n" + MANIFEST_BODY)
    else:
        (tmp_path / "spec.py").write_text(SPEC_BLUEPRINT)
        manifest_path.write_text("blueprint: spec.py\nmanifestVersion: v3\nname: t\n")

    assert load(manifest_path).cli.name == "t"


def test_example_manifests_use_the_current_version():
    for path in sorted(glob.glob("examples/*.yaml")):
        with open(path, encoding="utf-8") as manifest_file:
            declared = re.findall(r"^manifestVersion:\s*(\S+)", manifest_file.read(), re.MULTILINE)
        assert declared in ([], ["v3"]), path
