import contextlib
import io
import re
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from io import TextIOWrapper
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name
from shiv import cli as shiv_cli

from cliffy.commander import CLI
from cliffy.helper import TEMP_FILES, delete_temp_files, import_module_from_path
from cliffy.transformer import Transformer

DEFAULT_INTERPRETER = "/usr/bin/env python3"
# Package that provides the framework a generated CLI imports
FRAMEWORK_PACKAGES = {"typer": "typer", "rich_click": "rich-click", "click": "click"}
GENERATED_HEADER = re.compile(r"\A## Generated (\S+) on .*\n")


@dataclass
class BuildResult:
    """Outcome of a build. `output` holds the reason when `exit_code` is not 0."""

    exit_code: int
    output: str = ""
    exception: BaseException | None = None
    path: str | None = None
    requires_python: str | None = None


def build_cli_from_manifest(
    manifestIO: TextIOWrapper,
    output_dir: str | None = None,
    interpreter: str = DEFAULT_INTERPRETER,
    blueprint: str | None = None,
) -> tuple[CLI, BuildResult]:
    """Build a manifest, or a YAML file written in a blueprint's spec, into a single-file executable.

    The blueprint is applied here, at build time. The executable holds the generated CLI and its
    dependencies and needs neither the blueprint nor the YAML file to run.
    """
    T = Transformer(manifestIO, validate_requires=False, blueprint=blueprint)
    # the directory is removed with the script in it, also when the build fails
    with TemporaryDirectory() as script_dir:
        script_path = Path(script_dir) / f"{T.cli.name}.py"
        script_path.write_text(T.cli.code, encoding="utf-8")
        result = build_cli(
            T.cli.name,
            script_path=str(script_path),
            deps=T.cli.requires,
            output_dir=output_dir,
            interpreter=interpreter,
        )

    return T.cli, result


def build_cli(
    cli_name: str,
    script_path: str,
    deps: list[str] | None = None,
    output_dir: str | None = None,
    interpreter: str = DEFAULT_INTERPRETER,
) -> BuildResult:
    """Bundle a generated CLI script and its dependencies into one executable zipapp named `cli_name`.

    Dependencies are installed with the pip of the running interpreter. The framework the CLI imports
    (typer or rich-click) is pinned to the version installed next to cliffy unless `deps` names it, and
    the archive is written with fixed timestamps, so equal inputs give an identical file.
    """
    try:
        code = Path(script_path).read_text(encoding="utf-8")
    except OSError as e:
        return BuildResult(1, f"could not read the generated CLI at {script_path}", e)

    module_name = cli_name.replace("-", "_")
    output_path = Path(output_dir or ".") / cli_name
    requirements = get_build_requirements(code, deps or [])

    with TemporaryDirectory() as staging:
        pip_install = [sys.executable, "-m", "pip", "--disable-pip-version-check", "install", "--no-compile"]
        pip = subprocess.run([*pip_install, "--target", staging, *requirements], capture_output=True, text=True)
        if pip.returncode != 0:
            reason = (pip.stderr.strip() or pip.stdout.strip()).splitlines()[-15:]
            return BuildResult(1, f"could not install {', '.join(requirements)}:\n" + "\n".join(reason))

        requires_python = get_requires_python(Path(staging))
        code = GENERATED_HEADER.sub(r"## Generated \1 with cliffy\n", code)
        Path(staging, f"{module_name}.py").write_text(
            get_python_guard(cli_name, requires_python) + code, encoding="utf-8"
        )

        shiv_args = ["--site-packages", staging, "--compressed", "--reproducible"]
        shiv_args += ["-e", f"{module_name}.cli", "-o", str(output_path), "-p", interpreter]
        shiv_output = io.StringIO()
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with contextlib.redirect_stdout(shiv_output), contextlib.redirect_stderr(shiv_output):
                shiv_cli.main.main(args=shiv_args, standalone_mode=False)
        except (Exception, SystemExit) as e:
            return BuildResult(1, f"{shiv_output.getvalue()}could not write {output_path}", e)

    return BuildResult(0, path=str(output_path), requires_python=requires_python)


def get_build_requirements(code: str, deps: list[str]) -> list[str]:
    """Requirements to bundle: the manifest's `requires` plus the framework the generated code imports.

    The framework is read from the generated code, because a loaded CLI is built from its script alone.
    """
    named = set()
    for dep in deps:
        with contextlib.suppress(InvalidRequirement):
            named.add(canonicalize_name(Requirement(dep).name))

    requirements = list(deps)
    for module, package in FRAMEWORK_PACKAGES.items():
        if package in named or not re.search(rf"^\s*(import|from) {module}\b", code, flags=re.MULTILINE):
            continue
        try:
            requirements.append(f"{package}=={metadata.version(package)}")
        except metadata.PackageNotFoundError:
            requirements.append(package)
    return requirements


def get_requires_python(site_packages: Path) -> str:
    """Python versions the bundled packages can run on, as `>=3.X` or `==3.X.*`.

    A bundle with compiled extension modules only runs on the Python minor version it was built with.
    Otherwise the lowest version accepted by every bundled package is the floor.
    """
    compiled = [
        path
        for pattern in ("*.so", "*.pyd", "*.dylib")
        for path in site_packages.rglob(pattern)
        if ".abi3." not in path.name
    ]
    if compiled:
        return f"==3.{sys.version_info.minor}.*"

    specifiers = []
    for metadata_file in site_packages.glob("*.dist-info/METADATA"):
        for line in metadata_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                break
            if line.lower().startswith("requires-python:"):
                with contextlib.suppress(InvalidSpecifier):
                    specifiers.append(SpecifierSet(line.split(":", 1)[1].strip()))

    for minor in range(sys.version_info.minor):
        if all(specifier.contains(f"3.{minor}.99") for specifier in specifiers):
            return f">=3.{minor}"
    return f">=3.{sys.version_info.minor}"


def get_python_guard(cli_name: str, requires_python: str) -> str:
    """Code put at the top of the bundled CLI so that an unsupported interpreter gets a readable error."""
    exact = requires_python.startswith("==")
    minor = int(requires_python.removesuffix(".*").split(".")[1])
    wanted = f"Python 3.{minor}" if exact else f"Python 3.{minor} or newer"
    message = f"{cli_name} was built for {wanted}, but is running on Python "
    return f"""import sys

if not sys.version_info[:2] {"==" if exact else ">="} (3, {minor}):
    raise SystemExit({message!r} + sys.version.split()[0] + ". Run it with a matching interpreter.")

"""


def run_cli(cli_name: str, script_code: str, args: tuple) -> None:
    with NamedTemporaryFile(
        mode="w", prefix=f"{cli_name}_", suffix=".py", delete=False, encoding="utf-8"
    ) as runner_file:
        TEMP_FILES.append(runner_file)
        try:
            runner_file.write(script_code)
            runner_file.flush()
            module = import_module_from_path(runner_file.name)
        finally:
            # also when the generated code fails to import
            delete_temp_files()

    runner_argvs = [runner_file.name, *list(args)]
    sys.argv = runner_argvs
    module.cli()
