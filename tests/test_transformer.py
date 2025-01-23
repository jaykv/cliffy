import os
import tempfile
import yaml

from cliffy.transformer import Transformer
import pytest


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
