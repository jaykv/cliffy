from io import TextIOWrapper
import os
import sys
from pathlib import Path
from shutil import copy
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Optional

from click.testing import CliRunner, Result
from shiv import cli as shiv_cli
from shiv import pip

from cliffy.helper import TEMP_FILES, delete_temp_files, import_module_from_path

from cliffy.transformer import Transformer

from cliffy.commander import CLI


def build_cli_from_manifest(
    manifestIO: TextIOWrapper, output_dir: Optional[str] = None, interpreter: str = "/usr/bin/env python3"
) -> tuple[CLI, Result]:
    T = Transformer(manifestIO, validate_requires=False)
    with NamedTemporaryFile(mode="w", prefix=f"{T.cli.name}_", suffix=".py", delete=False) as script:
        script.write(T.cli.code)
        script.flush()
        result = build_cli(
            T.cli.name, script_path=script.name, deps=T.cli.requires, output_dir=output_dir, interpreter=interpreter
        )
        TEMP_FILES.append(script)

    delete_temp_files()
    return T.cli, result


def build_cli(
    cli_name: str,
    script_path: str,
    deps: Optional[list[str]] = None,
    output_dir: Optional[str] = None,
    interpreter: str = "/usr/bin/env python3",
) -> Result:
    if deps is None:
        deps = []

    if output_dir and not Path(output_dir).exists():
        os.mkdir(output_dir)

    with TemporaryDirectory() as tdist:
        copy(script_path, os.path.join(tdist, f"{cli_name}.py"))
        pip_deps = ["typer"] + deps

        pip.install(["--target", tdist] + pip_deps)

        runner = CliRunner()
        output_file = os.path.join(output_dir, f"{cli_name}") if output_dir else cli_name
        return runner.invoke(
            shiv_cli.main,  # type: ignore
            ["--site-packages", tdist, "--compressed", "-e", f"{cli_name}.cli", "-o", output_file, "-p", interpreter],
        )


def run_cli(cli_name: str, script_code: str, args: tuple) -> None:
    with NamedTemporaryFile(mode="w", prefix=f"{cli_name}_", suffix=".py", delete=False) as runner_file:
        runner_file.write(script_code)
        runner_file.flush()
        module = import_module_from_path(runner_file.name)
        TEMP_FILES.append(runner_file)

    delete_temp_files()
    runner_argvs = [runner_file.name] + list(args)
    sys.argv = runner_argvs
    module.cli()
