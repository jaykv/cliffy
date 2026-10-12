![cliffy logo](https://raw.githubusercontent.com/jaykv/cliffy/main/docs/images/logo.svg)

[![CI](https://img.shields.io/github/actions/workflow/status/jaykv/cliffy/python-app.yaml?branch=main)](https://github.com/jaykv/cliffy/actions)
[![PyPI](https://img.shields.io/pypi/v/cliffy)](https://pypi.org/project/cliffy/)
[![Python versions](https://img.shields.io/pypi/pyversions/cliffy)](https://pypi.org/project/cliffy/)
![License](https://img.shields.io/github/license/jaykv/cliffy)
[![codecov](https://codecov.io/github/jaykv/cliffy/graph/badge.svg?token=84SM8XD5IW)](https://codecov.io/github/jaykv/cliffy)
[![Documentation](https://img.shields.io/badge/docs-jaykv.github.io%2Fcliffy-8A2BE2)](https://jaykv.github.io/cliffy/)

# cliffy

Describe a command-line tool in YAML and get a real Python CLI.

cliffy reads a manifest that lists your commands, their parameters and the code each one runs, and
generates a [Typer](https://typer.tiangolo.com/) application from it. Command bodies are plain Python,
and any line that starts with `$` runs as a shell command.

**Documentation: <https://jaykv.github.io/cliffy/>**

## Example

Install cliffy (Python 3.11 to 3.15):

```console
$ pip install cliffy
```

Write a manifest:

```yaml
# hello.yaml
name: hello
version: 0.1.0
help: Hello world!

commands:
  shell: $ echo "hello from shell"
  python: print("hello from python")
  greet:
    help: Greet someone by name
    params:
      - name: str!
      - --shout|-s: bool = False
    run: |
      message = f"Hello, {name}!"
      print(message.upper() if shout else message)
```

Load it and use it:

```console
$ cli load hello.yaml
✨ Generated hello CLI v0.1.0 ✨
$ hello shell
hello from shell
$ hello greet Ada --shout
HELLO, ADA!
```

## What it does

- **Python and shell in one place.** Run scripts are Python; `$` lines become `subprocess` calls.
- **Typed parameters with a short syntax.** `name: str!` is a required argument, `--count|-c: int = 1`
  is an option.
- **Groups, aliases and templates.** `db.create` nests a command, `delete|rm` adds an alias, command
  templates share params between commands.
- **Hot reload.** `cli dev hello.yaml` reloads the CLI every time you save the manifest.
- **Built-in tests.** Keep assertions next to your commands and run them with `cli test`.
- **Single-file executables.** `cli build hello.yaml` packs the CLI and its dependencies into one
  zipapp.

## Commands

| Command | Description |
|---|---|
| `cli init <name>` | Write a manifest template |
| `cli run <manifest> -- <args>` | Run a manifest's CLI once, without installing it |
| `cli load <manifest>` | Install the CLI as a command in the current environment |
| `cli dev <manifest>` | Reload the CLI whenever the manifest changes |
| `cli test <manifest>` | Run the tests defined in the manifest |
| `cli build <manifest>` | Build a single-file executable |
| `cli render <manifest>` | Print the generated Python code |
| `cli validate <manifest>` | Check a manifest against the schema |
| `cli docs <manifest>` | Generate documentation for the CLI |
| `cli list`, `info`, `update`, `remove` | Manage loaded CLIs |
| `cli ai generate`, `cli ai ask` | Draft manifests with an LLM (needs the `ai` extra) |

Every command and option is described in the
[CLI reference](https://jaykv.github.io/cliffy/reference/cli/).

## Install options

```console
$ pip install cliffy               # core
$ pip install "cliffy[rich]"       # rich-click help for the cli command, needed for the Click backend
$ pip install "cliffy[ai]"         # AI commands, built on pydantic-ai
$ uvx cliffy run hello.yaml greet Ada   # run without installing
```

See [Installation](https://jaykv.github.io/cliffy/installation/) for details.

## Learn more

- [Quickstart](https://jaykv.github.io/cliffy/quickstart/): build a complete CLI step by step
- [Guides](https://jaykv.github.io/cliffy/guides/manifest-basics/): params, groups, templates,
  includes, vars, shell commands, testing, building
- [Manifest reference](https://jaykv.github.io/cliffy/reference/manifest/): every key of the format
- [Examples](https://jaykv.github.io/cliffy/reference/examples/): the manifests in
  [`examples/`](examples/)
- [Changelog](https://jaykv.github.io/cliffy/project/changelog/) and
  [migration notes](https://jaykv.github.io/cliffy/project/migration/)
- [Contributing](https://jaykv.github.io/cliffy/project/contributing/)

## Similar tools

- [Bashly](https://github.com/DannyBen/bashly) generates Bash CLIs from YAML.
- [Fire](https://github.com/google/python-fire) generates CLIs from Python objects.

## License

[MIT](LICENSE)
