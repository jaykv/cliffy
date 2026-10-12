---
title: cliffy
hide:
  - navigation
---

# cliffy

![cliffy logo](images/logo.svg){ width="220" }

**Describe a command-line tool in YAML. Get a real Python CLI.**

cliffy reads a manifest that lists your commands, their parameters and the code each one runs, and
generates a [Typer](https://typer.tiangolo.com/) application from it. Command bodies are plain Python,
and any line that starts with `$` runs as a shell command, so a manifest can replace a folder of
one-off scripts with a single CLI that has help text, typed arguments and subcommands.

## A CLI in 60 seconds

**1. Install cliffy** (Python 3.11 to 3.15):

```console
$ pip install cliffy
```

**2. Write a manifest** and save it as `hello.yaml`:

```yaml title="hello.yaml"
--8<-- "docs/snippets/hello.yaml"
```

**3. Load it.** cliffy generates the CLI and puts a `hello` command into your Python environment:

```console
$ cli load hello.yaml
✨ Generated hello CLI v0.1.0 ✨
$ hello -h
```

**4. Use it** like any other command:

```console
$ hello shell
hello from shell
$ hello greet Ada --shout
HELLO, ADA!
$ hello --help

 Usage: hello [OPTIONS] COMMAND [ARGS]...

 Hello world!

╭─ Options ──────────────────────────────────────────────────────────────────╮
│ --version                                                                  │
│ --install-completion          Install completion for the current shell.    │
│ --show-completion             Show completion for the current shell, to    │
│                               copy it or customize the installation.       │
│ --help                -h      Show this message and exit.                  │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────╮
│ shell                                                                      │
│ python                                                                     │
│ greet   Greet someone by name                                              │
╰────────────────────────────────────────────────────────────────────────────╯
```

The `tests` section at the bottom of the manifest is optional. `cli test hello.yaml` runs it.

## What you get

- **Python and shell in one place.** Run scripts are Python; lines starting with `$` become
  `subprocess` calls. See [Shell commands](guides/shell-commands.md).
- **Typed parameters with a short syntax.** `name: str!` is a required argument and
  `--count|-c: int = 1` is an option. See [Params and types](guides/params.md).
- **Groups, aliases and templates.** `db.create` nests a command, `delete|rm` adds an alias and
  command templates share params between commands. See
  [Commands, groups and aliases](guides/commands.md).
- **A fast edit loop.** `cli dev` reloads the CLI every time you save the manifest. See
  [Hot-reload dev loop](guides/dev-loop.md).
- **Tests next to the commands.** `cli test` runs the assertions you keep in the manifest. See
  [Testing manifests](guides/testing.md).
- **One file to ship.** `cli build` packs the CLI and its dependencies into a single executable
  zipapp, a single Python script or a native executable. See
  [Building executables](guides/building.md).

## How it works

```text
manifest.yaml ──► validate ──► generate Python (Typer or Click) ──► load │ run │ build
```

1. cliffy renders the manifest with [Jinja2](https://jinja.palletsprojects.com/), parses the YAML and
   validates it against the [manifest schema](reference/manifest.md).
2. It generates one Python module. `cli render` prints that module, so nothing about the result is
   hidden.
3. `cli load` installs the module as a command, `cli run` executes it once and `cli build` packages it.

## Where to go next

| If you want to | Read |
|---|---|
| Install cliffy and its extras | [Installation](installation.md) |
| Build a complete CLI step by step | [Quickstart](quickstart.md) |
| Look up a manifest key | [Manifest reference](reference/manifest.md) |
| Look up a `cli` command or flag | [CLI reference](reference/cli.md) |
| Copy from working manifests | [Examples gallery](reference/examples.md) |
| Upgrade from an older release | [Migration notes](project/migration.md) |

## Similar tools

- [Bashly](https://github.com/DannyBen/bashly) generates Bash CLIs from YAML.
- [Fire](https://github.com/google/python-fire) generates CLIs from Python objects.
