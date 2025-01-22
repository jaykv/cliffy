import os
from cliffy.cli import remove_all_command
from shutil import rmtree
from cliffy.homer import get_clis
from click.testing import CliRunner
import pytest
import xdist


@pytest.hookimpl()
def pytest_sessionstart(session):
    if xdist.is_xdist_worker(session):
        return
    rmtree("test-builds", ignore_errors=True)
    rmtree("test-manifest-builds", ignore_errors=True)
    rmtree("test-manifest-builds-response", ignore_errors=True)
    os.mkdir("test-builds")
    os.mkdir("test-manifest-builds")
    os.mkdir("test-manifest-builds-response")


@pytest.hookimpl()
def pytest_sessionfinish(session, exitstatus):
    if xdist.is_xdist_worker(session):
        return
    runner = CliRunner()
    runner.invoke(remove_all_command)
    clis = get_clis()
    for cli in clis:
        assert cli is None

    rmtree("test-builds", ignore_errors=True)
    rmtree("test-manifest-builds", ignore_errors=True)
    rmtree("test-manifest-builds-response", ignore_errors=True)
