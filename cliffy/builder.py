import os
import sys
from io import TextIOWrapper
from pathlib import Path
from shutil import copy
from tempfile import NamedTemporaryFile, TemporaryDirectory

from click.testing import CliRunner, Result
from shiv import cli as shiv_cli
from shiv import pip

from cliffy.commander import CLI
from cliffy.helper import TEMP_FILES, delete_temp_files, import_module_from_path
from cliffy.transformer import Transformer


def build_cli_from_manifest(
    manifestIO: TextIOWrapper, output_dir: str | None = None, interpreter: str = "/usr/bin/env python3"
) -> tuple[CLI, Result]:
    T = Transformer(manifestIO, validate_requires=False)
    with NamedTemporaryFile(mode="w", prefix=f"{T.cli.name}_", suffix=".py", delete=False, encoding="utf-8") as script:
        TEMP_FILES.append(script)
        try:
            script.write(T.cli.code)
            script.flush()
            result = build_cli(
                T.cli.name,
                script_path=script.name,
                deps=T.cli.requires,
                output_dir=output_dir,
                interpreter=interpreter,
            )
        finally:
            delete_temp_files()

    return T.cli, result


def build_cli(
    cli_name: str,
    script_path: str,
    deps: list[str] | None = None,
    output_dir: str | None = None,
    interpreter: str = "/usr/bin/env python3",
) -> Result:
    if deps is None:
        deps = []

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with TemporaryDirectory() as tdist:
        copy(script_path, os.path.join(tdist, f"{cli_name}.py"))
        pip_deps = [*get_framework_requirements(script_path), *deps]

        pip.install(["--target", tdist, *pip_deps])

        runner = CliRunner()
        output_file = os.path.join(output_dir, f"{cli_name}") if output_dir else cli_name
        return runner.invoke(
            shiv_cli.main,  # type: ignore
            ["--site-packages", tdist, "--compressed", "-e", f"{cli_name}.cli", "-o", output_file, "-p", interpreter],
        )


def get_framework_requirements(script_path: str) -> list[str]:
    """Packages the generated CLI imports no matter what the manifest requires.

    Read from the generated code, because a loaded CLI is built from its script alone.
    """
    code = Path(script_path).read_text(encoding="utf-8")
    return ["rich-click"] if "import rich_click as click" in code else ["typer"]


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
