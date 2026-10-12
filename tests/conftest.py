import os
from shutil import rmtree

import pytest
import xdist
from click.testing import CliRunner

from cliffy.cli import remove_all_command
from cliffy.homer import get_clis


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


@pytest.fixture(scope="session", autouse=True)
def shiv_root(tmp_path_factory):
    """Zipapps built by the tests extract themselves here instead of into ``~/.shiv``.

    A shiv zipapp unpacks its bundled packages into ``SHIV_ROOT`` (default ``~/.shiv``) on every run
    of a new build, and nothing removes them. Set in ``os.environ`` so that it also reaches the
    subprocesses the tests start; each xdist worker runs this fixture for itself.
    """
    root = tmp_path_factory.mktemp("shiv-root")
    with pytest.MonkeyPatch.context() as environment:
        environment.setenv("SHIV_ROOT", str(root))
        yield root


@pytest.fixture
def isolated_fs(tmp_path, monkeypatch):
    """Run the test from an empty temporary working directory.

    Replaces ``CliRunner.isolated_filesystem``, deprecated in Click 8.5 and removed in Click 9.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path
