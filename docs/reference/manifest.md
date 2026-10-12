<!--
  GENERATED FILE - do not edit by hand.
  Source: scripts/docs.py. Regenerate with `make docs-generate`.
-->

# Manifest reference

Every key a manifest accepts. The tables are generated from the pydantic models in
`cliffy/manifest.py`, the same models that produce the
[JSON schema](https://github.com/jaykv/cliffy/blob/main/examples/cliffy_schema.json) used for
[editor completion](../guides/editor-setup.md). The notes under each table are written by hand.

## Top-level keys

The top level of a manifest file.

| Key | Type | Default | Description |
|---|---|---|---|
| `manifestVersion` | string | `"v3"` | Manifest schema version. `v3` is the only version. |
| `name` | string | **required** | The name of the CLI, used when invoking from command line. |
| `version` | string | **required** | CLI version |
| `help` | string | `""` | Brief description of the CLI |
| `use_click` | boolean | `false` | Generate CLI to Click instead of Typer |
| `requires` | list of strings | `[]` | Python packages the CLI needs, as requirement specifiers such as `rich` or `tabulate>=0.9.0`. Checked when the manifest is loaded and bundled by `cli build`. |
| `includes` | list of strings | `[]` | Paths of other manifest files to merge into this one. Keys set in this manifest win over included ones; lists are combined. |
| `vars` | mapping of name to (string or `{expression}`) | `{}` | Variables for the manifest. Each one can be used anywhere in the file as `{{ name }}` and is also defined as a module-level Python variable in the generated CLI. Values are Jinja2 templates; `env` gives access to environment variables. |
| `imports` | string or list of strings | `[]` | String block or list of strings containing any module imports. These can be used to import any python modules that the CLI depends on. |
| `functions` | string or list of strings | `[]` | String block or list of helper function definitions. These functions should be defined as strings that can be executed by the Python interpreter. |
| `types` | mapping of name to string | `{}` | A mapping containing any shared type definitions. These types can be referenced by name in the params section to provide type annotations for args and options defined in the params section. |
| `global_params` | list of [params](#params) | `[]` | Parameters applied to all commands |
| `command_templates` | mapping of name to [CommandTemplate](#commandtemplate) | `{}` | Reusable command templates |
| `commands` | mapping of name to ([Command](#command), string or list of strings) or list of [Command](#command) | **required** | The commands of the CLI, keyed by name. In a key, `.` separates groups, `\|` separates aliases and a leading `(*)` adds the command to every group. |
| `cli_options` | mapping | `{}` | Additional CLI configuration options |
| `tests` | list of (string or mapping of name to string) | `[]` | Test cases for commands |
| `examples` | list of (string or [Example](#example)) | `[]` | Example command usages to display in generated CLI docs. |

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

## Command

Defines a single command within the CLI. It specifies the command's execution logic, parameters, and configuration.

| Key | Type | Default | Description |
|---|---|---|---|
| `run` | string or list of strings | `""` | The script to run. A string, or a list of strings that are joined with newlines. Lines starting with `$` or `>` are shell commands. |
| `help` | string | `""` | A description of the command, displayed in the help output. |
| `params` | list of [params](#params) | `[]` | The parameters of the command. See [Params](#params) for the three accepted forms. |
| `template` | string | `""` | A reference to a command template defined in the `command_templates` section of the manifest. This allows for reusable command definitions. |
| `pre_run` | string | `""` | Script to run before the command's run block. This can be used for setup tasks or preconditions. |
| `post_run` | string | `""` | Script to run after the command's run block. This can be used for cleanup tasks or post-processing. |
| `aliases` | list of strings | `[]` | A list of aliases for the command. These aliases can be used to invoke the command with a different name. |
| `name` | string | `""` | The name of the command. This is generally derived from the key in the `commands` section of the manifest, but can be explicitly set here. |
| `config` | [CommandConfig](#commandconfig) or null | `null` | An optional `CommandConfig` object that provides additional configuration options for the command, such as context settings, help text customization, and visibility. |

A command value can also be just a string or a list of strings, which is shorthand for a mapping with
only `run`.

The key of the command carries meaning: `.` separates groups (`db.create`), `|` separates aliases
(`delete|rm`) and a leading `(*)` adds the command to every group. See
[Commands, groups and aliases](../guides/commands.md).

A command that has `help` and no `run`, and whose key is the name of a group, sets the help text of
that group.

## Params

Every entry of a `params` list (on a command, a template or `global_params`) takes one of three forms.

### Shorthand

A one-key mapping: the key is the name, the value is the type.

| Part | Meaning | Example |
|---|---|---|
| `name` | Positional argument | `source: str` |
| `--name` | Option | `--count: int` |
| `--name\|-n` | Option with a short alias | `--count\|-c: int` |
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

## CommandParam

Defines the structure of a command parameter. It is used within the `params` field of a `Command` object. By default, parameters are treated as positional arguments. To specify an option, prefix the name with `--` to indicate flag.

| Key | Type | Default | Description |
|---|---|---|---|
| `name` | string | **required** | Parameter name. Prefix with `--` to indicate an option. |
| `type` | string | **required** | Parameter type (e.g., 'str', 'int', 'bool', or a custom type defined in the manifest's 'types' section). |
| `default` | any | `null` | Default parameter value. |
| `help` | string | `""` | Parameter description. |
| `short` | string | `""` | Short option alias. i.e. '-v' for verbose. |
| `required` | boolean | `false` | Whether the parameter is required. |

This is the explicit form. `short` is written with its dash (`-w`). With the Typer backend a `str`
default is quoted for you; other defaults are emitted as written.

## CommandTemplate

Defines a reusable template for command definitions. Templates allow you to define common parameters, pre-run/post-run scripts, and configuration options that can be applied to multiple commands.

| Key | Type | Default | Description |
|---|---|---|---|
| `params` | list of [params](#params) | `[]` | A list of parameters for the command template. These parameters will be applied to any command that uses this template. |
| `pre_run` | string | `""` | Script to run before the command's run and pre-run block. This script will be applied to any command that uses this template. |
| `post_run` | string | `""` | Script to run after the command's run and post-run block. This script will be applied to any command that uses this template. |
| `config` | [CommandConfig](#commandconfig) or null | `null` | Additional configuration options for commands using this template. This allows customization of help text, context settings, and other Typer command parameters. |

Template `params` are placed before the command's own params. Scripts run in this order: template
`pre_run`, command `pre_run`, command `run`, command `post_run`, template `post_run`. `config` values
from the command override the template's. See
[Command templates and global params](../guides/templates-and-global-params.md).

## CommandConfig

Configuration options for a Cliffy command.

| Key | Type | Default | Description |
|---|---|---|---|
| `context_settings` | mapping | `{}` | Settings passed to the Click context of the command, for example `help_option_names` or `max_content_width`. |
| `epilog` | string | `""` | Text displayed after the help message. |
| `short_help` | string | `""` | Short one-line help message displayed in help overviews. |
| `options_metavar` | string | `"[OPTIONS]"` | Placeholder text displayed for options in help messages. |
| `add_help_option` | boolean | `true` | Whether to add the `--help` option automatically. |
| `no_args_is_help` | boolean | `false` | If True, invoking the command without any arguments displays the help message. |
| `hidden` | boolean | `false` | If True, the command is hidden from help messages and command lists. |
| `deprecated` | boolean | `false` | If True, the command is marked as deprecated in help messages. |
| `rich_help_panel` | string | `""` | Name of the panel this command is listed under in rich help output. |

Only the keys you set are passed on, as keyword arguments of Typer's `command()`. The Click backend
ignores `config`.

## Example

| Key | Type | Default | Description |
|---|---|---|---|
| `command` | string | **required** | The command line to show. |
| `description` | string or null | `null` | A sentence describing what the command does. |

`examples` entries are only used by [`cli docs`](../guides/generating-docs.md). An entry can also be a
plain string, which is shown without a description.

## Include files

Special model specifically to define the allowed named objects that can be merged with other manifests.

| Key | Type | Default | Description |
|---|---|---|---|
| `requires` | list of strings | `[]` | Merged into the `requires` of the including manifest. |
| `commands` | mapping of name to ([Command](#command), string or list of strings) | `{}` | Merged into the `commands` of the including manifest. |
| `vars` | mapping of name to (string or `{expression}`) | `{}` | Merged into `vars`. Available as Python variables, not as `{{ }}` placeholders. |
| `imports` | string or list of strings | `[]` | Merged into `imports`. |
| `functions` | list of strings | `[]` | Merged into `functions`. Must be a list here. |
| `types` | mapping of name to string | `{}` | Merged into `types`. |
| `cli_options` | mapping of name to string | `{}` | Merged into `cli_options`. |
| `tests` | list of (string or mapping of name to string) | `[]` | Appended to `tests`. |

Files listed under `includes` are validated against this smaller model. Paths are resolved relative to
the directory you run `cli` from. See [Includes and merging](../guides/includes.md).
