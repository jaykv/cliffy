"""`cli build --target`: the script and native targets, and what all targets share."""

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from importlib import metadata
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cliffy import builder
from cliffy.builder import (
    MIN_PYTHON,
    PYAPP_VERSION,
    SCRIPT_INTERPRETER,
    TARGETS,
    BuildJob,
    BuildResult,
    BuildTarget,
    NativeTarget,
    build_cli,
    build_cli_from_manifest,
    find_python_distribution,
    get_inline_metadata,
    get_project_name,
    get_project_version,
    get_standalone_code,
    pyapp_environment,
    write_wheel_project,
)
from cliffy.cli import cli
from cliffy.homer import CLIMetadata
from cliffy.transformer import Transformer

EXAMPLES = Path(__file__).parent.parent / "examples"
TYPER_PIN = f"typer=={metadata.version('typer')}"
# a pipe and a chain: these go through the pybash helper, a plain `$ echo` does not
SHELL_MANIFEST = """name: piper
version: 1.2.0
help: Shell operators in a built CLI
commands:
  shout:
    help: Upper-case a word
    params: [word: str!]
    run: |
      out = $ echo f{word} | tr a-z A-Z && echo done
      print(out.decode().split())
  plain: $ echo plain
"""
PLAIN_MANIFEST = "name: plain\nversion: '1'\ncommands:\n  hi: print('hi')\n"


@pytest.fixture
def shell_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "piper.yaml"
    manifest.write_text(SHELL_MANIFEST)
    return manifest


@pytest.fixture
def temp_dir(monkeypatch, tmp_path):
    """Makes the tempfile module create its files in an empty directory"""
    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))
    return temp_dir


def job(tmp_path: Path, **fields: object) -> BuildJob:
    defaults: dict = {
        "cli_name": "my-tool",
        "version": "1.2.0",
        "code": "import typer\ncli = typer.Typer()\n",
        "requirements": ["requests>=2", TYPER_PIN],
        "output_dir": tmp_path,
    }
    return BuildJob(**{**defaults, **fields})


def clean_environment(home: Path, **extra: str) -> dict[str, str]:
    """Environment of another machine: nothing of the test run leaks into the artifact"""
    return {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "PYTHONNOUSERSITE": "1", **extra}


def inline_metadata(script: str) -> dict:
    """The PEP 723 block of a script, parsed the way a script runner reads it"""
    lines = script.splitlines()
    start, end = lines.index("# /// script"), lines.index("# ///")
    return tomllib.loads("\n".join(line.removeprefix("#").removeprefix(" ") for line in lines[start + 1 : end]))


# --- shared by all targets ----------------------------------------------------------------------


def test_targets_are_registered_by_name_behind_one_interface():
    assert list(TARGETS) == ["zipapp", "script", "native"]
    for name, target in TARGETS.items():
        assert isinstance(target, BuildTarget)
        assert target.name == name
        assert target.description


def test_unknown_target_is_a_failed_build(tmp_path):
    script = tmp_path / "demo.py"
    script.write_text("print(1)\n")

    result = build_cli("demo", str(script), output_dir=str(tmp_path / "out"), target="wasm")

    assert result.exit_code == 1
    assert result.output == "unknown build target `wasm`: choose one of zipapp, script, native"
    assert not (tmp_path / "out").exists()

    rejected = CliRunner().invoke(cli, ["build", str(script), "--target", "wasm"])
    assert rejected.exit_code == 2
    assert "wasm" in rejected.output
    assert "Traceback" not in rejected.output


def test_standalone_code_pastes_the_shell_helper_in(shell_manifest):
    with open(shell_manifest) as manifest_io:
        from cliffy.transformer import Transformer

        generated = Transformer(manifest_io).cli.code
    assert "import pybash.runtime as _pybash\n" in generated

    code = get_standalone_code(generated)

    assert "import pybash" not in code
    assert "class _pybash:" in code
    # the header names the cliffy version and nothing that changes between two builds
    assert code.startswith(f"## Generated piper with cliffy {metadata.version('cliffy')}\n")
    # runs where pybash cannot be imported
    with patch.dict(sys.modules, {"pybash": None, "pybash.runtime": None}):
        namespace: dict = {"__name__": "piper"}
        exec(compile(code, "piper.py", "exec"), namespace)
        output = namespace["_pybash"].run([["echo", "a"], "|", ["tr", "a", "b"]], capture=True)
    assert output == b"b\n"


def test_standalone_code_leaves_a_cli_without_shell_operators_alone():
    code = "## Generated demo with cliffy 0.7.0\nimport subprocess\nsubprocess.run(['ls'])\n"

    assert get_standalone_code(code) == code


def test_standalone_code_drops_the_timestamp_of_a_cli_loaded_by_an_older_cliffy():
    # cliffy 0.6 wrote the time of generation into the header: a CLI loaded back then is built from that script
    code = "## Generated demo on 2026-01-01 00:00:00\nimport subprocess\nsubprocess.run(['ls'])\n"

    assert get_standalone_code(code) == "## Generated demo with cliffy\nimport subprocess\nsubprocess.run(['ls'])\n"


def test_two_builds_of_a_manifest_ship_the_same_code(tmp_path):
    manifest_path = tmp_path / "same.yaml"
    manifest_path.write_text("name: same\nversion: '1'\ncommands:\n  a: $ echo a | tr a b\n")
    shipped = []
    for _ in range(2):
        with open(manifest_path) as manifest_io:
            shipped.append(get_standalone_code(Transformer(manifest_io).cli.code))

    assert shipped[0] == shipped[1]


def test_zipapp_bundles_the_shell_helper_instead_of_pybash(shell_manifest, tmp_path):
    pip_run = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("cliffy.builder.subprocess.run", return_value=pip_run) as mock_pip, open(shell_manifest) as manifest_io:
        _, result = build_cli_from_manifest(manifest_io, output_dir=str(tmp_path / "out"))  # type: ignore[arg-type]

    assert result.exit_code == 0, result.output
    assert result.target == "zipapp"
    assert result.needs.startswith("Python >=3.")
    assert result.notes == [f"run it with: {tmp_path / 'out' / 'piper'}"]
    # pybash is not a requirement of the built CLI
    assert mock_pip.call_args.args[0][-1] == TYPER_PIN
    with zipfile.ZipFile(tmp_path / "out" / "piper") as archive:
        module = archive.read("site-packages/piper.py").decode()
    assert "class _pybash:" in module
    assert "import pybash" not in module


def test_build_command_prints_what_was_built_and_how_to_run_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("plain.yaml").write_text(PLAIN_MANIFEST)

    result = CliRunner().invoke(cli, ["build", "plain.yaml", "-t", "script", "-o", "dist"])

    assert result.exit_code == 0, result.output
    assert "+ plain built" in result.output
    assert (
        f"  dist/plain.py (single file, needs uv, or Python {MIN_PYTHON} with {TYPER_PIN} installed, " in result.output
    )
    assert "  run it with: ./dist/plain.py (or: uv run dist/plain.py)" in result.output


def test_build_command_reports_an_output_dir_that_cannot_be_created(tmp_path):
    manifest = tmp_path / "plain.yaml"
    manifest.write_text(PLAIN_MANIFEST)
    (tmp_path / "taken").write_text("a file, not a directory")

    with open(manifest) as manifest_io:
        _, result = build_cli_from_manifest(manifest_io, output_dir=str(tmp_path / "taken" / "dist"), target="script")  # type: ignore[arg-type]

    assert result.exit_code == 1
    assert "could not create the output directory" in result.output


# --- script target ------------------------------------------------------------------------------


def test_inline_metadata_is_a_pep_723_block():
    block = get_inline_metadata(["requests>=2,<3", TYPER_PIN], ">=3.11")

    assert block == (
        "# /// script\n"
        '# requires-python = ">=3.11"\n'
        "# dependencies = [\n"
        '#     "requests>=2,<3",\n'
        f'#     "{TYPER_PIN}",\n'
        "# ]\n"
        "# ///\n"
    )
    assert inline_metadata(block) == {"requires-python": ">=3.11", "dependencies": ["requests>=2,<3", TYPER_PIN]}
    assert inline_metadata(get_inline_metadata([], ">=3.11")) == {"requires-python": ">=3.11", "dependencies": []}


def test_inline_metadata_keeps_a_requirement_as_data():
    hostile = 'six"]\n# ///\nimport os; os.system("echo pwned")\n# dependencies = ["x'

    block = get_inline_metadata([hostile, 'pkg; python_version < "3.13"'], ">=3.11")

    # still one block, and each requirement is still one string
    assert block.splitlines().count("# ///") == 1
    assert len(block.splitlines()) == 7
    assert all(line.startswith("#") for line in block.splitlines())
    assert inline_metadata(block)["dependencies"] == [hostile, 'pkg; python_version < "3.13"']


def test_script_target_writes_one_executable_file(shell_manifest, tmp_path):
    output_dir = tmp_path / "nested" / "dist"
    with open(shell_manifest) as manifest_io:
        built, result = build_cli_from_manifest(manifest_io, output_dir=str(output_dir), target="script")  # type: ignore[arg-type]

    assert result.exit_code == 0, result.output
    assert built.name == "piper"
    assert result.target == "script"
    assert result.path == str(output_dir / "piper.py")
    assert result.requires_python == MIN_PYTHON
    assert [path.name for path in output_dir.iterdir()] == ["piper.py"]
    assert os.access(output_dir / "piper.py", os.X_OK)

    script = (output_dir / "piper.py").read_text()
    assert script.startswith(f"#!{SCRIPT_INTERPRETER}\n# /// script\n")
    assert inline_metadata(script) == {"requires-python": MIN_PYTHON, "dependencies": [TYPER_PIN]}
    # the generated CLI follows, readable, with the shell helper pasted in
    assert f"\n## Generated piper with cliffy {metadata.version('cliffy')}\n" in script
    assert "class _pybash:" in script
    assert "import pybash" not in script
    assert "cliffy" not in script.replace("## Generated piper with cliffy", "")
    compile(script, "piper.py", "exec")


def test_script_target_is_reproducible_and_takes_requires_and_interpreter(tmp_path):
    manifest = tmp_path / "plain.yaml"
    manifest.write_text(PLAIN_MANIFEST + "requires:\n  - tabulate>=0.9\n  - Typer>=0.24\n")

    scripts = []
    for output_dir in (tmp_path / "one", tmp_path / "two"):
        with open(manifest) as manifest_io:
            _, result = build_cli_from_manifest(
                manifest_io,  # type: ignore[arg-type]
                output_dir=str(output_dir),
                interpreter="/usr/bin/env python3",
                target="script",
            )
        assert result.exit_code == 0, result.output
        scripts.append((output_dir / "plain.py").read_text())

    assert scripts[0] == scripts[1]
    assert scripts[0].startswith("#!/usr/bin/env python3\n")
    # `requires` as written; the framework is not added a second time when the manifest pins it
    assert inline_metadata(scripts[0])["dependencies"] == ["tabulate>=0.9", "Typer>=0.24"]


def test_script_target_refuses_an_unsupported_python(tmp_path):
    manifest = tmp_path / "plain.yaml"
    manifest.write_text(PLAIN_MANIFEST)
    with open(manifest) as manifest_io:
        build_cli_from_manifest(manifest_io, output_dir=str(tmp_path), target="script")  # type: ignore[arg-type]

    script = (tmp_path / "plain.py").read_text().replace("(3, 11)", "(3, 99)")

    with pytest.raises(SystemExit) as exit_info:
        exec(compile(script, "plain.py", "exec"), {"__name__": "plain"})
    assert "plain was built for Python 3.11 or newer, but is running on Python 3." in str(exit_info.value.code)


def test_script_target_builds_a_loaded_cli_by_name(tmp_path):
    loaded = tmp_path / "loaded.py"
    loaded.write_text("## Generated loaded on 2026-01-01 00:00:00\nimport rich_click as click\n")
    cli_metadata = CLIMetadata(
        cli_name="loaded", runner_path="loaded.yaml", version="2.0", manifest="", requires=["six"], loaded="2026-01-01"
    )

    with (
        patch("cliffy.cli.get_metadata", return_value=cli_metadata),
        patch("cliffy.cli.Loader.get_cli_path", return_value=str(loaded)),
    ):
        result = CliRunner().invoke(cli, ["build", "loaded", "--target", "script", "-o", str(tmp_path / "dist")])

    assert result.exit_code == 0, result.output
    script = (tmp_path / "dist" / "loaded.py").read_text()
    # rich-click is an optional extra: it is pinned to the installed version, when it is installed
    try:
        rich_click = f"rich-click=={metadata.version('rich-click')}"
    except metadata.PackageNotFoundError:
        rich_click = "rich-click"
    assert inline_metadata(script)["dependencies"] == ["six", rich_click]


def test_script_runs_with_uv_and_with_the_current_interpreter(shell_manifest, tmp_path):
    """End to end: the script needs neither cliffy nor pybash, only what its inline metadata lists."""
    assert shutil.which("uv"), "uv has to be on PATH to test that a built script runs with `uv run`"
    result = CliRunner().invoke(cli, ["build", str(shell_manifest), "-t", "script", "-o", str(tmp_path / "dist")])
    assert result.exit_code == 0, result.output
    script = tmp_path / "dist" / "piper.py"

    workdir = tmp_path / "elsewhere"
    workdir.mkdir()
    # uv builds an environment that holds only the declared dependencies; the interpreter is fixed so
    # that the test never downloads a Python
    environment = clean_environment(tmp_path / "home", UV_PYTHON=sys.executable)
    if cache_dir := os.environ.get("UV_CACHE_DIR"):
        environment["UV_CACHE_DIR"] = cache_dir
    else:
        # the cache of the user, so that the framework is not downloaded for every test run
        environment["HOME"] = os.environ.get("HOME", str(tmp_path / "home"))

    runs = {
        "uv run": ["uv", "run", str(script)],
        "shebang": [str(script)],
        # isolated mode: the framework comes from the test environment, nothing else is on the path
        "python": [sys.executable, "-I", str(script)],
    }
    for name, command in runs.items():
        shouted = subprocess.run(
            [*command, "shout", "quiet"], capture_output=True, encoding="utf-8", cwd=workdir, env=environment
        )
        assert shouted.returncode == 0, f"{name}: {shouted.stderr}"
        assert shouted.stdout == "['QUIET', 'done']\n", name

        version = subprocess.run(
            [*command, "--version"], capture_output=True, encoding="utf-8", cwd=workdir, env=environment
        )
        assert version.stdout == "piper, 1.2.0\n", f"{name}: {version.stderr}"

    # the environment uv made for the script has the framework and neither cliffy nor pybash
    probe = tmp_path / "dist" / "probe.py"
    probe.write_text(
        script.read_text().split("## Generated")[0]
        + "import importlib.util\n"
        + "print([name for name in ('typer', 'cliffy', 'pybash') if importlib.util.find_spec(name)])\n"
    )
    probed = subprocess.run(
        ["uv", "run", str(probe)], capture_output=True, encoding="utf-8", cwd=workdir, env=environment
    )
    assert probed.stdout == "['typer']\n", probed.stderr


def test_script_from_a_blueprint_spec_runs_without_the_blueprint(tmp_path):
    result = CliRunner().invoke(
        cli, ["build", str(EXAMPLES / "blueprints" / "text-tools.yaml"), "--target", "script", "-o", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    script = tmp_path / "text-tools.py"
    assert "mcp_tools" not in script.read_text()

    workdir = tmp_path / "elsewhere"
    workdir.mkdir()
    formatted = subprocess.run(
        [sys.executable, "-I", str(script), "format-text", " hello there ", "--uppercase", "--trim"],
        capture_output=True,
        encoding="utf-8",
        cwd=workdir,
        env=clean_environment(tmp_path),
    )

    assert formatted.returncode == 0, formatted.stderr
    assert formatted.stdout == "HELLO THERE\n"


# --- native target ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cli_name", "project_name"),
    [("my-tool", "my-tool"), ("my_tool", "my-tool"), ("_private", "private"), ("a.b", "a-b"), ("___", "cli")],
)
def test_project_name_is_a_valid_distribution_name(cli_name, project_name):
    assert get_project_name(cli_name) == project_name


@pytest.mark.parametrize(
    ("version", "project_version"),
    [("1.2.0", "1.2.0"), ("v1.0", "1.0"), ("1", "1"), ("2.0-beta1", "2.0b1"), ("latest", "0"), ("", "0")],
)
def test_project_version_is_a_version_a_wheel_accepts(version, project_version):
    assert get_project_version(version) == project_version


def test_wheel_project_layout(tmp_path):
    hostile = 'six"]\n[project.scripts]\nevil = "os:system'
    project = write_wheel_project(
        tmp_path / "project", job(tmp_path, code="CODE = 1\n", requirements=[hostile, TYPER_PIN]), ">=3.12"
    )

    assert sorted(path.name for path in project.iterdir()) == ["my_tool.py", "pyproject.toml"]
    assert (project / "my_tool.py").read_text() == "CODE = 1\n"
    assert tomllib.loads((project / "pyproject.toml").read_text()) == {
        "build-system": {"requires": ["hatchling"], "build-backend": "hatchling.build"},
        "project": {
            "name": "my-tool",
            "version": "1.2.0",
            "requires-python": ">=3.12",
            # requirements stay data, whatever they contain
            "dependencies": [hostile, TYPER_PIN],
            "scripts": {"my-tool": "my_tool:cli"},
        },
        "tool": {"hatch": {"build": {"targets": {"wheel": {"include": ["my_tool.py"]}}}}},
    }


def test_pyapp_environment_embeds_a_ready_distribution(tmp_path):
    archive = tmp_path / "python.tar.gz"

    assert pyapp_environment(job(tmp_path), archive, "3.12") == {
        "PYAPP_PROJECT_NAME": "my-tool",
        "PYAPP_PROJECT_VERSION": "1.2.0",
        "PYAPP_DISTRIBUTION_PATH": str(archive),
        "PYAPP_DISTRIBUTION_PYTHON_PATH": "bin/python3",
        "PYAPP_DISTRIBUTION_SITE_PACKAGES_PATH": "lib/python3.12/site-packages",
        # nothing is downloaded or installed when the executable runs
        "PYAPP_FULL_ISOLATION": "1",
        "PYAPP_SKIP_INSTALL": "1",
        "PYAPP_EXEC_CODE": "import sys, my_tool; sys.exit(my_tool.cli(prog_name='my-tool'))",
        "PYAPP_SELF_COMMAND": "none",
    }


def test_find_python_distribution_skips_the_version_link(tmp_path):
    assert find_python_distribution(tmp_path / "missing") is None
    assert find_python_distribution(tmp_path) is None

    real = tmp_path / "cpython-3.12.1-linux-x86_64-gnu"
    (real / "bin").mkdir(parents=True)
    (real / "bin" / "python3").write_text("")
    (tmp_path / "cpython-3.12-linux-x86_64-gnu").symlink_to(real)
    (tmp_path / "notes.txt").write_text("")

    assert find_python_distribution(tmp_path) == real


@pytest.mark.parametrize(
    ("missing", "expected"),
    [
        ("cargo", ["needs `cargo`, which was not found on PATH", "https://rustup.rs", "sh.rustup.rs | sh"]),
        ("uv", ["`uv` was not found on PATH", "https://docs.astral.sh/uv/", "astral.sh/uv/install.sh | sh"]),
    ],
)
def test_native_target_says_how_to_install_a_missing_tool(tmp_path, monkeypatch, temp_dir, missing, expected):
    monkeypatch.setattr(builder.shutil, "which", lambda tool: None if tool == missing else f"/usr/bin/{tool}")
    manifest = tmp_path / "plain.yaml"
    manifest.write_text(PLAIN_MANIFEST)

    with patch("cliffy.builder.subprocess.run") as mock_run:
        result = CliRunner().invoke(cli, ["build", str(manifest), "--target", "native", "-o", str(tmp_path / "out")])

    # found before anything is downloaded or compiled
    mock_run.assert_not_called()
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
    for text in expected:
        assert text in result.output
    assert "plain build failed" in result.output
    assert "Traceback" not in result.output
    assert list((tmp_path / "out").iterdir()) == []
    assert list(temp_dir.iterdir()) == []


def test_native_target_does_not_take_an_interpreter(tmp_path):
    manifest = tmp_path / "plain.yaml"
    manifest.write_text(PLAIN_MANIFEST)

    with patch("cliffy.builder.subprocess.run") as mock_run:
        result = CliRunner().invoke(cli, ["build", str(manifest), "-t", "native", "-p", "/usr/bin/env python3.12"])

    mock_run.assert_not_called()
    assert result.exit_code == 1
    assert "A native build brings its own Python" in result.output


class FakeTools:
    """Stands in for uv and cargo: records every command and leaves the files the real tools would."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.commands: list[list[str]] = []
        self.cargo_env: dict[str, str] = {}
        self.archived: list[str] = []
        self.project: dict = {}

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        self.commands.append(command)
        step = " ".join(command[:3])
        if self.fail_on and step.startswith(self.fail_on):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr=f"noise\nerror: {self.fail_on} broke")

        if step == "uv python install":
            install_dir = Path(command[command.index("--install-dir") + 1])
            real = install_dir / "cpython-3.x.1-test"
            (real / "bin").mkdir(parents=True)
            (real / "bin" / "python3").write_text("#!python")
            (real / "lib").mkdir()
            (install_dir / "cpython-3.x-test").symlink_to(real)
        elif step == "uv build --wheel":
            self.project = tomllib.loads((Path(command[-1]) / "pyproject.toml").read_text())
            wheels = Path(command[command.index("--out-dir") + 1])
            wheels.mkdir()
            (wheels / "piper-1.2.0-py3-none-any.whl").write_text("wheel")
        elif step == "uv pip install":
            python = Path(command[command.index("--python") + 1])
            (python.parent.parent / "lib" / "installed.txt").write_text(Path(command[-1]).name)
        elif step == "cargo install pyapp":
            self.cargo_env = dict(kwargs["env"])  # type: ignore[call-overload]
            with tarfile.open(self.cargo_env["PYAPP_DISTRIBUTION_PATH"]) as archive:
                self.archived = sorted(archive.getnames())
            binary = Path(command[command.index("--root") + 1]) / "bin" / "pyapp"
            binary.parent.mkdir(parents=True)
            binary.write_text("compiled")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


@pytest.fixture
def tools_on_path(monkeypatch):
    monkeypatch.setattr(builder.shutil, "which", lambda tool: f"/usr/bin/{tool}")


def test_native_target_prepares_a_distribution_and_compiles_it_in(shell_manifest, tmp_path, monkeypatch, temp_dir):
    monkeypatch.setattr(builder.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setenv("CARGO_TARGET_DIR", str(tmp_path / "shared-target"))
    tools = FakeTools()
    python_version = f"3.{sys.version_info.minor}"

    with patch("cliffy.builder.subprocess.run", side_effect=tools), open(shell_manifest) as manifest_io:
        built, result = build_cli_from_manifest(manifest_io, output_dir=str(tmp_path / "out"), target="native")  # type: ignore[arg-type]

    assert result.exit_code == 0, result.output
    assert built.name == "piper"
    assert result.target == "native"
    assert result.path == str(tmp_path / "out" / "piper")
    assert result.needs.startswith("nothing installed, runs on ")
    assert result.notes[0] == f"run it with: {tmp_path / 'out' / 'piper'}"
    assert f"the first run unpacks its Python {python_version}" in result.notes[1]
    assert "without network access" in result.notes[1]

    artifact = tmp_path / "out" / "piper"
    assert artifact.read_text() == "compiled"
    assert os.access(artifact, os.X_OK)
    assert [path.name for path in (tmp_path / "out").iterdir()] == ["piper"]

    assert [" ".join(command[:3]) for command in tools.commands] == [
        "uv python install",
        "uv build --wheel",
        "uv pip install",
        "cargo install pyapp",
    ]
    install_python, _, pip_install, cargo = tools.commands
    # the Python the build runs on, as a standalone copy that touches nothing on the build machine
    assert install_python[3] == python_version
    assert "--no-bin" in install_python
    assert pip_install[-1].endswith("piper-1.2.0-py3-none-any.whl")
    assert cargo[3:7] == ["--version", PYAPP_VERSION, "--locked", "--force"]

    # the wheel holds the CLI with its entry point and requirements
    assert tools.project["project"]["dependencies"] == [TYPER_PIN]
    assert tools.project["project"]["scripts"] == {"piper": "piper:cli"}
    assert tools.project["project"]["requires-python"] == f">={python_version}"

    # the archive that is compiled in is the distribution with the CLI installed, python at bin/python3
    assert tools.archived == ["bin", "bin/python3", "lib", "lib/installed.txt"]
    assert tools.cargo_env["PYAPP_SKIP_INSTALL"] == "1"
    assert tools.cargo_env["PYAPP_FULL_ISOLATION"] == "1"
    assert tools.cargo_env["PYAPP_PROJECT_NAME"] == "piper"
    assert "piper.cli(prog_name='piper')" in tools.cargo_env["PYAPP_EXEC_CODE"]
    # PATH and the rest of the environment are passed on, a shared cargo target directory is not:
    # cargo would reuse the executable of the previous build
    assert tools.cargo_env["PATH"] == os.environ["PATH"]
    assert tools.cargo_env["CARGO_TARGET_DIR"] != str(tmp_path / "shared-target")
    assert tools.cargo_env["CARGO_TARGET_DIR"].startswith(str(temp_dir))

    # the work directory is gone
    assert list(temp_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("fail_on", "reason"),
    [
        ("uv python install", "could not download a standalone Python (`uv python install ...` failed):"),
        ("uv build", "could not package the CLI as a wheel (`uv build --wheel ...` failed):"),
        ("uv pip install", f"could not install {TYPER_PIN} into the standalone Python (`uv pip install ...` failed):"),
        ("cargo install", "could not compile the executable (`cargo install pyapp ...` failed):"),
    ],
)
def test_native_target_reports_the_step_that_failed(tmp_path, tools_on_path, temp_dir, fail_on, reason):
    manifest = tmp_path / "plain.yaml"
    manifest.write_text(PLAIN_MANIFEST)
    tools = FakeTools(fail_on=fail_on)

    with patch("cliffy.builder.subprocess.run", side_effect=tools):
        result = CliRunner().invoke(cli, ["build", str(manifest), "--target", "native", "-o", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert reason in result.output
    assert f"error: {fail_on} broke" in result.output
    assert "plain build failed" in result.output
    assert "Traceback" not in result.output
    # the failed step is the last one that ran, and nothing is left behind
    assert " ".join(tools.commands[-1]).startswith(fail_on)
    assert list((tmp_path / "out").iterdir()) == []
    assert list(temp_dir.iterdir()) == []


def test_native_target_reports_a_tool_that_cannot_be_started(tmp_path, tools_on_path):
    with patch("cliffy.builder.subprocess.run", side_effect=PermissionError("uv is not executable")):
        result = NativeTarget().build(job(tmp_path))

    assert result == BuildResult(
        1,
        "could not download a standalone Python: `uv` could not be started",
        result.exception,
        target="native",
    )
    assert isinstance(result.exception, PermissionError)


NATIVE_TOOLS = bool(shutil.which("cargo") and shutil.which("uv"))


@pytest.mark.skipif(
    not (NATIVE_TOOLS and os.environ.get("CLIFFY_TEST_NATIVE") == "1"),
    reason="compiles a real executable: needs cargo, uv, network access and CLIFFY_TEST_NATIVE=1",
)
def test_native_build_runs_in_an_empty_environment(shell_manifest, tmp_path, temp_dir):
    """End to end: compile a manifest into an executable and run it with an empty environment and home."""
    result = CliRunner().invoke(cli, ["build", str(shell_manifest), "--target", "native", "-o", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert "needs nothing installed" in result.output
    artifact = tmp_path / "out" / "piper"
    assert os.access(artifact, os.X_OK)
    assert list(temp_dir.iterdir()) == [] or all(path.name.startswith("uv-") for path in temp_dir.iterdir())

    home = tmp_path / "home"
    home.mkdir()
    # an empty environment and an empty home directory: the executable unpacks its own Python there
    environment = {"PATH": "/bin:/usr/bin", "HOME": str(home), "XDG_DATA_HOME": str(home / "data")}
    environment["XDG_CACHE_HOME"] = str(home / "cache")
    for _ in ("first run", "second run"):
        shouted = subprocess.run(
            [str(artifact), "shout", "quiet"], capture_output=True, encoding="utf-8", cwd=home, env=environment
        )
        assert shouted.returncode == 0, shouted.stderr
        assert shouted.stdout == "['QUIET', 'done']\n"

    usage = subprocess.run([str(artifact), "--help"], capture_output=True, encoding="utf-8", cwd=home, env=environment)
    assert "Usage: piper " in usage.stdout
    assert any(home.iterdir())
