"""The test suite must not leave anything in the user's home directory."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_shiv_root_points_into_the_pytest_temp_directory(tmp_path_factory):
    # zipapps built by the tests extract themselves into SHIV_ROOT when they run. Without it they
    # go to ~/.shiv, one copy per build, and are never removed.
    shiv_root = Path(os.environ["SHIV_ROOT"]).resolve()
    assert shiv_root.is_relative_to(tmp_path_factory.getbasetemp().resolve())
    assert not shiv_root.is_relative_to((Path.home() / ".shiv").resolve())


def test_shiv_root_reaches_subprocesses():
    code = "import os; print(os.environ.get('SHIV_ROOT', ''))"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == os.environ["SHIV_ROOT"]


def test_docs_snippet_runner_uses_a_temporary_shiv_root(tmp_path):
    spec = importlib.util.spec_from_file_location("cliffy_docs_script", ROOT / "scripts" / "docs.py")
    assert spec and spec.loader
    docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(docs)

    env = docs.snippet_environment(tmp_path)
    assert Path(env["SHIV_ROOT"]).is_relative_to(tmp_path)
