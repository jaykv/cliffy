![Cliffy logo](docs/images/logo.svg)

[![GitHub Workflow Status (with branch)](https://img.shields.io/github/actions/workflow/status/jaykv/cliffy/python-app.yaml?branch=main)](https://github.com/jaykv/cliffy/actions)
[![PyPI](https://img.shields.io/pypi/v/cliffy)](https://pypi.org/project/cliffy/)
![GitHub](https://img.shields.io/github/license/jaykv/cliffy)
[![codecov](https://codecov.io/github/jaykv/cliffy/graph/badge.svg?token=84SM8XD5IW)](https://codecov.io/github/jaykv/cliffy)
[![cliffy docs](https://img.shields.io/badge/📝%20docs-8A2BE2)](https://jaykv.github.io/cliffy)

Build feature-rich CLIs _quickly_.

## Features
* ⚡ Generate Python CLIs with a simple YAML manifest
* 📦 Package your CLI into a single executable that runs anywhere
* 🔄 Hot-reload changes instantly during development with built-in testing
* 🎨 Mix Python and shell commands naturally with built-in scripting support
* 🤖 AI-friendly with [manifest generation support](https://jaykv.github.io/cliffy/features#ai-features)

### Load

1. Define a manifest
```yaml
# hello.yaml
name: hello
version: 0.1.0

commands:
  shell: 
    help: Print hello in shell
    run: $echo "hello from shell"
  python: print("hello from python")
```

2. Load CLI
```
$ cli load hello.yaml
```
Parses `hello.yaml` to generate a Typer CLI and load it into the running Python environment.

3. Run CLI directly

`hello -h`

![hello-demo](docs/images/hello.png)

### Build

Simple todo CLI with sqlite3 + tabulate.

1. Define the manifest
```yaml
# todo.yaml
name: todo
version: 1.0.0
requires:
  - tabulate  # For pretty table output
  - rich      # For colored terminal output
imports: |
  import sqlite3
  from pathlib import Path
  from tabulate import tabulate
  from rich import print

commands:
  create:
    help: Create a new database with tasks table
    params:
      - name: str = typer.Option(..., prompt=True, confirmation_prompt=True)
    run: |
      db_path = Path(f"{name}.db")
      conn = sqlite3.connect(db_path)
      conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, task TEXT NOT NULL, done BOOLEAN NOT NULL)")

      # insert example tasks
      conn.execute("INSERT INTO tasks (task, done) VALUES ('Fight for your right!', 0)")
      conn.execute("INSERT INTO tasks (task, done) VALUES ('To party!', 1)")
      conn.commit()
      conn.close()
      print(f"✨ Created database {db_path} with tasks table")

  tasks:
    help: List tasks in database
    params: [name: str!]
    run: |
      conn = sqlite3.connect(f"{name}.db")
      cursor = conn.execute("SELECT * FROM tasks")
      tasks = cursor.fetchall()
      conn.close()
      print(tabulate(tasks, headers=['ID', 'Task', 'Done'], tablefmt='grid'))

  add:
    help: Add a new task
    params: [name: str!, task: str!]
    run: |
      conn = sqlite3.connect(f"{name}.db")
      conn.execute("INSERT INTO tasks (task, done) VALUES (?, 0)", (task,))
      conn.commit()
      conn.close()
      print(f"📝 Added task: {task}")

  complete:
    help: Mark a task as complete
    params: [name: str!, id: int!]
    run: |
      conn = sqlite3.connect(f"{name}.db")
      conn.execute("UPDATE tasks SET done = 1 WHERE id = ?", (id,))
      conn.commit()
      conn.close()
      print(f"🎉 Marked task {id} as complete")
```

![todo-demo](docs/images/demo.gif)

For more examples, check [examples](examples/) directory.

## Usage
`cli <command>`

| Command | Description |
|---|---|
| `init <cli name>`| Generate a template CLI manifest for a new CLI |
| `load <manifest>` | Add a new CLI based on the manifest |
| `render <manifest>` | View generated CLI script for a manifest |
| `list, ls` | Output a list of loaded CLIs |
| `update <cli name>`| Reload a loaded CLI |
| `remove <cli name>, rm <cli name>` | Remove a loaded CLI |
| `run <manifest> -- \<args>`| Runs a CLI manifest command in isolation|
| `build <cli name or manifest>` | Build a CLI manifest or a loaded CLI into a self-contained zipapp |
| `info <cli name>` | Display CLI metadata |
| `dev <manifest>` | Start hot-reloader for a manifest for active development |
| `test <manifest>` | Run tests defined in a manifest |
| `validate <manifest>` | Validate the syntax and structure of a CLI manifest |
| `docs <cli name or manifest>` | Generate documentation for a CLI |
| `ai generate <cli name> <description>` | Generate a CLI manifest based on a description. |
| `ai ask <prompt>` | Ask a question about cliffy or a specific CLI manifest. |

## How it works
1. Define CLI manifests in YAML files
2. Run `cli` commands to load, build, and manage CLIs
3. When loaded, cliffy parses the manifest and generates a [Typer](https://github.com/tiangolo/typer) CLI that is deployed directly as a script
4. Any code starting with `$` will translate to subprocess calls via [PyBash](https://github.com/jaykv/pybash)
5. Run loaded CLIs straight from the terminal
6. When ready to share, run `build` to generate portable zipapps built with [Shiv](https://github.com/linkedin/shiv)

## Get started

Cliffy can be installed using either pip or uv package managers.

### With pip
* `pip install "cliffy[rich]"` to include [rich-click](https://github.com/ewels/rich-click) for colorful CLI help output formatted with [rich](https://github.com/Textualize/rich).

or 

* `pip install cliffy` to use the default help output.
* `cli init mycli`

### With uv
* Init: `uvx cliffy init mycli`
* Load: `uvx cliffy load mycli.yaml`
* Run: `uvx --from cliffy mycli -h`

## Manifest template
Generated by `cli init`. For a barebones template, run `cli init --raw`

```yaml
manifestVersion: v3

# The name of the CLI, used when invoking from command line.
name: cliffy

# CLI version
version: 0.1.0

# Brief description of the CLI
help: A brief description of your CLI

# List of Python package dependencies for the CLI.Supports requirements specifier syntax.
requires: []
  # - requests>=2.25.1
  # - pyyaml~=5.4

# List of external CLI manifests to include.Performs a deep merge of manifests sequentially in the order given to assemble a merged manifest
# and finally, deep merges the merged manifest with this manifest.
includes: []
  # - path/to/other/manifest.yaml

# Mapping defining manifest variables that can be referenced in any other blocks
# Environments variables can be used in this section with ${some_env_var} for dynamic parsing
# Supports jinja2 formatted expressions as values
# Interpolate defined vars in other blocks jinja2-styled {{ var_name }}.
vars:
  data_file: "data.json"
  debug_mode: "{{ env['DEBUG'] or 'False' }}"

# String block or list of strings containing any module imports
# These can be used to import any python modules that the CLI depends on.
imports: |
  import json
  import os
  from pathlib import Path

# List of helper function definitions
# These functions should be defined as strings that can be executed by the Python interpreter.
functions:
  - |
    def load_data() -> dict:
        data_path = Path("{{ data_file }}")
        if data_path.exists():
            with data_path.open() as f:
                return json.load(f)
        return {}
  - |
      def save_data(data):
          with open("{{data_file}}", "w") as f:
              json.dump(data, f, indent=2)
# A mapping containing any shared type definitions
# These types can be referenced by name in the args section to provide type annotations for params and options defined in the args section.
types:
  Filename: str = typer.Argument(..., help="Name of the file to process")
  Verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")

# Arguments applied to all commands
global_params:
  - verbose: Verbose

# Reusable command templates
command_templates:
  with_confirmation:
    params:
      - "yes": bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
    pre_run: |
      if not yes:
        typer.confirm("Are you sure you want to proceed?", abort=True)

# A mapping containing the command definitions for the CLI
# Each command should have a unique key- which can be either a group command or nested subcommands
# Nested subcommands are joined by '.' in between each level
# Aliases for commands can be separated in the key by '|'
# A special '(*)' wildcard can be used to spread the subcommand to all group-level commands
commands:
  hello:
    help: Greet the user
    params:
      - name: str = typer.Option("World", "--name", "-n", help="Name to greet")
    run: |
      print(f"Hello, {name}!")
      $ echo "i can also mix-and-match this command script to run shell commands"

  file.process:
    help: Process a file
    params:
      - filename: Filename
    run: |
      data = load_data()
      print(f"Processing {filename}")
      if verbose:
        print("Verbose output enabled")
      data["processed"] = [filename]
      # Process the file here
      save_data(data)

  delete|rm:
    help: Delete a file
    template: with_confirmation
    params: [filename: Filename]
    run: |
      if verbose:
        print(f"Deleting {filename}")
      os.remove(filename)
      print("File deleted successfully")

# Additional CLI configuration options
cli_options:
  rich_help_panel: True

# Test cases for commands
tests:
  - hello --name Alice: assert 'Hello, Alice!' in result.output
  - file process test.txt: assert 'Processing test.txt' in result.output
```
