# CLI Manifest Schema

This document describes the schema for the CLI manifest, focusing on the `Command` model and its relationship with `CommandConfig`.

## CLIManifest

The `CLIManifest` model defines the structure of a CLI manifest file. It includes fields for the CLI's name, version, dependencies, commands, and other configuration options.

### Fields

- `manifestVersion`: The version of the manifest schema.
- `name`: The name of the CLI, used when invoking from the command line.
- `version`: The CLI version.
- `help`: A brief description of the CLI.
- `requires`: A list of Python package dependencies for the CLI. Supports requirements specifier syntax.
- `includes`: A list of external CLI manifests to include. Performs a deep merge of manifests sequentially in the order given to assemble a merged manifest, and finally, deep merges the merged manifest with this manifest.
- `vars`: A mapping defining manifest variables that can be referenced in any other blocks. Environments variables can be used in this section with `${some_env_var}` for dynamic parsing. Supports jinja2 formatted expressions as values. Interpolate defined vars in other blocks jinja2-styled `{{ var_name }}`.
- `imports`: A string block or list of strings containing any module imports. These can be used to import any python modules that the CLI depends on.
- `functions`: A list of helper function definitions. These functions should be defined as strings that can be executed by the Python interpreter.
- `types`: A mapping containing any shared type definitions. These types can be referenced by name in the args section to provide type annotations for params and options defined in the args section.
- `global_args`: Arguments applied to all commands.
- `command_templates`: Reusable command templates.
- `commands`: A mapping containing the command definitions for the CLI. Each command should have a unique key- which can be either a group command or nested subcommands. Nested subcommands are joined by '.' in between each level. Aliases for commands can be separated in the key by '|'. A special '(*)' wildcard can be used to spread the subcommand to all group-level commands.
- `cli_options`: Additional CLI configuration options.
- `tests`: Test cases for commands.

## Command

The `Command` model defines a single command within the CLI. It specifies the command's execution logic, arguments, and configuration.

### Fields

- `run`: The command's execution logic, which can be a string or a list of strings.
- `help`: A description of the command.
- `args`: A list of arguments for the command. Each argument can be defined as a dictionary, a `CommandArg` object, or a string. Types can be referenced inline using `typer.Option` and `typer.Argument`.
- `template`: A reference to a command template.
- `pre_run`: A script to run before the command.
- `post_run`: A script to run after the command.
- `aliases`: A list of aliases for the command.
- `name`: The name of the command.
- `config`: An optional `CommandConfig` object that provides additional configuration for the command.

### CommandArg

The `CommandArg` model defines the structure of a command argument.

#### Fields

- `name`: The name of the argument.
- `kind`: The kind of argument, which can be either "Option" or "Argument".
- `type`: The type of the argument. This corresponds to Typer's type annotations, such as `str`, `int`, `bool`, or custom types defined in the `types` section of the manifest.
- `default`: The default value of the argument.
- `help`: A description of the argument.
- `short`: A short alias for the argument.
- `required`: Whether the argument is required.

## CommandConfig

The `CommandConfig` model provides additional configuration options for a command.

### Fields

These directly correlate with params accepted by Typer `@app.command()`

- `context_settings`: Additional context settings for the command.
- `epilog`: Text to display after the help message.
- `short_help`: A short description of the command.
- `options_metavar`: The metavar to use for options in the help message.
- `add_help_option`: Whether to add a help option to the command.
- `no_args_is_help`: Whether to display the help message if no arguments are provided.
- `hidden`: Whether to hide the command from the help message.
- `deprecated`: Whether the command is deprecated.
- `rich_help_panel`: An optional panel name for rich help output.


For a deeper dive, check out the [manifest.py](https://github.com/jaykv/cliffy/blob/main/cliffy/manifest.py).