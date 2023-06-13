import contextlib
import os
import subprocess
from shutil import rmtree

import pytest
from click.testing import CliRunner

from cliffy.cli import build, bundle, load, remove
from cliffy.homer import get_clis, get_metadata

RICH_INSTALLED = False
with contextlib.suppress(ImportError):
    import rich

    if rich:
        RICH_INSTALLED = True

CLI_LOADS = {"hello", "db", "pydev", "template", "town", "environ", "penv"}
CLI_BUNDLES = {"hello", "db", "pydev", "template", "town", "environ", "penv"}
CLI_BUILDS = {"hello", "db", "pydev", "template", "town", "requires", "environ", "penv"}
CLI_LOAD_FAILS = {"requires"}
CLI_BUNDLE_FAILS = {"requires"}
CLI_TESTS = {
    "hello": [{"args": "bash", "resp": "hello from bash"}, {"args": "python", "resp": "hello from python"}],
    "town": [
        {"args": "land build test123 202str", "resp": "building land"},
        {"args": "land sell test123 --money 50", "resp": "selling"},
        {"args": "land list", "resp": "listing land"},
    ],
    "template": [
        {"args": "hello bash", "resp": "hello from bash"},
        {"args": "hello python", "resp": "hello from python"},
    ],
    "environ": [
        {"args": "hello", "resp": "hello"},
        {"args": "bye", "env": {"ENVIRON_BYE_TEXT": "goodbye"}, "resp": "goodbye"},
    ],
}

if not RICH_INSTALLED:
    CLI_LOADS.remove("db")
    CLI_BUNDLES.remove("db")
    CLI_LOAD_FAILS.add("db")
    CLI_BUNDLE_FAILS.add("db")


def setup_module():
    pytest.installed_clis = []  # type: ignore
    os.mkdir("test-builds")
    os.mkdir("test-bundles")


def teardown_module(cls):
    runner = CliRunner()
    for cli in pytest.installed_clis:  # type: ignore
        runner.invoke(remove, cli)

    clis = get_clis()
    for cli in clis:
        assert cli is None

    rmtree("test-builds")
    rmtree("test-bundles")


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
    result = runner.invoke(build, [f"examples/{cli_name}.yaml", "-o", "test-builds"])
    assert result.exit_code == 0


@pytest.mark.parametrize("cli_name", CLI_BUNDLES)
def test_cli_bundles(cli_name):
    runner = CliRunner()
    result = runner.invoke(bundle, [f"{cli_name}", "-o", "test-bundles"])
    assert result.exit_code == 0
    assert f"+ {cli_name} bundled" in result.stdout


@pytest.mark.parametrize("cli_name", CLI_BUNDLE_FAILS)
def test_cli_bundle_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(bundle, [f"{cli_name}", "-o", "test-bundles"])
    assert result.exit_code == 0
    assert f"~ {cli_name} not loaded" in result.stdout


@pytest.mark.parametrize("cli_name", CLI_TESTS.keys())
def test_cli_response(cli_name):
    for command in CLI_TESTS[cli_name]:
        environment = None
        if cli_env_vars := command.get("env"):
            environment = {**os.environ, **cli_env_vars}

        # loaded_cli_result = subprocess.run(
        #     f"{cli_name} {command['args']}",
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE,
        #     encoding="utf-8",
        #     env=environment,
        #     shell=True,
        # )
        # assert command["resp"] in loaded_cli_result.stdout

        built_cli_result = subprocess.run(
            f"./test-builds/{cli_name} {command['args']}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            env=environment,
            shell=True,
        )
        assert command["resp"] in built_cli_result.stdout

        bundled_cli_result = subprocess.run(
            f"./test-bundles/{cli_name} {command['args']}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            env=environment,
            shell=True,
        )
        assert command["resp"] in bundled_cli_result.stdout
