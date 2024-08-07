import os
import platform
import shlex
import subprocess
import sys
from shutil import rmtree

import pytest
from click.testing import CliRunner

from cliffy.cli import build, load, remove
from cliffy.homer import get_clis, get_metadata

try:
    import rich

    rich.print("~ rich installed")
    RICH_INSTALLED = True
except ImportError:
    RICH_INSTALLED = False

CLI_LOADS = {"hello", "db", "pydev", "template", "town", "environ", "penv"}
CLI_BUILDS = {"hello", "db", "pydev", "template", "town", "environ", "penv"}
CLI_MANIFEST_BUILDS = {"hello", "db", "pydev", "template", "town", "requires", "environ", "penv"}
CLI_LOAD_FAILS = {"requires"}
CLI_BUILD_FAILS = {"requires"}
CLI_TESTS = {
    "hello": [{"args": "bash", "resp": "hello from bash"}, {"args": "python", "resp": "hello from python"}],
    "town": [
        {"args": "land build test123 202str", "resp": "building land"},
        {"args": "land sell test123 --money 50", "resp": "selling"},
        {"args": "land list", "resp": "listing land"},
        {"args": "home build test123 202str", "resp": "building home"},
        {"args": "home bu test123 202str", "resp": "building home"},
        {"args": "home s test123", "resp": "selling home"},
    ],
    "template": [
        {"args": "hello bash", "resp": "hello from bash"},
        {"args": "hello python", "resp": "hello from python"},
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
        {"args": "mk", "resp": "Creating database"},
        {"args": "rm", "resp": "Deleting database"},
    ],
}

if not RICH_INSTALLED:
    CLI_LOADS.remove("db")
    CLI_BUILDS.remove("db")
    CLI_LOAD_FAILS.add("db")
    CLI_BUILD_FAILS.add("db")
    del CLI_TESTS["db"]

if platform.system() == "Windows":
    del CLI_TESTS["template"]


def setup_module():
    pytest.installed_clis = []  # type: ignore
    os.mkdir("test-builds")
    os.mkdir("test-manifest-builds")


def teardown_module(cls):
    runner = CliRunner()
    for cli in pytest.installed_clis:  # type: ignore
        runner.invoke(remove, cli)

    clis = get_clis()
    for cli in clis:
        assert cli is None

    rmtree("test-builds")
    rmtree("test-manifest-builds")


@pytest.mark.parametrize("cli_name", CLI_LOADS)
def test_cli_loads(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f"examples/{cli_name}.yaml"])
    assert result.exit_code == 0
    assert get_metadata(cli_name) is not None
    pytest.installed_clis.append(cli_name)  # type: ignore


@pytest.mark.parametrize("cli_name", CLI_LOAD_FAILS)
def test_cli_load_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f"examples/{cli_name}.yaml"])
    assert result.exit_code == 1
    assert get_metadata(cli_name) is None


@pytest.mark.parametrize("cli_name", CLI_BUILDS)
def test_cli_builds(cli_name):
    runner = CliRunner()
    result = runner.invoke(build, [f"{cli_name}", "-o", "test-builds"])
    assert result.exit_code == 0
    assert f"+ {cli_name} built" in result.stdout


@pytest.mark.parametrize("cli_name", CLI_BUILD_FAILS)
def test_cli_build_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(build, [f"{cli_name}", "-o", "test-builds"])
    assert result.exit_code == 0
    assert f"~ {cli_name} not loaded" in result.stdout


@pytest.mark.parametrize("cli_name", CLI_MANIFEST_BUILDS)
def test_cli_builds_from_manifests(cli_name):
    runner = CliRunner()
    result = runner.invoke(build, [f"examples/{cli_name}.yaml", "-o", "test-manifest-builds"])
    assert result.exit_code == 0


@pytest.mark.parametrize("cli_name", CLI_TESTS.keys())
def test_cli_response(cli_name):
    for command in CLI_TESTS[cli_name]:
        environment = None
        if cli_env_vars := command.get("env"):
            environment = {**os.environ, **cli_env_vars}

        if platform.system() != "Windows":
            loaded_cli_result = subprocess.run(
                [cli_name] + command["args"].split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                env=environment,
            )
            assert command["resp"] in loaded_cli_result.stdout

        executable_path = os.path.join(os.getcwd(), "test-manifest-builds", cli_name)

        built_manifest_result = subprocess.run(
            [sys.executable, executable_path] + shlex.split(command["args"]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            env=environment,
        )
        assert command["resp"] in built_manifest_result.stdout

        executable_path = os.path.join(os.getcwd(), "test-builds", cli_name)

        built_cli_result = subprocess.run(
            [sys.executable, executable_path] + shlex.split(command["args"]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            env=environment,
        )
        assert command["resp"] in built_cli_result.stdout
