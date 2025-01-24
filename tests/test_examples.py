import os
import platform
import shlex
import subprocess
import sys

import pytest
from click.testing import CliRunner

from cliffy.cli import build_command, load_command, test_command
from cliffy.homer import get_metadata

try:
    import rich

    rich.print("~ rich installed")
    RICH_INSTALLED = True
except ImportError:
    RICH_INSTALLED = False

CLI_NAME_BUILDS = ["hello", "db", "pydev", "template", "town", "environ", "penv", "taskmaster", "todo", "nested-cli"]
CLI_MANIFEST_BUILDS = ["pydev", "requires", "penv", "taskmaster", "nested-cli"]
CLI_LOAD_FAILS = ["requires"]
CLI_BUILD_FAILS = ["requires"]
CLI_TESTS = {
    "hello": [{"args": "shell", "resp": "hello from shell"}, {"args": "python", "resp": "hello from python"}],
    "town": [
        {"args": "land build test123 202str", "resp": "building land"},
        {"args": "land sell test123 --money 50", "resp": "selling"},
        {"args": "land list", "resp": "listing land"},
        {"args": "home build test123 202str", "resp": "building home at test123 for None on land 202str"},
        {"args": "home bu test123 202str", "resp": "building home at test123 for None on land 202str"},
        {"args": "home s test123 --money 123", "resp": "selling home test123 for $123.00"},
    ],
    "template": [
        {"args": "hello shell --local-arg-2 test", "resp": "hello shell --test"},
        {"args": "hello python --local-arg-2 test2", "resp": "hello python --test2"},
    ],
    "environ": [
        {"args": "hello", "resp": "hello"},
        {"args": "bye", "env": {"ENVIRON_BYE_TEXT": "goodbye"}, "resp": "goodbye"},
        {"args": "read TESTVAR", "env": {"TESTVAR": "hello"}, "resp": "hello"},
        {"args": "hello-bye", "resp": "hello bye"},
    ],
    "db": [
        {"args": "list", "resp": "Listing all databases"},
        {"args": "ls", "resp": "Listing all databases"},
        {"args": "mk --name test", "resp": "Creating database test"},
        {"args": "v --name test --table test", "resp": "Viewing test table for test DB"},
    ],
    "nested-cli": [
        {"args": "group1 subgroup command1", "resp": "hello"},
        {"args": "group1 subgroup command2", "resp": "world"},
        {"args": "group2 command3", "resp": "foo"},
    ],
}
CLI_WITH_MANIFEST_TESTS = ["hello", "taskmaster"]

if not RICH_INSTALLED:
    CLI_NAME_BUILDS.remove("db")
    CLI_LOAD_FAILS.append("db")
    CLI_BUILD_FAILS.append("db")
    del CLI_TESTS["db"]
    CLI_NAME_BUILDS.remove("todo")
    CLI_LOAD_FAILS.append("todo")
    CLI_BUILD_FAILS.append("todo")

if platform.system() == "Windows":
    del CLI_TESTS["template"]
    if "todo" in CLI_NAME_BUILDS:
        CLI_NAME_BUILDS.remove("todo")


@pytest.mark.parametrize("cli_name", CLI_LOAD_FAILS)
def test_cli_load_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(load_command, [f"examples/{cli_name}.yaml"])
    assert result.exit_code == 1
    assert get_metadata(cli_name) is None


@pytest.mark.parametrize("cli_name", CLI_BUILD_FAILS)
def test_cli_build_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(build_command, [f"{cli_name}", "-o", "test-builds"])
    assert result.exit_code == 0
    assert f"~ {cli_name} not loaded" in result.stdout


@pytest.mark.parametrize("cli_name", CLI_MANIFEST_BUILDS)
def test_cli_builds_from_manifests(cli_name):
    runner = CliRunner()
    result = runner.invoke(build_command, [f"examples/{cli_name}.yaml", "-o", "test-manifest-builds"])
    assert result.exit_code == 0


@pytest.mark.parametrize("cli_name", CLI_TESTS.keys())
def test_cli_response_with_loads(cli_name):
    # load cli
    runner = CliRunner()
    result = runner.invoke(load_command, [f"examples/{cli_name}.yaml"])
    assert result.exit_code == 0

    # TODO: windows has issues here with running loaded CLIs
    if platform.system() != "Windows":
        for command in CLI_TESTS[cli_name]:
            environment = None
            if cli_env_vars := command.get("env"):
                environment = {**os.environ, **cli_env_vars}

            # run commands for loaded cli
            loaded_cli_result = subprocess.run(
                [cli_name] + command["args"].split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                env=environment,
            )
            assert command["resp"] in loaded_cli_result.stdout


@pytest.mark.parametrize("cli_name", CLI_TESTS.keys())
def test_cli_response_with_builds(cli_name):
    BUILD_DIR_PATH = "test-manifest-builds-response"
    # build cli
    runner = CliRunner()
    result = runner.invoke(build_command, [f"examples/{cli_name}.yaml", "-o", BUILD_DIR_PATH])
    assert result.exit_code == 0

    for command in CLI_TESTS[cli_name]:
        environment = None
        if cli_env_vars := command.get("env"):
            environment = {**os.environ, **cli_env_vars}

        # run commands for built cli
        executable_path = os.path.join(os.getcwd(), BUILD_DIR_PATH, cli_name)

        built_manifest_result = subprocess.run(
            [sys.executable, executable_path] + shlex.split(command["args"]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            env=environment,
        )
        assert command["resp"] in built_manifest_result.stdout


@pytest.mark.parametrize("cli_name", CLI_WITH_MANIFEST_TESTS)
def test_cli_tests_pass(cli_name):
    runner = CliRunner()
    result = runner.invoke(test_command, [f"examples/{cli_name}.yaml"])
    assert "All tests passed" in result.output
    assert result.exit_code == 0
