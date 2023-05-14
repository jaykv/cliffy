import pytest 
from click.testing import CliRunner
from cliffy.cli import load, remove
from cliffy.homer import get_clis, get_metadata

def setup_module():
    pytest.installed_clis = [] # type: ignore

def teardown_module(cls):
    runner = CliRunner()
    for cli in pytest.installed_clis: # type: ignore
        runner.invoke(remove, cli)
    
    clis = get_clis()
    for cli in clis:
        assert cli is None

@pytest.mark.parametrize("cli_name", ["hello", "db", "pydev", "template", "town"])
def test_cli_loads(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f'examples/{cli_name}.yaml'])
    assert result.exit_code == 0
    assert get_metadata(cli_name) is not None
    pytest.installed_clis.append(cli_name) # type: ignore


@pytest.mark.parametrize("cli_name", ["requires"])
def test_cli_fails(cli_name):
    runner = CliRunner()
    result = runner.invoke(load, [f'examples/{cli_name}.yaml'])
    assert result.exit_code == 1
    assert get_metadata(cli_name) is None
