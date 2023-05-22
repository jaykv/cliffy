from shutil import rmtree

import pytest
from click.testing import CliRunner

from cliffy.cli import build, bundle, load, remove
from cliffy.homer import get_clis, get_metadata


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


@pytest.mark.parametrize("cli_name", ["hello", "db", "pydev", "template", "town", "environ"])
def test_cli_loads(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f'examples/{cli_name}.yaml'])
    assert result.exit_code == 0
    assert get_metadata(cli_name) is not None
    pytest.installed_clis.append(cli_name)  # type: ignore


@pytest.mark.parametrize("cli_name", ["requires"])
def test_cli_load_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f'examples/{cli_name}.yaml'])
    assert result.exit_code == 1
    assert get_metadata(cli_name) is None


@pytest.mark.parametrize("cli_name", ["hello", "db", "pydev", "template", "town", "requires", "environ"])
def test_cli_builds(cli_name):
    runner = CliRunner()
    result = runner.invoke(build, [f'examples/{cli_name}.yaml', '-o', 'test-builds'])
    assert result.exit_code == 0


@pytest.mark.parametrize("cli_name", ["hello", "db", "pydev", "template", "town", "environ"])
def test_cli_bundles(cli_name):
    runner = CliRunner()
    result = runner.invoke(bundle, [f'{cli_name}', '-o', 'test-bundles'])
    assert result.exit_code == 0
    assert f'+ {cli_name} bundled' in result.stdout


@pytest.mark.parametrize("cli_name", ["requires"])
def test_cli_bundle_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(bundle, [f'{cli_name}', '-o', 'test-bundles'])
    assert result.exit_code == 0
    assert f'~ {cli_name} not loaded' in result.stdout
