import contextlib
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

CLI_LOADS = ["hello", "db", "pydev", "template", "town", "environ"]
CLI_BUNDLES = ["hello", "db", "pydev", "template", "town", "environ"]
CLI_BUILDS = ["hello", "db", "pydev", "template", "town", "requires", "environ"]
CLI_LOAD_FAILS = ["requires"]
CLI_BUNDLE_FAILS = ["requires"]

if not RICH_INSTALLED:
    CLI_LOADS = ["hello", "pydev", "template", "town", "environ"]
    CLI_BUNDLES = ["hello", "pydev", "template", "town", "environ"]
    CLI_LOAD_FAILS = ["requires", "db"]
    CLI_BUNDLE_FAILS = ["requires", "db"]


def setup_module():
    pytest.installed_clis = []  # type: ignore


def teardown_module(cls):
    runner = CliRunner()
    for cli in pytest.installed_clis:  # type: ignore
        runner.invoke(remove, cli)

    clis = get_clis()
    for cli in clis:
        assert cli is None

    rmtree('test-builds')
    rmtree('test-bundles')


@pytest.mark.parametrize("cli_name", CLI_LOADS)
def test_cli_loads(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f'examples/{cli_name}.yaml'])
    assert result.exit_code == 0
    assert get_metadata(cli_name) is not None
    pytest.installed_clis.append(cli_name)  # type: ignore


@pytest.mark.parametrize("cli_name", CLI_LOAD_FAILS)
def test_cli_load_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f'examples/{cli_name}.yaml'])
    assert result.exit_code == 1
    assert get_metadata(cli_name) is None


@pytest.mark.parametrize("cli_name", CLI_BUILDS)
def test_cli_builds(cli_name):
    runner = CliRunner()
    result = runner.invoke(build, [f'examples/{cli_name}.yaml', '-o', 'test-builds'])
    assert result.exit_code == 0


@pytest.mark.parametrize("cli_name", CLI_BUNDLES)
def test_cli_bundles(cli_name):
    runner = CliRunner()
    result = runner.invoke(bundle, [f'{cli_name}', '-o', 'test-bundles'])
    assert result.exit_code == 0
    assert f'+ {cli_name} bundled' in result.stdout


@pytest.mark.parametrize("cli_name", CLI_BUNDLE_FAILS)
def test_cli_bundle_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(bundle, [f'{cli_name}', '-o', 'test-bundles'])
    assert result.exit_code == 0
    assert f'~ {cli_name} not loaded' in result.stdout
