import os
from pathlib import Path

import pytest

from cliffy.commander import CLI
from cliffy.loader import Loader


@pytest.fixture
def loader_dirs(monkeypatch, tmp_path):
    bin_dir = tmp_path / "bin"
    clis_dir = tmp_path / "clis"
    bin_dir.mkdir()
    clis_dir.mkdir()
    monkeypatch.setattr("cliffy.loader.PYTHON_BIN", str(bin_dir))
    monkeypatch.setattr("cliffy.loader.CLIFFY_CLI_DIR", clis_dir)
    return bin_dir, clis_dir


def test_load_does_not_overwrite_foreign_executable(loader_dirs, capsys):
    bin_dir, clis_dir = loader_dirs
    # a manifest named `python` or `pip` would land on the interpreter's own executables
    real_python = bin_dir / "python3.x"
    real_python.write_bytes(b"\xcf\xfa\xed\xfe real interpreter")
    (bin_dir / "python").symlink_to(real_python)

    with pytest.raises(SystemExit):
        Loader.load_from_cli(CLI(name="python", version="1", code="cli = print"))

    assert real_python.read_bytes() == b"\xcf\xfa\xed\xfe real interpreter"
    assert (bin_dir / "python").is_symlink()
    assert not (clis_dir / "python.py").exists()
    assert "was not created by cliffy" in capsys.readouterr().err


def test_load_replaces_its_own_script(loader_dirs):
    bin_dir, clis_dir = loader_dirs

    Loader.load_from_cli(CLI(name="my-cli", version="1", code="cli = print"))
    Loader.load_from_cli(CLI(name="my-cli", version="2", code="cli = repr"))

    assert "from cliffy.clis.my_cli import cli" in (bin_dir / "my-cli").read_text()
    assert os.access(bin_dir / "my-cli", os.X_OK)
    assert (clis_dir / "my_cli.py").read_text() == "cli = repr"


def test_unload_removes_module_when_script_is_missing(loader_dirs):
    bin_dir, clis_dir = loader_dirs
    Loader.load_from_cli(CLI(name="my-cli", version="1", code="cli = print"))
    (bin_dir / "my-cli").unlink()

    Loader.unload_cli("my-cli")

    assert not (clis_dir / "my_cli.py").exists()


def test_unload_keeps_foreign_executable(loader_dirs):
    bin_dir, _ = loader_dirs
    foreign: Path = bin_dir / "pip"
    foreign.write_text("#!/bin/sh\necho pip\n")

    Loader.unload_cli("pip")

    assert foreign.exists()
