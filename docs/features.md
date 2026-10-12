# Cliffy Features

Cliffy provides a wide range of features to help you build powerful and flexible command-line interfaces. This guide will explore some of the key features with examples.

!!! note
    Refer to [Typer docs](https://typer.tiangolo.com/tutorial/parameter-types/) for docs on crafting custom paramater types.

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
    params: [name: ProjectName]
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

## Global params

Define `global_params` to add common arguments/options across ALL commands.

```yaml
global_params:
  - name: "--verbose"
    type: "bool"
    default: false
    help: "Enable verbose output"

commands:
  hello:
    run: |
      if verbose:
        print("Verbose mode enabled")
      print("Hello!")
  goodbye:
    run: |
      if verbose:
        print("Verbose mode enabled")
      print("Goodbye!")
```

When either command is executed with `--verbose`, the corresponding `if verbose:` block within the run script will be executed.

Note how the verbose variable is available directly within the command's script. No special handling is needed. It's treated like a normal parameter.

## Command Templates

You can define reusable command templates in the `command_templates` section. For example:

```yaml
command_templates:
  with_confirmation:
    params:
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
    params: [filename: Filename]
    run: |
      if verbose:
        print(f"Deleting {{filename}}")
      os.remove(filename)
      print("File deleted successfully")
```

This allows you to reuse common argument definitions and pre/post run logic across multiple commands.

!!! note
    Command script execution is performed in the following order:

    1. Template pre-run
    2. Command pre-run
    3. Command run
    4. Command post-run
    5. Template post-run

## Tests

The `tests` section allows you to define test cases for your commands. For example:

```yaml
tests:
  - project add test1: assert result.exit_code == 0
  - project list: assert "test1" in result.output
```

These tests can then be run with `cli test`. 

## Hot-reload

Use the `cli dev` command to actively monitor a manifest for changes and automatically reload. Highly recommended for CLI manifest development.

!!! example 
    - `cli dev examples/hello.yaml`
    - `cli dev examples/hello.yaml --run-cli hello` (reload on change and run `hello` command)

## IDE Integration

### Schema validation and autocomplete

To get real-time feedback while developing your CLI, install the [YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) and setup by either:

a. Generating manifest with local json-schema: `cli init --json-schema`
b. Referencing the latest remote json-schema in your manifest:

  ```yaml
  # yaml-language-server: $schema=https://raw.githubusercontent.com/jaykv/cliffy/refs/heads/main/examples/cliffy_schema.json
  ```

### Embedded syntax highlighting

Install the [YAML embedded languages extension](https://marketplace.visualstudio.com/items?itemName=harrydowning.yaml-embedded-languages) for proper syntax-highlighting for command run scripts.


## AI Features

Cliffy includes AI-powered commands to help you generate and understand CLI manifests. Access these features through the `cli ai` command group.

!!! note
    Requires the `ai` extra: `pip install "cliffy[ai]"`. See [Installation](getting-started.md#installation).
    Without it, `cli ai` commands exit with an install hint; the rest of cliffy is unaffected.

### Choosing a model

The AI commands are built on [Pydantic AI](https://pydantic.dev/docs/ai/models/overview/) and work with any model it supports. Models are named `provider:model`, and each provider reads its API key from its usual environment variable.

The model is picked in this order:

1. the `--model` / `-m` option
2. the `CLIFFY_AI_MODEL` environment variable
3. a default for the first provider that has an API key set:

    | API key | Default model |
    |---|---|
    | `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) | `google:gemini-flash-latest` |
    | `ANTHROPIC_API_KEY` | `anthropic:claude-sonnet-5-5` |
    | `OPENAI_API_KEY` | `openai:gpt-5.4-mini` |

```bash
# use the default model of the provider whose key is set
export ANTHROPIC_API_KEY='your-api-key'
cli ai generate mycli "Create a todo app"

# pick a model for one command
cli ai generate mycli "Create a todo app" --model openai:gpt-5.5

# or for the whole shell session
export CLIFFY_AI_MODEL=google:gemini-2.5-pro
```

!!! tip
    Use `--preview` to print the fully constructed prompt instead of sending it. This needs neither a model nor an API key.

### Manifest Generation

Generate complete CLI manifests from natural language descriptions:

```bash
cli ai generate mycli "Create a CLI for managing docker containers with commands to list, start, stop and remove containers"
cli load mycli.yaml
```

The model's reply is validated before anything is written: it has to be valid YAML, match the manifest schema, and produce a CLI that is valid Python. A reply that fails is sent back to the model together with the reason, up to `--retries` times (default 2). If no valid manifest comes back, the command fails and writes nothing.

`mycli.yaml` is written to the current directory, or to `--output-dir`. An existing file is only replaced with `--force`.

!!! warning
    Validation checks that the manifest loads, not that the commands do what you asked. Read the generated run blocks before running the CLI.

### Interactive Help

Get AI assistance for understanding and working with cliffy:

```bash
cli ai ask "How do I create nested subcommands?"
```

The question is answered from a reference built from your installed cliffy version: its command list, the annotated `cli init` template and the manifest JSON schema.

You can also get targeted help about specific CLIs by referencing a manifest or a loaded CLI:

```bash
cli ai ask --cli mycli.yaml "How do I add input validation to the start command?"
```

The answer is printed to stdout and token usage to stderr, so the answer can be redirected to a file.
