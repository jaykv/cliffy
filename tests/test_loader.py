import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from cliffy.cli import cli as cliffy_cli
from cliffy.commander import CLI
from cliffy.homer import get_clis, get_metadata, save_metadata
from cliffy.loader import Loader, LoaderError


@pytest.fixture
def loader_dirs(monkeypatch, tmp_path):
    bin_dir = tmp_path / "bin"
    clis_dir = tmp_path / "clis"
    metadata_dir = tmp_path / "metadata"
    bin_dir.mkdir()
    clis_dir.mkdir()
    metadata_dir.mkdir()
    monkeypatch.setattr("cliffy.loader.PYTHON_BIN", str(bin_dir))
    monkeypatch.setattr("cliffy.loader.CLIFFY_CLI_DIR", clis_dir)
    monkeypatch.setattr("cliffy.homer.CLIFFY_METADATA_DIR", metadata_dir)
    return bin_dir, clis_dir


def load(tmp_path: Path, name: str, code: str = "cli = print") -> None:
    """What `cli load` does for a manifest: the launcher, the module and the metadata record."""
    manifest_path = tmp_path / f"{name}.yaml"
    manifest_path.write_text(f"name: {name}\n")
    cli = CLI(name=name, version="1", code=code)
    Loader.load_from_cli(cli)
    save_metadata(str(manifest_path), cli)


def symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as e:
        # i.e. Windows without the privilege to create symbolic links
        pytest.skip(f"symbolic links cannot be created here: {e}")


def test_load_does_not_overwrite_foreign_executable(loader_dirs, capsys):
    bin_dir, clis_dir = loader_dirs
    # a manifest named `python` or `pip` would land on the interpreter's own executables
    real_python = bin_dir / "python3.x"
    real_python.write_bytes(b"\xcf\xfa\xed\xfe real interpreter")
    symlink_or_skip(bin_dir / "python", real_python)

    with pytest.raises(SystemExit):
        Loader.load_from_cli(CLI(name="python", version="1", code="cli = print"))

    assert real_python.read_bytes() == b"\xcf\xfa\xed\xfe real interpreter"
    assert (bin_dir / "python").is_symlink()
    assert not (clis_dir / "python.py").exists()
    assert "was not created by cliffy" in capsys.readouterr().err


@pytest.mark.parametrize(
    "content",
    [
        # a script of someone else that happens to import a loaded CLI
        "#!/usr/bin/env python3\nfrom cliffy.clis.other import cli\ncli(['--version'])\n",
        # the launcher of another CLI, i.e. a copy
        Loader.get_cli_script("other"),
        # cliffy's own launcher, edited by hand
        Loader.get_cli_script("tool") + "\nprint('my change')\n",
    ],
    ids=["imports_a_loaded_cli", "launcher_of_another_cli", "edited_launcher"],
)
def test_load_does_not_overwrite_script_it_did_not_write(loader_dirs, capsys, content):
    bin_dir, clis_dir = loader_dirs
    (bin_dir / "tool").write_text(content)

    with pytest.raises(SystemExit):
        Loader.load_from_cli(CLI(name="tool", version="1", code="cli = print"))

    assert (bin_dir / "tool").read_text() == content
    assert not (clis_dir / "tool.py").exists()
    assert "was not created by cliffy" in capsys.readouterr().err


def test_load_does_not_follow_link_to_a_launcher(loader_dirs, tmp_path):
    bin_dir, _ = loader_dirs
    elsewhere = tmp_path / "elsewhere"
    elsewhere.write_text(Loader.get_cli_script("tool"))
    symlink_or_skip(bin_dir / "tool", elsewhere)

    with pytest.raises(SystemExit):
        Loader.load_from_cli(CLI(name="tool", version="1", code="cli = print"))

    assert (bin_dir / "tool").is_symlink()
    assert elsewhere.read_text() == Loader.get_cli_script("tool")


def test_load_does_not_replace_file_that_appears_after_the_check(loader_dirs, monkeypatch):
    bin_dir, clis_dir = loader_dirs
    (bin_dir / "tool").write_text("#!/bin/sh\necho created by someone else, after the check\n")
    # the check ran before that file existed
    monkeypatch.setattr(Loader, "script_state", staticmethod(lambda script_path, cli_name: "missing"))

    with pytest.raises(SystemExit):
        Loader.load_from_cli(CLI(name="tool", version="1", code="cli = print"))

    assert "created by someone else" in (bin_dir / "tool").read_text()
    assert not (clis_dir / "tool.py").exists()


def test_load_replaces_its_own_script(loader_dirs):
    bin_dir, clis_dir = loader_dirs

    Loader.load_from_cli(CLI(name="my-cli", version="1", code="cli = print"))
    Loader.load_from_cli(CLI(name="my-cli", version="2", code="cli = repr"))

    assert "from cliffy.clis.my_cli import cli" in (bin_dir / "my-cli").read_text()
    assert os.access(bin_dir / "my-cli", os.X_OK)
    assert (clis_dir / "my_cli.py").read_text() == "cli = repr"
    # written to a temporary file next to the target and moved into place
    assert sorted(path.name for path in bin_dir.iterdir()) == ["my-cli"]
    assert sorted(path.name for path in clis_dir.iterdir()) == ["my_cli.py"]


def test_load_replaces_script_written_with_another_interpreter_path(loader_dirs):
    bin_dir, _ = loader_dirs
    # the same environment reached through another path, i.e. bin/python3 instead of bin/python
    body = Loader.get_cli_script("my-cli").split("\n", 1)[1]
    (bin_dir / "my-cli").write_text(f"#!/some/venv/bin/python3\n{body}")

    Loader.load_from_cli(CLI(name="my-cli", version="1", code="cli = print"))

    assert (bin_dir / "my-cli").read_text() == Loader.get_cli_script("my-cli")


def test_unload_removes_script_and_module(loader_dirs):
    bin_dir, clis_dir = loader_dirs
    Loader.load_from_cli(CLI(name="my-cli", version="1", code="cli = print"))

    Loader.unload_cli("my-cli")

    assert list(bin_dir.iterdir()) == []
    assert list(clis_dir.iterdir()) == []


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

    with pytest.raises(LoaderError, match="was not created by cliffy"):
        Loader.unload_cli("pip")

    assert foreign.exists()


def test_unload_keeps_the_cli_runnable_when_its_script_was_edited(loader_dirs):
    bin_dir, clis_dir = loader_dirs
    Loader.load_from_cli(CLI(name="my-cli", version="1", code="cli = print"))
    edited = (bin_dir / "my-cli").read_text() + "\nprint('my change')\n"
    (bin_dir / "my-cli").write_text(edited)

    with pytest.raises(LoaderError):
        Loader.unload_cli("my-cli")

    # the module used to be deleted, which left a script that failed with ModuleNotFoundError
    assert (bin_dir / "my-cli").read_text() == edited
    assert (clis_dir / "my_cli.py").read_text() == "cli = print"


def test_unload_puts_the_script_back_when_the_module_cannot_be_removed(loader_dirs, monkeypatch):
    bin_dir, clis_dir = loader_dirs
    Loader.load_from_cli(CLI(name="my-cli", version="1", code="cli = print"))
    real_unlink = os.unlink

    def unlink(path, *args, **kwargs):
        if str(path).endswith("my_cli.py"):
            raise PermissionError(13, "Permission denied", str(path))
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr("cliffy.loader.os.unlink", unlink)

    with pytest.raises(LoaderError, match="Permission denied"):
        Loader.unload_cli("my-cli")

    assert (bin_dir / "my-cli").read_text() == Loader.get_cli_script("my-cli")
    assert os.access(bin_dir / "my-cli", os.X_OK)
    assert (clis_dir / "my_cli.py").exists()


@pytest.mark.parametrize("command", ["rm", "rm-all"])
def test_rm_leaves_nothing_half_removed_when_the_script_was_edited(loader_dirs, tmp_path, command):
    bin_dir, clis_dir = loader_dirs
    load(tmp_path, "kept")
    (bin_dir / "kept").write_text("#!/bin/sh\necho mine now\n")

    result = CliRunner().invoke(cliffy_cli, [command] if command == "rm-all" else [command, "kept"])

    assert result.exit_code == 1, result.output
    assert "was not created by cliffy" in result.output
    # still listed, and its module is still there: the metadata used to be removed first
    assert [cli.cli_name for cli in get_clis()] == ["kept"]
    assert (clis_dir / "kept.py").exists()
    assert (bin_dir / "kept").read_text() == "#!/bin/sh\necho mine now\n"


def test_rm_removes_script_module_and_metadata(loader_dirs, tmp_path):
    bin_dir, clis_dir = loader_dirs
    load(tmp_path, "gone")

    result = CliRunner().invoke(cliffy_cli, ["rm", "gone"])

    assert result.exit_code == 0, result.output
    assert list(bin_dir.iterdir()) == [] and list(clis_dir.iterdir()) == []
    assert get_metadata("gone") is None


@pytest.mark.parametrize("name", ["../outside", "../../outside", "sub/outside", "..", ".", "a\\b", "", "-x", "a b"])
def test_names_that_are_paths_are_not_cli_names(loader_dirs, name):
    with pytest.raises(ValueError, match="not a valid CLI name"):
        Loader.get_cli_path(name)
    with pytest.raises(ValueError, match="not a valid CLI name"):
        Loader.get_cli_script_path(name)
    with pytest.raises(ValueError, match="not a valid CLI name"):
        Loader.unload_cli(name)


@pytest.mark.parametrize("command", ["rm", "update", "info", "build", "docs"])
@pytest.mark.parametrize("name", ["../outside", "../../outside"])
def test_commands_do_not_resolve_a_name_outside_of_cliffys_directories(loader_dirs, tmp_path, command, name):
    load(tmp_path, "inside")
    # what a name with `..` in it would have reached: files one and two levels above the directories
    # that hold the launchers, the modules and the metadata records
    record = next((tmp_path / "metadata").glob("*/inside.json")).read_text()
    outside = [tmp_path / "outside", tmp_path / "outside.py", tmp_path / "outside.json"]
    outside += [tmp_path / "metadata" / "outside.json", tmp_path.parent / "outside.json"]
    for path in outside:
        path.write_text(Loader.get_cli_script("outside") if path.suffix == "" else record)

    try:
        result = CliRunner().invoke(cliffy_cli, [command, name])

        assert result.exit_code == 1, result.output
        assert "not a valid CLI name" in result.output
        for path in outside:
            assert path.exists(), path
    finally:
        (tmp_path.parent / "outside.json").unlink(missing_ok=True)
    assert [cli.cli_name for cli in get_clis()] == ["inside"]
