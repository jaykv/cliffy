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

#### Schema validation and autocomplete

To get real-time feedback while developing your CLI, install the [YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) and setup by either:

a. Generating manifest with local json-schema: `cli init --json-schema`
b. Referencing the latest remote json-schema in your manifest:

  ```yaml
  # yaml-language-server: $schema=https://raw.githubusercontent.com/jaykv/cliffy/refs/heads/main/examples/cliffy_schema.json
  ```

### Embedded syntax highlighting

Install the [YAML embedded languages extension](https://marketplace.visualstudio.com/items?itemName=harrydowning.yaml-embedded-languages) for proper syntax-highlighting for command run scripts.

## LLM-friendly Prompt

Use this prompt as a system prompt to generate custom Cliffy manifests with your choice of LLM. 

The output will be the CLI manifest which can then be loaded into cliffy with `cli load` or built into a single-file executable with `cli build`.

```
You are a YAML manifest generator. Your task is to generate a single YAML manifest using the given json-schema. The json-schema defines the structure of a YAML manifest that gets translated to a Typer CLI. Typer is the CLI framework in Python. Use Typer features and imports as needed to craft the best CLI for the following listed CLI requirements. Generate the YAML manifest only for the requested CLI.

cli_schema.json:
```json
{"$defs":{"Command":{"description":"Defines a single command within the CLI. It specifies the command's execution logic,\nparameters, and configuration.","properties":{"run":{"anyOf":[{"$ref":"#/$defs/RunBlock"},{"$ref":"#/$defs/RunBlockList"}],"default":"","title":"Run"},"help":{"default":"","description":"A description of the command, displayed in the help output.","title":"Help","type":"string"},"params":{"default":[],"description":"A list of parameters for the command.\nThere are three ways to define a param: \n(generic) 1. A string as param definition. Gets appended to the command params signature.\n(implicit) 2. A mapping with the param name as the key and the type as the value. Custom types are accepted here. Same as the implicit v1 params syntax. \n(explicit) 3. A mapping with the following keys: `name` (required), `type` (required), `default` (None by default), `help` (Optional), `short` (Optional), `required` (False by default).","items":{"anyOf":[{"$ref":"#/$defs/CommandParam"},{"$ref":"#/$defs/SimpleCommandParam"},{"$ref":"#/$defs/GenericCommandParam"}]},"title":"Params","type":"array"},"template":{"default":"","description":"A reference to a command template defined in the `command_templates` section of the manifest. This allows for reusable command definitions.","title":"Template","type":"string"},"pre_run":{"$ref":"#/$defs/PreRunBlock","default":"","description":"Script to run before the command's run block. This can be used for setup tasks or preconditions."},"post_run":{"$ref":"#/$defs/PostRunBlock","default":"","description":"Script to run after the command's run block. This can be used for cleanup tasks or post-processing."},"aliases":{"default":[],"description":"A list of aliases for the command. These aliases can be used to invoke the command with a different name.","items":{"type":"string"},"title":"Aliases","type":"array"},"name":{"default":"","description":"The name of the command. This is generally derived from the key in the `commands` section of the manifest, but can be explicitly set here.","title":"Name","type":"string"},"config":{"anyOf":[{"$ref":"#/$defs/CommandConfig"},{"type":"null"}],"default":null,"description":"An optional `CommandConfig` object that provides additional configuration options for the command, such as context settings, help text customization, and visibility."}},"title":"Command","type":"object"},"CommandConfig":{"description":"Configuration options for a Cliffy command.","properties":{"context_settings":{"default":{},"description":"Arbitrary settings passed to Click's context. Useful for things\n        like overriding the default `max_content_width`.\n        See Click's documentation for more details:\n        https://click.palletsprojects.com/en/8.1.x/advanced/#context-settings","title":"Context Settings","type":"object"},"epilog":{"default":"","description":"Text displayed after the help message.","title":"Epilog","type":"string"},"short_help":{"default":"","description":"Short one-line help message displayed in help overviews.","title":"Short Help","type":"string"},"options_metavar":{"default":"[OPTIONS]","description":"Placeholder text displayed for options in help messages.","title":"Options Metavar","type":"string"},"add_help_option":{"default":true,"description":"Whether to add the `--help` option automatically.","title":"Add Help Option","type":"boolean"},"no_args_is_help":{"default":false,"description":"If True, invoking the command without any arguments displays the help message.","title":"No Args Is Help","type":"boolean"},"hidden":{"default":false,"description":"If True, the command is hidden from help messages and command lists.","title":"Hidden","type":"boolean"},"deprecated":{"default":false,"description":"If True, the command is marked as deprecated in help messages.","title":"Deprecated","type":"boolean"},"rich_help_panel":{"default":"","description":"Name of a Rich help panel to display after the default help. This is useful for\n        displaying more complex help information, such as tables or formatted text.\n        The content of the panel is defined using the `@rich_help` decorator.","title":"Rich Help Panel","type":"string"}},"title":"CommandConfig","type":"object"},"CommandParam":{"description":"Defines the structure of a command parameter. It is used\nwithin the `params` field of a `Command` object.\n\nBy default, parameters are treated as positional arguments. To specify an option, prefix the name with `--` to indicate flag.","properties":{"name":{"description":"Parameter name. Prefix with `--` to indicate an option.","title":"Name","type":"string"},"type":{"description":"Parameter type (e.g., 'str', 'int', 'bool', or a custom type defined in the manifest's 'types' section).","title":"Type","type":"string"},"default":{"default":null,"description":"Default parameter value.","title":"Default"},"help":{"default":"","description":"Parameter description.","title":"Help","type":"string"},"short":{"default":"","description":"Short option alias. i.e. '-v' for verbose.","title":"Short","type":"string"},"required":{"default":false,"description":"Whether the parameter is required.","title":"Required","type":"boolean"}},"required":["name","type"],"title":"CommandParam","type":"object"},"CommandTemplate":{"description":"Defines a reusable template for command definitions.  Templates allow you to define\ncommon parameters, pre-run/post-run scripts, and configuration options that can be\napplied to multiple commands.","properties":{"params":{"default":[],"description":"A list of parameters for the command template.  These parameters will be applied to any command that uses this template.","items":{"anyOf":[{"$ref":"#/$defs/CommandParam"},{"$ref":"#/$defs/SimpleCommandParam"},{"$ref":"#/$defs/GenericCommandParam"}]},"title":"Params","type":"array"},"pre_run":{"$ref":"#/$defs/PreRunBlock","default":"","description":"Script to run before the command's run and pre-run block. This script will be applied to any command that uses this template."},"post_run":{"$ref":"#/$defs/PostRunBlock","default":"","description":"Script to run after the command's run and post-run block. This script will be applied to any command that uses this template."},"config":{"anyOf":[{"$ref":"#/$defs/CommandConfig"},{"type":"null"}],"default":null,"description":"Additional configuration options for commands using this template. This allows customization of help text, context settings, and other Typer command parameters."}},"title":"CommandTemplate","type":"object"},"GenericCommandParam":{"title":"Generic Command Param\nGets appended to the command params signature.","type":"string"},"PostRunBlock":{"title":"Post-run Block","type":"string"},"PreRunBlock":{"title":"Pre-run Block","type":"string"},"RunBlock":{"description":"Command execution logic. Lines prefixed with '$' are treated as shell commands.","title":"Command Run Block","type":"string"},"RunBlockList":{"items":{"$ref":"#/$defs/RunBlock"},"title":"Run Block List\nList of Run Blocks executed in order.","type":"array"},"SimpleCommandParam":{"additionalProperties":{"type":"string"},"maxProperties":1,"minProperties":1,"title":"Simple Command Param\nBuild params with key as the param name and value as the type and default vals, i.e. `verbose: bool = typer.Option(...)`","type":"object"}},"additionalProperties":true,"properties":{"manifestVersion":{"default":"v3","title":"Manifestversion","type":"string"},"name":{"description":"The name of the CLI, used when invoking from command line.","title":"Name","type":"string"},"version":{"description":"CLI version","title":"Version","type":"string"},"help":{"default":"","description":"Brief description of the CLI","title":"Help","type":"string"},"requires":{"default":[],"description":"List of Python package dependencies for the CLI.Supports requirements specifier syntax.","items":{"type":"string"},"title":"Requires","type":"array"},"includes":{"default":[],"description":"List of external CLI manifests to include.Performs a deep merge of manifests sequentially in the order given to assemble a merged manifest. and finally, deep merges the merged manifest with this manifest.","items":{"type":"string"},"title":"Includes","type":"array"},"vars":{"additionalProperties":{"anyOf":[{"type":"string"},{"additionalProperties":{"type":"null"},"type":"object"}]},"description":"Mapping defining manifest variables that can be referenced in any other blocks. Environments variables can be used in this section with ${some_env_var} for dynamic parsing. Supports jinja2 formatted expressions as values. Interpolate defined vars in other blocks jinja2-styled {{ var_name }}.","title":"Vars","type":"object"},"imports":{"anyOf":[{"type":"string"},{"items":{"type":"string"},"type":"array"}],"default":[],"description":"String block or list of strings containing any module imports. These can be used to import any python modules that the CLI depends on.","title":"Imports"},"functions":{"anyOf":[{"type":"string"},{"items":{"type":"string"},"type":"array"}],"default":[],"description":"String block or list of helper function definitions. These functions should be defined as strings that can be executed by the Python interpreter.","title":"Functions"},"types":{"additionalProperties":{"type":"string"},"description":"A mapping containing any shared type definitions. These types can be referenced by name in the params section to provide type annotations for args and options defined in the params section.","title":"Types","type":"object"},"global_params":{"default":[],"description":"Parameters applied to all commands","items":{"anyOf":[{"$ref":"#/$defs/CommandParam"},{"$ref":"#/$defs/SimpleCommandParam"},{"$ref":"#/$defs/GenericCommandParam"}]},"title":"Global Params","type":"array"},"command_templates":{"additionalProperties":{"$ref":"#/$defs/CommandTemplate"},"description":"Reusable command templates","title":"Command Templates","type":"object"},"commands":{"additionalProperties":{"anyOf":[{"$ref":"#/$defs/Command"},{"$ref":"#/$defs/RunBlock"},{"$ref":"#/$defs/RunBlockList"}]},"description":"A mapping containing the command definitions for the CLI. Each command should have a unique key- which can be either a group command or nested subcommands. Nested subcommands are joined by '.' in between each level. Aliases for commands can be separated in the key by '|'. A special '(*)' wildcard can be used to spread the subcommand to all group-level commands","title":"Commands","type":"object"},"cli_options":{"description":"Additional CLI configuration options","title":"Cli Options","type":"object"},"tests":{"default":[],"description":"Test cases for commands","items":{"anyOf":[{"type":"string"},{"additionalProperties":{"type":"string"},"type":"object"}]},"title":"Tests","type":"array"}},"required":["name","version","commands"],"title":"CLIManifest","type":"object"}
\`\`\`

Due to a feature limitation, parent command cannot be triggered if they have subcommands. Do not write a group command definition for the parent if it has a subcommand.
```
