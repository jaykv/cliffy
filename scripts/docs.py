"""Generate and check the documentation pages that are derived from code.

Three reference pages are generated so that they cannot drift from the code:

* ``docs/reference/cli.md``       from the Click command tree in ``cliffy.cli``
* ``docs/reference/manifest.md``  from the pydantic models in ``cliffy.manifest``
* ``docs/reference/examples.md``  from the manifests in ``examples/``

Usage (from the repository root, with all extras installed)::

    uv run python scripts/docs.py generate   # rewrite the generated pages
    uv run python scripts/docs.py check      # fail if they are stale, then test every docs snippet

``check`` also loads every manifest in ``docs/snippets``, compiles the code cliffy generates for it and
runs its ``tests`` section with ``cli test``, so the manifests shown in the guides are known to work.
"""

from __future__ import annotations

import argparse
import difflib
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import typing
from pathlib import Path
from typing import Any

import click
import yaml
from pydantic import BaseModel, RootModel
from pydantic.fields import FieldInfo

from cliffy import manifest as manifest_module
from cliffy.cli import ALIASES
from cliffy.cli import cli as cliffy_cli
from cliffy.manifest import (
    CLIManifest,
    Command,
    CommandConfig,
    CommandParam,
    CommandTemplate,
    Example,
    IncludeManifest,
)
from cliffy.transformer import Transformer

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SNIPPETS = DOCS / "snippets"
EXAMPLES = ROOT / "examples"

HEADER = """<!--
  GENERATED FILE - do not edit by hand.
  Source: scripts/docs.py. Regenerate with `make docs-generate`.
-->
"""


# --------------------------------------------------------------------------------------------------
# CLI reference
# --------------------------------------------------------------------------------------------------

# Click arguments carry no help text, so each one is described here. Generation fails when a command
# gains an argument that is missing from this table.
ARGUMENT_HELP: dict[tuple[str, str], str] = {
    ("load", "manifests"): "One or more manifest files to load.",
    ("update", "cli_names"): "Names of loaded CLIs to regenerate from their manifests.",
    ("render", "manifest"): "Manifest file to render.",
    ("run", "manifest"): "Manifest file to run.",
    ("run", "cli_args"): "Arguments passed to the generated CLI. Put `--` first when they include options.",
    ("init", "cli_name"): "Name of the CLI. The manifest is written to `<cli_name>.yaml`.",
    ("remove", "cli_names"): "Names of loaded CLIs to remove.",
    ("build", "cli_or_manifests"): "Manifest files (paths ending in `yaml`) or names of loaded CLIs.",
    ("info", "cli_name"): "Name of a loaded CLI.",
    ("dev", "manifest"): "Manifest file to watch.",
    ("dev", "run_cli_args"): "Arguments for the generated CLI when `--run-cli` is set.",
    ("test", "manifest"): "Manifest file whose `tests` section should run.",
    ("validate", "manifest"): "Manifest file to validate.",
    ("docs", "cli_or_manifest"): "Manifest file (a path ending in `yaml`).",
    ("ai generate", "cli_name"): "Name of the CLI. The manifest is written to `<cli_name>.yaml`.",
    ("ai generate", "description"): "Plain-language description of the CLI you want.",
    ("ai ask", "prompt"): "Your question.",
}

# Options whose declaration has no help text.
OPTION_HELP: dict[tuple[str, str], str] = {
    ("docs", "format"): "Output format.",
}

# Hand-written notes and examples shown under each command. Every statement here was checked by
# running the command.
COMMAND_NOTES: dict[str, str] = {
    "load": """
Loading does three things:

1. generates the CLI code and writes it to `cliffy/clis/<name>.py` inside the installed cliffy package,
2. writes a launcher script called `<name>` into the `bin` directory of the active Python environment,
3. records the manifest path and contents so that `cli list`, `cli info` and `cli update` can find it.

The CLI is therefore available wherever that environment is active. Packages listed under `requires`
must already be installed, otherwise loading stops with `missing requirement`.

```console
$ cli load hello.yaml
✨ Generated hello CLI v0.1.0 ✨
$ hello -h
```

See [Hot-reload dev loop](../guides/dev-loop.md).
""",
    "update": """
`update` re-reads the manifest from the path recorded by `cli load`, so it only works while the manifest
is still at that location.

```console
$ cli update hello
✨ Reloaded hello CLI v0.1.0 ✨
$ hello -h
```
""",
    "render": """
Prints the Python module cliffy generates, without loading or running it. Use it to see exactly how
params, shell lines and templates are translated.

```console
$ cli render hello.yaml
```
""",
    "run": """
Generates the CLI in a temporary file and runs it once, without loading it. Options meant for your
CLI must come after `--`, otherwise `cli run` tries to parse them itself:

```console
$ cli run hello.yaml greet Ada
Hello, Ada!
$ cli run hello.yaml -- greet Ada --shout
HELLO, ADA!
$ cli run hello.yaml -- --help
```

Help output shows the temporary file name instead of the CLI name.
""",
    "init": """
```console
$ cli init mycli --raw
+ mycli.yaml
```

`--raw` writes a skeleton with every top-level key and no content, which is the recommended starting
point. Without `--raw` the manifest is a commented tour of the format; see
[Known issues](../project/known-issues.md) before using that one as a starting point.

`--json-schema` also writes `cliffy_schema.json` and adds a `# yaml-language-server` comment that points
at it. See [Editor setup](../guides/editor-setup.md).
""",
    "list": """
```console
$ cli list
┏━━━━━━━┳━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name  ┃ Version ┃ Age ┃ Manifest                ┃
┡━━━━━━━╇━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ hello │ 0.1.0   │ 5s  │ /home/ada/hello.yaml    │
└───────┴─────────┴─────┴─────────────────────────┘
```
""",
    "remove": """
Deletes the launcher script, the generated module and the stored metadata.

```console
$ cli remove hello
~ hello removed 💥
```
""",
    "remove-all": "",
    "build": """
Builds a single-file [zipapp](https://docs.python.org/3/library/zipapp.html) with
[shiv](https://shiv.readthedocs.io/). The file contains the generated CLI, Typer and every package
listed under `requires`. Without `--output-dir` it is written to the current directory.

```console
$ cli build hello.yaml -o dist
+ hello built 📦
$ ./dist/hello greet Ada
Hello, Ada!
```

See [Building executables](../guides/building.md).
""",
    "info": """
Prints the name, version, requirements, age and stored manifest of a loaded CLI.
""",
    "dev": """
Nothing is loaded when the command starts. The CLI is loaded the first time the file changes and
again on every later change. Stop with Ctrl+C.

With `--run-cli`, the remaining arguments are passed to the freshly generated CLI after each reload.
Put `--` before them when they include options.

See [Hot-reload dev loop](../guides/dev-loop.md).
""",
    "test": """
Runs the `tests` section of a manifest and prints each command, its output and the result. The exit
code is `1` when every test fails or when the manifest has no tests, and `0` otherwise, so check the
last line of the output (`All tests passed!`) in scripts.

See [Testing manifests](../guides/testing.md).
""",
    "validate": """
Checks that the file is valid YAML, matches the manifest schema and that its `requires` are installed.
It does not check that the generated Python is valid; run `cli test` or `cli run` for that.

```console
$ cli validate hello.yaml
Manifest hello.yaml is valid
```
""",
    "docs": """
Writes `<name>.md`, `<name>.rst` or `<name>.html` to the output directory, or to the current directory
when `--output-dir` is not given. The output directory must exist.

See [Generating docs](../guides/generating-docs.md).
""",
    "ai": """
Only available when the `ai` extra is installed (`pip install "cliffy[ai]"`). Both commands send the
manifest JSON schema to the model as part of the prompt and print token usage when they finish.

Model names use the pydantic-ai `provider:model` form, for example `openai:gpt-4o` or
`google:gemini-2.5-flash`, and the API key of that provider must be set in the environment.
""",
    "ai generate": """
`--preview` prints the prompt and exits without calling a model.
""",
    "ai ask": """
`--preview` prints the prompt and exits without calling a model.
""",
}


def _load_cli() -> click.Group:
    """Return the ``cli`` group with the ``ai`` commands attached, as ``cliffy.run`` does."""
    try:
        from cliffy.ai import ai
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise SystemExit(f"The reference is generated with all extras installed (uv sync --all-extras): {e}") from e

    if "ai" not in cliffy_cli.commands:
        cliffy_cli.add_command(ai)
    return cliffy_cli


def _escape_cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _param_type(param: click.Parameter) -> str:
    if isinstance(param, click.Option) and param.is_flag:
        return "flag"
    if isinstance(param.type, click.Choice):
        return " \\| ".join(f"`{choice}`" for choice in param.type.choices)
    names = {"text": "text", "integer": "integer", "filename": "file", "directory": "directory", "path": "path"}
    return names.get(param.type.name, param.type.name)


def _param_default(param: click.Parameter, ctx: click.Context) -> str:
    if isinstance(param, click.Option) and param.is_flag:
        return ""
    default = param.get_default(ctx)
    if default is None or default == () or type(default).__name__ in {"Sentinel", "_Unset"}:
        return ""
    if isinstance(default, Path):
        return "`.`" if default == Path() else f"`{default}`"
    return f"`{default}`"


def _render_command(path: str, command: click.Command, parent: click.Context, level: int) -> list[str]:
    ctx = click.Context(command, info_name=path.split()[-1], parent=parent)
    lines = [f"{'#' * level} `cli {path}`", ""]

    help_text = inspect.cleandoc(command.help or "")
    if help_text:
        lines += [help_text, ""]

    usage = " ".join(["cli", path, *command.collect_usage_pieces(ctx)])
    lines += ["```text", usage, "```", ""]

    aliases = sorted(alias for alias, target in ALIASES.items() if target == path)
    if aliases:
        label = "Alias" if len(aliases) == 1 else "Aliases"
        lines += [f"{label}: " + ", ".join(f"`cli {alias}`" for alias in aliases), ""]

    rows = []
    for param in command.get_params(ctx):
        if isinstance(param, click.Argument):
            assert param.name is not None
            key = (path, param.name)
            if key not in ARGUMENT_HELP:
                raise SystemExit(f"scripts/docs.py: add a description for argument {key} to ARGUMENT_HELP")
            name = f"`{param.make_metavar(ctx)}`"
            required = "yes" if param.required else "no"
            rows.append((name, _param_type(param), required, _param_default(param, ctx), ARGUMENT_HELP[key]))
        elif isinstance(param, click.Option):
            if param.name == "help":
                continue
            assert param.name is not None
            help_text = param.help or OPTION_HELP.get((path, param.name), "")
            if not help_text and not isinstance(command, click.Group):
                raise SystemExit(f"scripts/docs.py: add a description for option {(path, param.name)} to OPTION_HELP")
            name = ", ".join(f"`{opt}`" for opt in sorted(param.opts, key=len))
            required = "yes" if param.required else "no"
            rows.append((name, _param_type(param), required, _param_default(param, ctx), help_text))

    rows.sort(key=lambda row: row[0].startswith("`-"))
    if rows:
        lines += ["| Argument or option | Type | Required | Default | Description |", "|---|---|---|---|---|"]
        lines += [" | ".join(["| " + row[0], *row[1:4], _escape_cell(row[4]) + " |"]) for row in rows]
        lines.append("")

    if path not in COMMAND_NOTES:
        raise SystemExit(f"scripts/docs.py: add an entry for command {path!r} to COMMAND_NOTES")
    notes = COMMAND_NOTES[path].strip()
    if notes:
        lines += [notes, ""]

    if isinstance(command, click.Group):
        for name in sorted(command.commands):
            sub = command.commands[name]
            if not sub.hidden:
                lines += _render_command(f"{path} {name}", sub, ctx, level + 1)
    return lines


def render_cli_reference() -> str:
    group = _load_cli()
    root = click.Context(group, info_name="cli")
    visible = {name: cmd for name, cmd in sorted(group.commands.items()) if not cmd.hidden}

    lines = [
        HEADER,
        "# CLI reference",
        "",
        "Installing cliffy adds two identical entry points, `cli` and `cliffy`. This page uses `cli`.",
        "It is generated from the command definitions in `cliffy/cli.py` and `cliffy/ai.py`, so the",
        "arguments, options and defaults below are the ones the installed version accepts.",
        "",
        "```text",
        "cli [OPTIONS] COMMAND [ARGS]...",
        "```",
        "",
        "## Commands at a glance",
        "",
        "| Command | Description |",
        "|---|---|",
    ]
    for name, cmd in visible.items():
        summary = inspect.cleandoc(cmd.help or "").split("\n")[0]
        anchor = f"cli-{name}"
        lines.append(f"| [`cli {name}`](#{anchor}) | {_escape_cell(summary)} |")
    lines += [
        "",
        "## Global options",
        "",
        "| Option | Description |",
        "|---|---|",
        "| `--version` | Print the version and exit. |",
        "| `--aliases` | List the command aliases and exit. |",
        "| `-h`, `--help` | Show help. Every command accepts this option. |",
        "",
        "## Aliases",
        "",
        "Aliases are hidden from `cli --help`. `cli --aliases` prints this list.",
        "",
        "| Alias | Command |",
        "|---|---|",
    ]
    lines += [f"| `cli {alias}` | [`cli {target}`](#cli-{target}) |" for alias, target in ALIASES.items()]
    lines.append("")

    for name, cmd in visible.items():
        lines += _render_command(name, cmd, root, 2)
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------------------------------
# Manifest reference
# --------------------------------------------------------------------------------------------------

# Descriptions for fields that have none in the model.
FIELD_FALLBACK: dict[tuple[str, str], str] = {
    ("CLIManifest", "manifestVersion"): "Manifest schema version. `v3` is the only version.",
    ("Command", "run"): "The script to run. A string, or a list of strings that are joined with newlines. "
    "Lines starting with `$` or `>` are shell commands.",
    ("Example", "command"): "The command line to show.",
    ("Example", "description"): "A sentence describing what the command does.",
    ("IncludeManifest", "requires"): "Merged into the `requires` of the including manifest.",
    ("IncludeManifest", "commands"): "Merged into the `commands` of the including manifest.",
    ("IncludeManifest", "vars"): "Merged into `vars`. Available as Python variables, not as `{{ }}` placeholders.",
    ("IncludeManifest", "imports"): "Merged into `imports`.",
    ("IncludeManifest", "functions"): "Merged into `functions`. Must be a list here.",
    ("IncludeManifest", "types"): "Merged into `types`.",
    ("IncludeManifest", "cli_options"): "Merged into `cli_options`.",
    ("IncludeManifest", "tests"): "Appended to `tests`.",
}

# Replacements for model descriptions that do not match what the code does. The model text also feeds
# the JSON schema and the `cli init` template, so it is corrected here instead of in cliffy/manifest.py.
FIELD_OVERRIDES: dict[tuple[str, str], str] = {
    ("CLIManifest", "requires"): "Python packages the CLI needs, as requirement specifiers such as `rich` or "
    "`tabulate>=0.9.0`. Checked when the manifest is loaded and bundled by `cli build`.",
    ("CLIManifest", "includes"): "Paths of other manifest files to merge into this one. Keys set in this manifest "
    "win over included ones; lists are combined.",
    ("CLIManifest", "vars"): "Variables for the manifest. Each one can be used anywhere in the file as "
    "`{{ name }}` and is also defined as a module-level Python variable in the generated CLI. Values are "
    "Jinja2 templates; `env` gives access to environment variables.",
    ("CLIManifest", "commands"): "The commands of the CLI, keyed by name. In a key, `.` separates groups, `|` "
    "separates aliases and a leading `(*)` adds the command to every group.",
    ("Command", "params"): "The parameters of the command. See [Params](#params) for the three accepted forms.",
    ("CommandConfig", "context_settings"): "Settings passed to the Click context of the command, for example "
    "`help_option_names` or `max_content_width`.",
    ("CommandConfig", "rich_help_panel"): "Name of the panel this command is listed under in rich help output.",
}

# Hand-written notes shown under each generated table. Every statement was checked by running it.
MODEL_NOTES: dict[str, str] = {
    "CLIManifest": """
- `name` and `version` are the only required keys besides `commands`. `version` must be a string, so
  quote values such as `"1.0"`.
- Unknown top-level keys are ignored.
- `manifestVersion` is accepted and ignored when a manifest file is loaded.
- `vars` values must be strings (quote numbers) or a one-key mapping such as `{"3"}` or `{os.getcwd()}`,
  which is emitted as a Python expression. See [Vars and Jinja](../guides/vars-and-jinja.md).
- `cli_options` is passed as keyword arguments to `typer.Typer(...)`, or to `click.group(...)` when
  `use_click` is set. Useful Typer values are `add_completion: false` and `no_args_is_help: true`.
- `commands` is usually a mapping. A list of [Command](#command) mappings that each set `name` is also
  accepted.
- Each `tests` entry is either a string starting with `$` or `>` (a shell step) or a one-key mapping of
  command line to assertion code. See [Testing manifests](../guides/testing.md).
""",
    "Command": """
A command value can also be just a string or a list of strings, which is shorthand for a mapping with
only `run`.

The key of the command carries meaning: `.` separates groups (`db.create`), `|` separates aliases
(`delete|rm`) and a leading `(*)` adds the command to every group. See
[Commands, groups and aliases](../guides/commands.md).

A command that has `help` and no `run`, and whose key is the name of a group, sets the help text of
that group.
""",
    "CommandParam": """
This is the explicit form. `short` is written with its dash (`-w`). With the Typer backend a `str`
default is quoted for you; other defaults are emitted as written.
""",
    "CommandTemplate": """
Template `params` are placed before the command's own params. Scripts run in this order: template
`pre_run`, command `pre_run`, command `run`, command `post_run`, template `post_run`. `config` values
from the command override the template's. See
[Command templates and global params](../guides/templates-and-global-params.md).
""",
    "CommandConfig": """
Only the keys you set are passed on, as keyword arguments of Typer's `command()`. The Click backend
ignores `config`.
""",
    "Example": """
`examples` entries are only used by [`cli docs`](../guides/generating-docs.md). An entry can also be a
plain string, which is shown without a description.
""",
    "IncludeManifest": """
Files listed under `includes` are validated against this smaller model. Paths are resolved relative to
the directory you run `cli` from. See [Includes and merging](../guides/includes.md).
""",
}

PARAM_SECTION = """
## Params

Every entry of a `params` list (on a command, a template or `global_params`) takes one of three forms.

### Shorthand

A one-key mapping: the key is the name, the value is the type.

| Part | Meaning | Example |
|---|---|---|
| `name` | Positional argument | `source: str` |
| `--name` | Option | `--count: int` |
| `--name\\|-n` | Option with a short alias | `--count\\|-c: int` |
| `type!` | Required | `source: str!` |
| `type = value` | Default value, written as a Python expression | `target: str = "out.txt"` |
| a name from `types` | Reuse a full Typer definition | `level: Level` |

Hyphens in a name become underscores in the Python variable (`--dry-run` is `dry_run`).

### Explicit

A mapping with the keys of [CommandParam](#commandparam), which adds `help` text.

### Generic

A plain string that is copied into the generated function signature as written, for example
`'lines: int = typer.Option(10, "--lines", "-n", min=1)'`. With the Click backend the string is a
decorator such as `"@click.option('--loud', is_flag=True)"`.

See [Params and types](../guides/params.md) for worked examples of all three.
"""

DOCUMENTED_MODELS: list[type[BaseModel]] = [
    CLIManifest,
    Command,
    CommandParam,
    CommandTemplate,
    CommandConfig,
    Example,
    IncludeManifest,
]

# Module-level type aliases and root models, rendered by name instead of by structure.
NAMED_TYPES: dict[str, str] = {
    "ParamBlock": "[param](#params)",
    "CommandBlock": "[Command](#command), string or list of strings",
    "VarBlock": "string or `{expression}`",
    "RunBlock": "string",
    "PreRunBlock": "string",
    "PostRunBlock": "string",
    "RunBlockList": "list of strings",
    "SimpleCommandParam": "shorthand param",
    "GenericCommandParam": "string",
}
BUILTIN_NAMES = {str: "string", int: "integer", float: "number", bool: "boolean", type(None): "null"}


def _alias_name(annotation: Any) -> str | None:
    for name in ("ParamBlock", "CommandBlock", "VarBlock"):
        if annotation == getattr(manifest_module, name):
            return name
    return None


def _plural(name: str) -> str:
    return {"string": "strings", "[param](#params)": "[params](#params)"}.get(name, name)


def _group(name: str) -> str:
    """Parenthesize a compound type so that it reads unambiguously inside a list or mapping."""
    return f"({name})" if " or " in name or "," in name else name


def _format_type(annotation: Any) -> str:
    if (alias := _alias_name(annotation)) is not None:
        return NAMED_TYPES[alias]
    if annotation is Any:
        return "any"
    if annotation in BUILTIN_NAMES:
        return BUILTIN_NAMES[annotation]
    if inspect.isclass(annotation) and issubclass(annotation, RootModel):
        return NAMED_TYPES[annotation.__name__]
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return f"[{annotation.__name__}](#{annotation.__name__.lower()})"

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin in (typing.Union, types.UnionType):
        parts: list[str] = []
        for arg in args:
            formatted = _format_type(arg)
            if formatted not in parts:
                parts.append(formatted)
        return " or ".join(parts)
    if origin is list:
        return f"list of {_group(_plural(_format_type(args[0])))}"
    if origin is dict:
        value = _format_type(args[1])
        return "mapping" if value == "any" else f"mapping of name to {_group(value)}"
    raise SystemExit(f"scripts/docs.py: cannot describe type {annotation!r}")


def _format_default(field: FieldInfo) -> str:
    if field.is_required():
        return "**required**"
    default = field.default_factory() if field.default_factory is not None else field.default  # type: ignore[call-arg]
    if isinstance(default, RootModel):
        default = default.root
    if default is None:
        return "`null`"
    if isinstance(default, bool):
        return f"`{str(default).lower()}`"
    if isinstance(default, str):
        return f'`"{default}"`'
    return f"`{default}`"


def _render_model(model: type[BaseModel], title: str) -> list[str]:
    lines = [f"## {title}", ""]
    doc = inspect.cleandoc(model.__doc__ or "")
    if model is CLIManifest:
        doc = "The top level of a manifest file."
    if doc:
        lines += [" ".join(doc.split()), ""]

    lines += ["| Key | Type | Default | Description |", "|---|---|---|---|"]
    for name, field in model.model_fields.items():
        key = (model.__name__, name)
        description = FIELD_OVERRIDES.get(key) or field.description or FIELD_FALLBACK.get(key)
        if not description:
            raise SystemExit(f"scripts/docs.py: add a description for {model.__name__}.{name} to FIELD_FALLBACK")
        lines.append(
            f"| `{name}` | {_escape_cell(_format_type(field.annotation))} | {_format_default(field)} "
            f"| {_escape_cell(description)} |"
        )
    lines.append("")

    notes = MODEL_NOTES[model.__name__].strip()
    if notes:
        lines += [notes, ""]
    return lines


def render_manifest_reference() -> str:
    lines = [
        HEADER,
        "# Manifest reference",
        "",
        "Every key a manifest accepts. The tables are generated from the pydantic models in",
        "`cliffy/manifest.py`, the same models that produce the",
        "[JSON schema](https://github.com/jaykv/cliffy/blob/main/examples/cliffy_schema.json) used for",
        "[editor completion](../guides/editor-setup.md). The notes under each table are written by hand.",
        "",
    ]
    lines += _render_model(CLIManifest, "Top-level keys")
    lines += _render_model(Command, "Command")
    lines += [*PARAM_SECTION.strip().split("\n"), ""]
    lines += _render_model(CommandParam, "CommandParam")
    lines += _render_model(CommandTemplate, "CommandTemplate")
    lines += _render_model(CommandConfig, "CommandConfig")
    lines += _render_model(Example, "Example")
    lines += _render_model(IncludeManifest, "Include files")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------------------------------
# Examples gallery
# --------------------------------------------------------------------------------------------------

# What each example demonstrates and a command line that works. Generation fails when a manifest is
# added to or removed from examples/ without updating this table.
EXAMPLE_NOTES: dict[str, tuple[str, str]] = {
    "hello.yaml": (
        "The smallest useful manifest: one shell command, one Python command and a `tests` section.",
        "cli run examples/hello.yaml python",
    ),
    "nested-cli.yaml": (
        "Command groups nested two levels deep with dotted keys.",
        "cli run examples/nested-cli.yaml group1 subgroup command1",
    ),
    "town.yaml": (
        "A larger CLI: groups with help text, shared `types`, short option aliases, command aliases and a "
        "`(*).list` command that is added to every group.",
        "cli run examples/town.yaml land list",
    ),
    "template.yaml": (
        "A command template that gives two commands the same params, a run script written as a list, "
        "and per-command `config`.",
        "cli run examples/template.yaml -- debug one --local-arg-2 two",
    ),
    "environ.yaml": (
        "Environment variables read when the manifest is loaded (`vars` with `env`) and when a command runs.",
        "cli run examples/environ.yaml hello",
    ),
    "db.yaml": (
        "Prompting options defined in `types`, YAML anchors to share params, `pre_run`, command aliases "
        "and `cli_options`.",
        "cli run examples/db.yaml -- mk --name demo",
    ),
    "penv.yaml": (
        "A virtualenv manager: `vars` holding Python expressions, helper `functions` and shell lines that "
        "interpolate Python values with `f{...}`.",
        "cli run examples/penv.yaml -- --help",
    ),
    "pydev.yaml": (
        "Developer chores as run-script lists that mix shell and Python lines, with helper functions.",
        "cli run examples/pydev.yaml -- --help",
    ),
    "taskmaster.yaml": (
        "A task manager with JSON storage, a `vars` placeholder used inside functions, shared `types`, "
        "nested groups and a full `tests` section.",
        "cli test examples/taskmaster.yaml",
    ),
    "todo.yaml": (
        "A sqlite-backed todo list that depends on `tabulate` and `rich`.",
        "cli run examples/todo.yaml -- --help",
    ),
    "requires.yaml": (
        "Version specifiers in `requires`. Loading fails on purpose unless `requests>=2.30.0` and `six<1.0.0` "
        "are installed, which is what the test suite checks.",
        "cli validate examples/requires.yaml",
    ),
    "click_hello.yaml": (
        "The Click backend (`use_click: true`) with a command alias. Needs the `rich` extra.",
        "cli run examples/click_hello.yaml hello",
    ),
    "aiprompt.yaml": (
        "An OpenAI client written by an LLM: explicit params with help text, `global_params` and nested "
        "groups. Needs `openai`, `rich` and `keyring`.",
        "cli render examples/aiprompt.yaml",
    ),
}


def render_examples_gallery() -> str:
    found = sorted(path.name for path in EXAMPLES.glob("*.yaml"))
    if set(found) != set(EXAMPLE_NOTES):
        missing = sorted(set(found) - set(EXAMPLE_NOTES))
        extra = sorted(set(EXAMPLE_NOTES) - set(found))
        raise SystemExit(f"scripts/docs.py: EXAMPLE_NOTES is out of date (missing {missing}, unknown {extra})")

    lines = [
        HEADER,
        "# Examples gallery",
        "",
        "The manifests in the [`examples/`](https://github.com/jaykv/cliffy/tree/main/examples) directory of the",
        "repository. Each entry shows the file as it is in the repository. The code cliffy generates for them is",
        "committed next to them in",
        "[`examples/generated/`](https://github.com/jaykv/cliffy/tree/main/examples/generated).",
        "",
        "To try one, clone the repository and run the command shown from its root.",
        "",
        "| Example | Backend | Requires | Has tests |",
        "|---|---|---|---|",
    ]
    loaded: dict[str, dict[str, Any]] = {}
    for name in EXAMPLE_NOTES:
        data = yaml.safe_load((EXAMPLES / name).read_text())
        loaded[name] = data
        requires = ", ".join(f"`{req}`" for req in data.get("requires", [])) or "nothing"
        backend = "Click" if data.get("use_click") else "Typer"
        tests = "yes" if data.get("tests") else "no"
        lines.append(f"| [{name}](#{data['name']}) | {backend} | {_escape_cell(requires)} | {tests} |")
    lines.append("")

    for name, (blurb, command) in EXAMPLE_NOTES.items():
        data = loaded[name]
        lines += [
            f"## {data['name']}",
            "",
            blurb,
            "",
            "```console",
            f"$ {command}",
            "```",
            "",
            f'??? example "examples/{name}"',
            "",
            "    ```yaml",
            f'    --8<-- "examples/{name}"',
            "    ```",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------------------

GENERATED = {
    DOCS / "reference" / "cli.md": render_cli_reference,
    DOCS / "reference" / "manifest.md": render_manifest_reference,
    DOCS / "reference" / "examples.md": render_examples_gallery,
}

SNIPPET_REFERENCE = re.compile(r'--8<--\s+"([^":]+)(?::[^"]*)?"')


def generate() -> int:
    for path, render in GENERATED.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render())
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


def check_generated() -> list[str]:
    errors = []
    for path, render in GENERATED.items():
        expected = render()
        actual = path.read_text() if path.exists() else ""
        if actual != expected:
            diff = "".join(
                difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=f"{path.relative_to(ROOT)} (committed)",
                    tofile=f"{path.relative_to(ROOT)} (generated)",
                    n=1,
                )
            )
            errors.append(f"{path.relative_to(ROOT)} is stale, run `make docs-generate`\n{diff}")
        else:
            print(f"ok    {path.relative_to(ROOT)} is up to date")
    return errors


def check_snippet_references() -> list[str]:
    """Every file pulled into a page with ``--8<--`` must exist."""
    errors = []
    for page in sorted(DOCS.rglob("*.md")):
        for reference in SNIPPET_REFERENCE.findall(page.read_text()):
            if not (ROOT / reference).is_file():
                errors.append(f"{page.relative_to(ROOT)} includes missing file {reference}")
    return errors


def check_readme() -> list[str]:
    """The manifest in README.md is a copy, so make sure it is still the start of the tested hello snippet."""
    match = re.search(r"```yaml\n# hello\.yaml\n(.*?)```", (ROOT / "README.md").read_text(), re.DOTALL)
    if not match:
        return ["README.md: the hello.yaml example block was not found"]
    if not (SNIPPETS / "hello.yaml").read_text().startswith(match.group(1)):
        return ["README.md: the hello.yaml example differs from docs/snippets/hello.yaml"]
    print("ok    README.md example matches docs/snippets/hello.yaml")
    return []


def check_snippets() -> list[str]:
    """Load, compile and test every manifest in docs/snippets from a scratch copy of that directory."""
    errors = []
    env = {**os.environ, "NO_COLOR": "1", "PYTHONWARNINGS": "ignore"}
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp) / "snippets"
        shutil.copytree(SNIPPETS, workdir)
        previous = Path.cwd()
        os.chdir(workdir)
        try:
            for path in sorted(workdir.glob("*.yaml")):
                name = f"docs/snippets/{path.name}"
                try:
                    with path.open() as manifest_io:
                        transformer = Transformer(manifest_io)
                    compile(transformer.cli.code, path.name, "exec")
                except (Exception, SystemExit) as e:
                    errors.append(f"{name} does not load: {e!r}")
                    continue

                if not transformer.manifest.tests:
                    print(f"ok    {name} loads and compiles (no tests section)")
                    continue

                result = subprocess.run(
                    [sys.executable, "-m", "cliffy", "test", path.name],
                    capture_output=True,
                    encoding="utf-8",
                    env=env,
                )
                cases = sum(isinstance(test, dict) for test in transformer.manifest.tests)
                if result.returncode != 0 or "All tests passed" not in result.stdout:
                    errors.append(f"{name} fails its tests:\n{result.stdout}\n{result.stderr}")
                else:
                    print(f"ok    {name} passes its {cases} tests")
        finally:
            os.chdir(previous)
    return errors


def check() -> int:
    errors = check_generated() + check_snippet_references() + check_readme() + check_snippets()
    for error in errors:
        print(f"FAIL  {error}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} problem(s) found", file=sys.stderr)
        return 1
    print("\ndocs are in sync with the code")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["generate", "check"])
    args = parser.parse_args()
    return generate() if args.command == "generate" else check()


if __name__ == "__main__":
    sys.exit(main())
