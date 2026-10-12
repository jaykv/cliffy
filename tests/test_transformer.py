import os
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
