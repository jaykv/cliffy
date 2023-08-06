## CLI to generate CLIs
import contextlib
from io import TextIOWrapper
import os
from typing import IO, Any, Optional, TextIO, Union, cast

from click.core import Context, Parameter
from click.types import _is_file_like

from .rich import click, Console
from .rich import ClickGroup  # type: ignore

from .builder import build_cli, build_cli_from_manifest, run_cli
from .helper import (
    CLIFFY_CLI_DIR,
    age_datetime,
    exit_err,
    indent_block,
    out,
    out_err,
    print_rich_table,
    write_to_file,
)
from .homer import get_clis, get_metadata, get_metadata_path, remove_metadata, save_metadata
from .loader import Loader
from .manifests import Manifest, set_manifest_version
from .transformer import Transformer

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class AliasedGroup(ClickGroup):
    def get_command(self, ctx: click.Context, cmd_name: Optional[str]) -> Optional[click.Command]:
        with contextlib.suppress(KeyError):
            cmd_name = ALIASES[cmd_name].name  # type: ignore
        return super().get_command(ctx, cmd_name or "")


class ManifestOrCLI(click.File):
    def convert(  # type: ignore[override]
        self, value: Union[str, "os.PathLike[str]", IO[Any]], param: Optional[Parameter], ctx: Optional[Context]
    ) -> Union[str, IO[Any]]:
        if _is_file_like(value):
            return value

        value = cast("Union[str, os.PathLike[str]]", value)

        if isinstance(value, os.PathLike) or value.endswith("yaml"):
            return super().convert(value, param, ctx)

        return value


@click.group(context_settings=CONTEXT_SETTINGS, cls=AliasedGroup)  # type: ignore[arg-type]
@click.version_option()
def cli() -> None:
    pass


@cli.command()  # type: ignore[arg-type]
@click.argument("manifests", type=click.File("rb"), nargs=-1)
def load(manifests: list[TextIO]) -> None:
    """Load CLI for given manifest(s)"""
    for manifest in manifests:
        T = Transformer(manifest)
        Loader.load_from_cli(T.cli)
        save_metadata(manifest.name, T.cli)
        out(f"✨ Generated {T.cli.name} CLI v{T.cli.version} ✨", fg="green")
        out("$", fg="magenta", nl=False)
        out(f" {T.cli.name} -h")


@cli.command()  # type: ignore[arg-type]
@click.argument("cli_names", type=str, nargs=-1)
def update(cli_names: list[str]) -> None:
    """Reloads CLI by name"""
    for cli_name in cli_names:
        if cli_metadata := get_metadata(cli_name):
            T = Transformer(open(cli_metadata.runner_path, "r"))
            Loader.load_from_cli(T.cli)
            save_metadata(cli_metadata.runner_path, T.cli)
            out(f"✨ Reloaded {T.cli.name} CLI v{T.cli.version} ✨", fg="green")
            out("$", fg="magenta", nl=False)
            out(f" {T.cli.name} -h")
        else:
            out_err(f"~ {cli_name} not found")


@cli.command()  # type: ignore[arg-type]
@click.argument("manifest", type=click.File("rb"))
def render(manifest: TextIO) -> None:
    """Render the CLI manifest generation as code"""
    T = Transformer(manifest)
    console = Console()
    console.print(T.cli.code, overflow="fold", emoji=False, markup=False)
    out(f"# Rendered {T.cli.name} CLI v{T.cli.version} ~", fg="green")


@cli.command("run")  # type: ignore[arg-type]
@click.argument("manifest", type=click.File("rb"))
@click.argument("cli_args", type=str, nargs=-1)
def cliffy_run(manifest: TextIO, cli_args: tuple[str]) -> None:
    """Run CLI for a manifest"""
    T = Transformer(manifest)
    run_cli(T.cli.name, T.cli.code, cli_args)


@cli.command()  # type: ignore[arg-type]
@click.argument("cli_name", type=str, default="cliffy")
@click.option("--version", "-v", type=str, show_default=True, default="v1", help="Manifest version")
@click.option("--render", is_flag=True, show_default=True, default=False, help="Render template to terminal directly")
@click.option(
    "--raw",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Raw template without boilerplate helpers and examples.",
)
def init(cli_name: str, version: str, render: bool, raw: bool) -> None:
    """Generate a CLI manifest template"""
    set_manifest_version(version)
    template = Manifest.get_raw_template(cli_name) if raw else Manifest.get_template(cli_name)

    if render:
        console = Console()
        console.print(template, overflow="fold", emoji=False, markup=False)
    else:
        try:
            write_to_file(f"{cli_name}.yaml", text=template)
        except Exception as e:
            exit_err(f"~ error writing to file: {e}")
        out(f"+ {cli_name}.yaml", fg="green")


@cli.command("list")  # type: ignore[arg-type]
def cliffy_list() -> None:
    """List all CLIs loaded"""
    cols = ["Name", "Version", "Age", "Manifest"]
    rows = [
        [metadata.cli_name, metadata.version, age_datetime(metadata.loaded), metadata.runner_path]
        for metadata in get_clis()
    ]
    print_rich_table(cols, rows, styles=["cyan", "magenta", "green", "blue"])


@cli.command()  # type: ignore[arg-type]
@click.argument("cli_names", type=str, nargs=-1)
def remove(cli_names: list[str]) -> None:
    """Remove a loaded CLI by name"""
    for cli_name in cli_names:
        if get_metadata_path(cli_name):
            remove_metadata(cli_name)
            Loader.unload_cli(cli_name)
            out(f"~ {cli_name} removed 💥", fg="green")
        else:
            out_err(f"~ {cli_name} not loaded")


@cli.command()  # type: ignore[arg-type]
@click.argument("cli_or_manifests", type=ManifestOrCLI(), nargs=-1)
@click.option("--output-dir", "-o", type=click.Path(file_okay=False, dir_okay=True, writable=True), help="Output dir")
@click.option(
    "--python",
    "-p",
    type=str,
    help="Python interpreter to set as the zipapp shebang. This gets added after the #! ",
    default="/usr/bin/env python3",
    show_default=True,
)
def build(cli_or_manifests: list[Union[TextIOWrapper, str]], output_dir: str, python: str) -> None:
    """Build a CLI manifest or a loaded CLI into a zipapp"""
    for cli_or_manifest in cli_or_manifests:
        if isinstance(cli_or_manifest, TextIOWrapper):
            cli, result = build_cli_from_manifest(cli_or_manifest, output_dir=output_dir, interpreter=python)
            cli_name = cli.name
        else:
            cli_name = cast("str", cli_or_manifest)
            if not (metadata := get_metadata(cli_name)):
                out_err(f"~ {cli_name} not loaded")
                continue

            result = build_cli(
                cli_name,
                script_path=f"{CLIFFY_CLI_DIR}/{cli_name}.py",
                deps=metadata.requires,
                output_dir=output_dir,
                interpreter=python,
            )

        if result.exit_code != 0:
            out(result.stdout)
            out_err(f"~ {cli_name} build failed")
            continue

        out(f"+ {cli_name} built 📦", fg="green")


@cli.command()  # type: ignore[arg-type]
@click.argument("cli_name", type=str)
def info(cli_name: str):
    """Display CLI info"""
    metadata = get_metadata(cli_name) or exit_err(f"~ {cli_name} not loaded")
    out(f"{click.style('name:', fg='blue')} {metadata.cli_name}")
    out(f"{click.style('version:', fg='blue')} {metadata.version}")
    out(f"{click.style('requires:', fg='blue')} {metadata.requires}")
    out(f"{click.style('age:', fg='blue')} {age_datetime(metadata.loaded)} ({metadata.loaded.ctime()})")
    out(f"{click.style('manifest:', fg='blue')}\n{indent_block(metadata.manifest, spaces=2)}")


ALIASES = {"add": load, "rm": remove, "ls": cliffy_list, "reload": update}
