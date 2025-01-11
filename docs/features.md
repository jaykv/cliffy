# Cliffy Features

Cliffy provides a wide range of features to help you build powerful and flexible command-line interfaces. This guide will explore some of the key features with examples.

## Dependencies

You can specify Python package dependencies for the CLI using the `requires` section. For example:

```yaml
requires:
  - tabulate>=0.9.0
```

This ensures that the `tabulate` package is installed when the CLI is used. Built CLIs will automatically bundle these specified dependencies with the CLI zipapp, making it super easy to distribute CLIs.

## Imports

The `imports` section allows you to import Python modules. For example:

```yaml
imports: |
  import json
  from datetime import datetime
  from tabulate import tabulate
```

These modules can then be used in any of your command or function definitions.

## Variables

You can define variables in the `vars` section and use them throughout your manifest. For example:

```yaml
vars:
  data_file: "tasks.json"
```

Then, you can reference this variable using `{{data_file}}` in other parts of the manifest for dynamic injection on CLI load.

## Functions

The `functions` section allows you to define helper functions that can be used in your commands. For example:

```yaml
functions:
  - |
    def load_data():
        try:
            with open("{{data_file}}", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"projects": [], "tasks": []}
```

These functions can be used to encapsulate reusable logic.

## Types

You can define custom types in the `types` section and use them in your command arguments and options. For example:

```yaml
types:
  ProjectName: str = typer.Argument(..., help="Name of the project")
  TaskName: str = typer.Argument(..., help="Name of the task")
  DueDate: str = typer.Option(None, "--due", "-d", help="Due date (YYYY-MM-DD)")
  Priority: int = typer.Option(1, "--priority", "-p", help="Priority (1-5)", min=1, max=5)
```

This allows you to define type annotations and help messages for your arguments and options.

## Commands

The `commands` section defines the different commands that your CLI supports. For example:

```yaml
commands:
  project.add:
    args: [name: ProjectName]
    run: |
      data = load_data()
      if name not in data["projects"]:
          data["projects"].append(name)
          save_data(data)
          print(f"Project '{name}' added successfully.")
      else:
          print(f"Project '{name}' already exists.")
```

This defines a nested `project add` command that takes a `ProjectName` argument.

## Shell Commands

You can execute shell commands using the `$` prefix in the `run` section. For example:

```yaml
backup:
  help: Create a backup of the task data
  run: |
    $ cp {{data_file}} {{data_file}}.backup
    $ echo "Backup created: {{data_file}}.backup"
```

This allows you to integrate shell commands into your CLI. Internally, shell commands will get translated into python subprocess calls. You can always verify the generated CLI code using `cli render`.

In special cases, you may want to trigger the unsafe `shell=True` in the subprocess calls. For those times, you can use the `>` prefix instead. [Beware!](https://docs.python.org/3.10/library/subprocess.html#security-considerations)

## Command Templates

You can define reusable command templates in the `command_templates` section. For example:

```yaml
command_templates:
  with_confirmation:
    args:
      - "yes": bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
    pre_run: |
      if not yes:
        typer.confirm("Are you sure you want to proceed?", abort=True)
```

Then, you can use this template in your commands:

```yaml
commands:
  delete|rm:
    help: Delete a file
    template: with_confirmation
    args: [filename: Filename]
    run: |
      if verbose:
        print(f"Deleting {{filename}}")
      os.remove(filename)
      print("File deleted successfully")
```

This allows you to reuse common argument definitions and pre/post run logic across multiple commands.

## Tests

The `tests` section allows you to define test cases for your commands. For example:

```yaml
tests:
  - project add test1: assert result.exit_code == 0
  - project list: assert "test1" in result.output
```

These tests can then be run with `cli test`. 

Explore the [Schema](schema.md) for concrete definition of CLI configuration and manifest fields.