# Manifest basics

A manifest is one YAML file that describes one CLI. This page explains its parts and how cliffy
turns them into Python. For a hands-on introduction, start with the [Quickstart](../quickstart.md).

## The smallest manifest

Three keys are required: `name`, `version` and `commands`.

```yaml title="hello.yaml"
name: hello
version: 0.1.0

commands:
  world: print("hello world")
```

```console
$ cli run hello.yaml world
hello world
```

## Top-level keys

| Key | What it is for | Guide |
|---|---|---|
| `name` | The command people type. | |
| `version` | Printed by `--version`. Must be a string, so write `"1.0"` with quotes. | |
| `help` | Description shown at the top of `--help`. | |
| `commands` | The commands and the code they run. | [Commands, groups and aliases](commands.md) |
| `imports` | Python imports for the generated module. | [below](#imports-and-functions) |
| `functions` | Helper functions shared by all commands. | [below](#imports-and-functions) |
| `vars` | Variables you can reuse across the manifest. | [Vars and Jinja](vars-and-jinja.md) |
| `types` | Named parameter definitions. | [Params and types](params.md) |
| `global_params` | Params added to commands. | [Templates and global params](templates-and-global-params.md) |
| `command_templates` | Reusable params, hooks and settings. | [Templates and global params](templates-and-global-params.md) |
| `includes` | Other manifests to merge in. | [Includes and merging](includes.md) |
| `requires` | Python packages the CLI depends on. | [below](#dependencies) |
| `cli_options` | Options for the CLI application object. | [below](#cli-options) |
| `use_click` | Generate Click code instead of Typer. | [Click and Typer backends](backends.md) |
| `tests` | Commands to run and assertions to check. | [Testing manifests](testing.md) |
| `examples` | Example command lines for generated docs. | [Generating docs](generating-docs.md) |

Keys that cliffy does not know are ignored. The [manifest reference](../reference/manifest.md) lists
every key with its type and default.

## How a manifest becomes Python

cliffy writes a single Python module from the manifest, in this order:

1. `import subprocess`, `import typer` and the lines from `imports`
2. one variable per entry in `vars`
3. the Typer application, with `--version` built in
4. the `functions`
5. one function per command, registered with Typer

Each command's `run` script becomes the body of its function, and its params become the function's
arguments. That is the whole model: anything you can write in a Python function, you can write in
`run`.

To read the generated module for any manifest:

```console
$ cli render hello.yaml
```

## Imports and functions

```yaml
imports: |
  import json
  from pathlib import Path

functions:
  - |
    def load(path: str) -> dict:
        return json.loads(Path(path).read_text())
  - |
    def branch() -> str:
        out = $ git rev-parse --abbrev-ref HEAD
        return out.decode().strip()
```

`imports` is a block of text or a list of lines. `functions` is a list with one function per item.
`subprocess` and `typer` are always imported, so `typer.Exit`, `typer.confirm` and friends are
available everywhere.

Write `functions` as a list when a function contains [shell lines](shell-commands.md). A single
block of text is also accepted, but `$` lines inside it are not translated.

## Dependencies

List the packages your code imports under `requires`, using the same specifiers as `pip`:

```yaml
requires:
  - tabulate>=0.9.0
  - rich
```

- `cli load`, `cli run`, `cli test` and `cli validate` stop with `missing requirement` when a listed
  package is not installed in the environment cliffy runs in.
- `cli build` downloads the listed packages and bundles them into the executable.

## CLI options

`cli_options` is passed to the Typer application as keyword arguments. Two common settings:

```yaml
cli_options:
  add_completion: false   # hide --install-completion and --show-completion
  no_args_is_help: true   # print help when the CLI is called without a command
```

## Check, run, load

| Command | What it does |
|---|---|
| `cli validate hello.yaml` | Checks the YAML, the schema and the `requires`. |
| `cli render hello.yaml` | Prints the generated Python. |
| `cli run hello.yaml -- <args>` | Runs the CLI once without installing it. |
| `cli test hello.yaml` | Runs the `tests` section. |
| `cli load hello.yaml` | Installs the CLI as a command in the current environment. |

All of them are described in the [CLI reference](../reference/cli.md).

## YAML pitfalls

Manifests mix YAML, Jinja and Python, and each has its own special characters.

**A colon followed by a space ends a YAML key.** This one-line command breaks, because of `: ` inside
the string:

```yaml
commands:
  status: print("status: ok")      # YAML error
```

Use a block instead:

```yaml
commands:
  status: |
    print("status: ok")
```

**Quote values that YAML would not read as text.** `version: 1.0` is a number and is rejected;
`version: "1.0"` works. The same applies to values in `vars`.

**Quote a one-line command that starts with `>`.** YAML treats a leading `>` as its own syntax, so
write `run: "> ls *.txt"`.

**Double braces belong to Jinja.** `{{ name }}` is replaced when the manifest is loaded. To get
literal double braces into your Python, see [Vars and Jinja](vars-and-jinja.md#literal-braces).

## Editor support

cliffy publishes a JSON schema for manifests, which gives you completion and validation while you
type. See [Editor setup](editor-setup.md).
