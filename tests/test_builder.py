import glob
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from importlib import metadata
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cliffy.builder import (
    build_cli,
    build_cli_from_manifest,
    get_build_requirements,
    get_python_guard,
    get_requires_python,
    run_cli,
)
from cliffy.cli import cli
from cliffy.helper import TEMP_FILES

EXAMPLES = Path(__file__).parent.parent / "examples" / "blueprints"
TYPER_CODE = "## Generated demo on 2026-01-01 00:00:00\nfrom typing import Optional, Any\nimport typer\n"
CLICK_CODE = "## Generated demo on 2026-01-01 00:00:00\nimport rich_click as click\n"
TYPER_MANIFEST = "name: buildme\nversion: '1'\ncommands:\n  a: print(1)\n"
CLICK_MANIFEST = "name: buildme\nversion: '1'\nuse_click: true\ncommands:\n  a: print(1)\n"


@pytest.fixture
def temp_dir(monkeypatch, tmp_path):
    """Makes the tempfile module create its files in an empty directory"""
    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))
    return temp_dir


def skip_pip():
    """Patches the pip run of a build: the zipapp is then built from the script alone"""
    pip_run = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    return patch("cliffy.builder.subprocess.run", return_value=pip_run)


def pip_requirements(mock_pip_run: MagicMock) -> list[str]:
    """Requirements a patched pip run was asked to install into the staging directory"""
    pip_args = mock_pip_run.call_args.args[0]
    assert pip_args[:3] == [sys.executable, "-m", "pip"]
    assert "install" in pip_args
    return pip_args[pip_args.index("--target") + 2 :]


def run_artifact(
    artifact: Path, args: list[str], workdir: Path, stdin: str | None = None
) -> subprocess.CompletedProcess:
    """Run a built CLI the way a user would on another machine: other directory, no cliffy, no blueprint."""
    environment = {
        "PATH": os.environ.get("PATH", ""),
        # where the zipapp unpacks its bundled packages on first run
        "SHIV_ROOT": str(workdir / "shiv-root"),
        "PYTHONNOUSERSITE": "1",
    }
    return subprocess.run(
        # -I: isolated mode, so nothing from the test environment can leak into the artifact
        [sys.executable, "-I", str(artifact), *args],
        capture_output=True,
        encoding="utf-8",
        cwd=workdir,
        env=environment,
        input=stdin,
    )


def pinned(package: str) -> str:
    """The requirement the builder adds for a framework: pinned to the installed version, when it is installed.

    rich-click is an optional extra, so in an install without extras it is requested without a pin.
    """
    try:
        return f"{package}=={metadata.version(package)}"
    except metadata.PackageNotFoundError:
        return package


def test_build_requirements_pin_the_framework():
    requirements = get_build_requirements(TYPER_CODE, ["requests>=2", "six"])

    assert requirements[:2] == ["requests>=2", "six"]
    assert len(requirements) == 3
    assert requirements[2].startswith("typer==")

    click_requirements = get_build_requirements(CLICK_CODE, [])
    assert click_requirements == [pinned("rich-click")]


def test_build_requirements_keep_the_users_framework_pin():
    assert get_build_requirements(TYPER_CODE, ["Typer>=0.24"]) == ["Typer>=0.24"]
    # an unparsable requirement is left for pip to report
    assert get_build_requirements("print(1)\n", ["not a requirement!"]) == ["not a requirement!"]


def write_dist(site_packages: Path, name: str, requires_python: str | None) -> None:
    dist_info = site_packages / f"{name}-1.0.dist-info"
    dist_info.mkdir(parents=True)
    line = f"Requires-Python: {requires_python}\n" if requires_python else ""
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n{line}\nRequires-Python: >=9\n"
    )


def test_requires_python_is_the_highest_floor_of_pure_packages(tmp_path):
    write_dist(tmp_path, "old", ">=3.6")
    write_dist(tmp_path, "new", ">=3.9,<4")
    write_dist(tmp_path, "any", None)

    assert get_requires_python(tmp_path) == ">=3.9"


def test_requires_python_is_exact_with_compiled_extensions(tmp_path):
    write_dist(tmp_path, "fast", ">=3.8")
    (tmp_path / "fast.cpython-311-darwin.so").write_bytes(b"")

    assert get_requires_python(tmp_path) == f"==3.{sys.version_info.minor}.*"

    # abi3 extensions work across Python versions
    (tmp_path / "fast.cpython-311-darwin.so").rename(tmp_path / "fast.abi3.so")
    assert get_requires_python(tmp_path) == ">=3.8"


@pytest.mark.parametrize(
    ("requires_python", "passes", "expected"),
    [
        (">=3.8", True, ""),
        (f"==3.{sys.version_info.minor}.*", True, ""),
        (">=3.99", False, "demo was built for Python 3.99 or newer, but is running on Python 3."),
        ("==3.1.*", False, "demo was built for Python 3.1, but is running on Python 3."),
    ],
)
def test_python_guard(requires_python, passes, expected):
    guard = get_python_guard("demo", requires_python)

    if passes:
        exec(guard, {})
        return

    with pytest.raises(SystemExit) as exit_info:
        exec(guard, {})
    assert expected in str(exit_info.value.code)


def test_build_reports_missing_script(tmp_path):
    result = build_cli("demo", script_path=str(tmp_path / "missing.py"), output_dir=str(tmp_path))

    assert result.exit_code == 1
    assert "could not read the generated CLI" in result.output
    assert result.path is None


def test_build_reports_dependency_that_cannot_be_installed(tmp_path):
    script = tmp_path / "demo.py"
    script.write_text("print(1)\n")

    result = build_cli("demo", script_path=str(script), deps=["not a requirement!"], output_dir=str(tmp_path / "out"))

    assert result.exit_code == 1
    assert "could not install not a requirement!" in result.output
    assert not (tmp_path / "out" / "demo").exists()


def test_build_command_shows_the_reason_of_a_failed_build(tmp_path):
    manifest = tmp_path / "broken.yaml"
    manifest.write_text(
        "name: bp-broken-build\nversion: 1.0.0\nrequires: ['not a requirement!']\ncommands:\n  a: print(1)\n"
    )

    result = CliRunner().invoke(cli, ["build", str(manifest), "-o", str(tmp_path / "out")])

    # a failed build is reported with the exit code as well
    assert result.exit_code == 1
    assert "could not install" in result.output
    assert "bp-broken-build build failed" in result.output


def test_build_blueprint_spec_into_a_single_self_contained_file(tmp_path):
    """End to end: a YAML file in a custom spec becomes one executable that needs neither cliffy nor the blueprint."""
    output_dir = tmp_path / "dist"
    result = CliRunner().invoke(cli, ["build", str(EXAMPLES / "text-tools.yaml"), "-o", str(output_dir)])

    assert result.exit_code == 0, result.output
    assert "text-tools built" in result.output
    assert "single file, needs Python >=3." in result.output

    assert [path.name for path in output_dir.iterdir()] == ["text-tools"]
    artifact = output_dir / "text-tools"
    assert os.access(artifact, os.X_OK)
    assert artifact.read_bytes().startswith(b"#!/usr/bin/env python3\n")

    with zipfile.ZipFile(artifact) as archive:
        names = archive.namelist()
    assert "site-packages/text_tools.py" in names
    assert any(name.startswith("site-packages/typer/") for name in names)
    # the blueprint is applied at build time, neither it nor cliffy is shipped
    assert not any("cliffy" in name or "mcp_tools" in name or "pydantic" in name for name in names)

    workdir = tmp_path / "elsewhere"
    workdir.mkdir()

    formatted = run_artifact(artifact, ["format-text", " hello there ", "--uppercase", "--trim"], workdir)
    assert formatted.returncode == 0, formatted.stderr
    assert formatted.stdout == "HELLO THERE\n"

    version = run_artifact(artifact, ["--version"], workdir)
    assert version.stdout == "text-tools, 0.1.0\n"

    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "count_words", "arguments": {"text": "a b"}},
        },
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope", "arguments": {}}},
    ]
    served = run_artifact(
        artifact, ["serve"], workdir, stdin="".join(json.dumps(request) + "\n" for request in requests)
    )
    assert served.returncode == 0, served.stderr
    replies = [json.loads(line) for line in served.stdout.splitlines()]

    assert [reply["id"] for reply in replies] == [1, 2, 3, 4]
    assert replies[0]["result"]["serverInfo"] == {"name": "text-tools", "version": "0.1.0"}
    assert [tool["name"] for tool in replies[1]["result"]["tools"]] == [
        "format_text",
        "count_words",
        "extract_entities",
        "repeat",
    ]
    assert json.loads(replies[2]["result"]["content"][0]["text"]) == {"words": 2}
    assert replies[2]["result"]["isError"] is False
    assert replies[3]["result"]["isError"] is True


def test_build_is_reproducible_and_takes_blueprint_and_interpreter_options(tmp_path):
    spec = tmp_path / "jobs.yaml"
    spec.write_text("name: bp-jobs\ntasks:\n  greet: echo hello from a build\n")
    blueprint = str(EXAMPLES / "tasks.py")
    interpreter = "/usr/bin/env -S python3 -I"

    builds = []
    for output_dir in (tmp_path / "one", tmp_path / "two"):
        with open(spec) as spec_io:
            built_cli, result = build_cli_from_manifest(
                spec_io, output_dir=str(output_dir), interpreter=interpreter, blueprint=blueprint
            )
        assert result.exit_code == 0, result.output
        assert built_cli.name == "bp-jobs"
        assert result.path == str(output_dir / "bp-jobs")
        assert result.requires_python is not None and result.requires_python.startswith(">=3.")
        builds.append((output_dir / "bp-jobs").read_bytes())

    assert builds[0] == builds[1]
    assert builds[0].startswith(f"#!{interpreter}\n".encode())

    ran = run_artifact(tmp_path / "one" / "bp-jobs", ["greet"], tmp_path)
    assert ran.returncode == 0, ran.stderr
    assert "hello from a build" in ran.stdout


def test_run_cli_removes_temp_file_when_import_fails(temp_dir):
    with pytest.raises(ImportError):
        run_cli("broken", "import no_such_module_for_cliffy", ())

    assert glob.glob(f"{temp_dir}/broken_*") == []
    assert TEMP_FILES == []


def test_build_removes_temp_file_when_build_fails(temp_dir, tmp_path):
    manifest_path = tmp_path / "buildme.yaml"
    manifest_path.write_text(TYPER_MANIFEST)

    with (
        patch("cliffy.builder.build_cli", side_effect=RuntimeError("pip failed")),
        open(manifest_path) as manifest,
        pytest.raises(RuntimeError),
    ):
        build_cli_from_manifest(manifest)  # type: ignore[arg-type]

    assert glob.glob(f"{temp_dir}/buildme_*") == []
    # the script is written into a temporary directory: neither it nor the directory is left behind
    assert list(temp_dir.iterdir()) == []
    assert TEMP_FILES == []


@pytest.mark.parametrize(
    "manifest, framework",
    [(TYPER_MANIFEST, "typer"), (CLICK_MANIFEST, "rich-click")],
    ids=["typer", "click"],
)
def test_build_installs_the_framework_the_cli_imports(tmp_path, manifest, framework):
    manifest_path = tmp_path / "buildme.yaml"
    manifest_path.write_text(manifest)
    output_dir = tmp_path / "out"

    # pip is not run: the zipapp is built from the script alone
    with skip_pip() as mock_pip_run, open(manifest_path) as manifest_io:
        cli, result = build_cli_from_manifest(manifest_io, output_dir=str(output_dir))  # type: ignore[arg-type]

    assert result.exit_code == 0, result.output
    assert os.path.exists(output_dir / cli.name)
    pip_args = mock_pip_run.call_args.args[0]
    assert pip_args[pip_args.index("--target") + 1] != str(output_dir)
    # only the framework of the generated code, pinned to the version installed next to cliffy
    assert pip_requirements(mock_pip_run) == [pinned(framework)]


def test_framework_requirements_and_deps_are_combined(tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text("import rich_click as click\n")

    with skip_pip() as mock_pip_run:
        build_cli("script", str(script_path), deps=["requests>=2,<3"], output_dir=str(tmp_path / "out"))

    assert pip_requirements(mock_pip_run) == ["requests>=2,<3", pinned("rich-click")]


def test_build_creates_nested_output_dir(tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text("import typer\n")
    output_dir = tmp_path / "dist" / "bin"

    with skip_pip():
        result = build_cli("script", str(script_path), output_dir=str(output_dir))

    assert result.exit_code == 0, result.output
    assert (output_dir / "script").exists()
