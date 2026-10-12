<!--
  GENERATED FILE - do not edit by hand.
  Source: scripts/docs.py. Regenerate with `make docs-generate`.
-->

# CLI reference

Installing cliffy adds two identical entry points, `cli` and `cliffy`. This page uses `cli`.
It is generated from the command definitions in `cliffy/cli.py` and `cliffy/ai.py`, so the
arguments, options and defaults below are the ones the installed version accepts.

```text
cli [OPTIONS] COMMAND [ARGS]...
```

## Commands at a glance

| Command | Description |
|---|---|
| [`cli ai`](#cli-ai) | AI-powered commands. Requires the `ai` extra: pip install 'cliffy[ai]' |
| [`cli blueprint`](#cli-blueprint) | Work with blueprints: custom YAML specs that map onto a CLI |
| [`cli build`](#cli-build) | Build a CLI manifest or a loaded CLI into a single file to hand to someone else |
| [`cli dev`](#cli-dev) | Start hot-reloader for a manifest for active development. |
| [`cli docs`](#cli-docs) | Generate documentation for a CLI |
| [`cli info`](#cli-info) | Display CLI info |
| [`cli init`](#cli-init) | Generate a CLI manifest template |
| [`cli list`](#cli-list) | List all CLIs loaded |
| [`cli load`](#cli-load) | Load CLI for given manifest(s) |
| [`cli remove`](#cli-remove) | Remove a loaded CLI by name |
| [`cli remove-all`](#cli-remove-all) | Remove all loaded CLIs |
| [`cli render`](#cli-render) | Render the CLI manifest generation as code |
| [`cli run`](#cli-run) | Run CLI for a manifest |
| [`cli test`](#cli-test) | Run tests defined in a manifest |
| [`cli update`](#cli-update) | Reloads CLI by name |
| [`cli validate`](#cli-validate) | Validate the syntax and structure of a CLI manifest |

## Global options

| Option | Description |
|---|---|
| `--version` | Print the version and exit. |
| `--aliases` | List the command aliases and exit. |
| `-h`, `--help` | Show help. Every command accepts this option. |

## Aliases

Aliases are hidden from `cli --help`. `cli --aliases` prints this list.

| Alias | Command |
|---|---|
| `cli ls` | [`cli list`](#cli-list) |
| `cli add` | [`cli load`](#cli-load) |
| `cli reload` | [`cli update`](#cli-update) |
| `cli rm` | [`cli remove`](#cli-remove) |
| `cli rm-all` | [`cli remove-all`](#cli-remove-all) |
| `cli rmall` | [`cli remove-all`](#cli-remove-all) |
| `cli blueprints` | [`cli blueprint list`](#cli-blueprint-list) |

## `cli ai`

AI-powered commands. Requires the `ai` extra: pip install 'cliffy[ai]'

```text
cli ai [OPTIONS] COMMAND [ARGS]...
```

Only available when the `ai` extra is installed (`pip install "cliffy[ai]"`). Both commands send the
manifest JSON schema to the model as part of the prompt and print token usage when they finish.

Model names use the pydantic-ai `provider:model` form, and the API key of that provider must be set in
the environment. Without `--model`, the `CLIFFY_AI_MODEL` environment variable is used, then a default
for the first provider that has an API key set. See [AI commands](../ai.md).

### `cli ai ask`

Ask a question about cliffy or a specific CLI manifest.

```text
cli ai ask [OPTIONS] PROMPT
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `PROMPT` | text | yes |  | Your question. |
| `--preview` | flag | no |  | Print the prompt instead of sending it. Needs no model. |
| `--max-tokens` | integer range | no |  | Maximum number of tokens in a model response. |
| `-m`, `--model` | text | no |  | Model to use, as `provider:model`. See https://pydantic.dev/docs/ai/models/overview/. Defaults to a model of the first provider with an API key set, else google:gemini-flash-latest. |
| `--cli` | file | no |  | Loaded CLI or manifest to include in the prompt as reference. |

`--preview` prints the prompt and exits without calling a model.

### `cli ai generate`

Generate a CLI manifest based on a description.

```text
cli ai generate [OPTIONS] CLI_NAME DESCRIPTION
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `CLI_NAME` | text | yes |  | Name of the CLI. The manifest is written to `<cli_name>.yaml`. |
| `DESCRIPTION` | text | yes |  | Plain-language description of the CLI you want. |
| `--preview` | flag | no |  | Print the prompt instead of sending it. Needs no model. |
| `--max-tokens` | integer range | no |  | Maximum number of tokens in a model response. |
| `-m`, `--model` | text | no |  | Model to use, as `provider:model`. See https://pydantic.dev/docs/ai/models/overview/. Defaults to a model of the first provider with an API key set, else google:gemini-flash-latest. |
| `--retries` | integer range | no | `2` | How often to send an invalid manifest back to the model to be fixed. |
| `-f`, `--force` | flag | no |  | Overwrite the manifest file if it exists. |
| `-o`, `--output-dir` | directory | no | `.` | Output directory |

The reply of the model is validated before the manifest is written, and sent back with the reason when
it is not a manifest cliffy can load. `--preview` prints the prompt and exits without calling a model.

## `cli blueprint`

Work with blueprints: custom YAML specs that map onto a CLI

```text
cli blueprint [OPTIONS] COMMAND [ARGS]...
```

A blueprint lets a YAML file use its own keys instead of `commands` and `params`, and maps them onto a
CLI. See [Blueprints](../blueprints.md).

### `cli blueprint list`

List the blueprints provided by installed packages

```text
cli blueprint list [OPTIONS]
```

Alias: `cli blueprints`

Lists the blueprints that installed packages register under the `cliffy.blueprints` entry point group.
A blueprint in a `.py` file or referenced as `module:Class` works without being listed.

```console
$ cli blueprint list
No blueprints installed. Use a .py file or module:Class reference, or install a blueprint package.
```

### `cli blueprint schema`

Print the JSON schema of a blueprint's spec, for validation and editor completion

```text
cli blueprint schema [OPTIONS] BLUEPRINT
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `BLUEPRINT` | text | yes |  | Blueprint reference: a `.py` file, `module:Class` or the name of an installed blueprint. |
| `-o`, `--output` | file | no |  | Write the schema to a file |

```console
$ cli blueprint schema examples/blueprints/tasks.py -o tasks.schema.json
+ tasks.schema.json
```

Point a `# yaml-language-server: $schema=` comment at the file to get completion and validation for
files written in the blueprint's spec.

## `cli build`

Build a CLI manifest or a loaded CLI into a single file to hand to someone else

```text
cli build [OPTIONS] [CLI_OR_MANIFESTS]...
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `[CLI_OR_MANIFESTS]...` | file | no |  | Manifest files (paths ending in `yaml`) or names of loaded CLIs. |
| `-t`, `--target` | `zipapp` \| `script` \| `native` | no | `zipapp` | What to build: `zipapp` is a zipapp with its dependencies bundled, which needs a compatible Python; `script` is a .py script that declares its dependencies inline, which needs uv or an environment with them; `native` is a compiled executable that brings its own Python and needs nothing installed (built with cargo and uv). |
| `-o`, `--output-dir` | directory | no |  | Output dir |
| `-p`, `--python` | text | no |  | Interpreter for the #! line of a zipapp or a script, added after the #!. [default: /usr/bin/env python3 for a zipapp, /usr/bin/env -S uv run --script for a script] |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

Builds one file to hand to someone else. `--target` chooses what kind:

| Target | What you get | Needs on the other machine |
|---|---|---|
| `zipapp` | `hello`, a [zipapp](https://docs.python.org/3/library/zipapp.html) built with [shiv](https://shiv.readthedocs.io/) that contains the dependencies | A compatible Python |
| `script` | `hello.py`, a script with its dependencies declared inline | [uv](https://docs.astral.sh/uv/), or Python with the dependencies installed |
| `native` | `hello`, a compiled executable with its own Python | Nothing |

Every target ships the generated CLI, the framework it imports (Typer, or rich-click with
`use_click`) and every package listed under `requires`. Without `--output-dir` the file is written
to the current directory.

```console
$ cli build hello.yaml -o dist
+ hello built 📦
  dist/hello (single file, needs Python >=3.10, 1.8 MB)
  run it with: ./dist/hello
$ ./dist/hello greet Ada
Hello, Ada!
$ cli build hello.yaml -o dist --target script
+ hello built 📦
  dist/hello.py (single file, needs uv, or Python >=3.11 with typer==0.27.3 installed, 1.3 kB)
  run it with: ./dist/hello.py (or: uv run dist/hello.py)
  uv downloads the dependencies the first time the script runs
```

The `native` target needs `cargo` and `uv` on the machine that builds. When a build fails, the
reason is printed and the exit code is `1`. With `--blueprint`, or a `blueprint:` key in the file,
the blueprint is applied at build time and is not needed to run the result.

See [Building executables](../guides/building.md).

## `cli dev`

Start hot-reloader for a manifest for active development.

Examples:

- cli dev examples/hello.yaml

- cli dev examples/hello.yaml --run-cli  -- -h

- cli dev examples/hello.yaml --run-cli python

```text
cli dev [OPTIONS] MANIFEST [RUN_CLI_ARGS]...
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `MANIFEST` | file | yes |  | Manifest file to watch. |
| `[RUN_CLI_ARGS]...` | text | no |  | Arguments for the generated CLI when `--run-cli` is set. |
| `--run-cli` | flag | no |  | If passed, runs CLI on each reload. Useful for syntax checks or testing command execution on each reload |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

Nothing is loaded when the command starts. The CLI is loaded the first time the file changes and
again on every later change. Stop with Ctrl+C.

With `--run-cli`, the remaining arguments are passed to the freshly generated CLI after each reload.
Put `--` before them when they include options.

See [Hot-reload dev loop](../guides/dev-loop.md).

## `cli docs`

Generate documentation for a CLI

```text
cli docs [OPTIONS] CLI_OR_MANIFEST
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `CLI_OR_MANIFEST` | file | yes |  | Manifest file (a path ending in `yaml`) or the name of a loaded CLI. |
| `-f`, `--format` | `md` \| `rst` \| `html` | no | `md` | Output format. |
| `-o`, `--output-dir` | directory | no |  | Output directory |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

Writes `<name>.md`, `<name>.rst` or `<name>.html` to the output directory, or to the current directory
when `--output-dir` is not given. The output directory must exist.

A loaded CLI is documented from the manifest path recorded by `cli load`.

See [Generating docs](../guides/generating-docs.md).

## `cli info`

Display CLI info

```text
cli info [OPTIONS] CLI_NAME
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `CLI_NAME` | text | yes |  | Name of a loaded CLI. |

Prints the name, version, requirements, blueprint (when one was used), age and stored manifest of a
loaded CLI.

## `cli init`

Generate a CLI manifest template

```text
cli init [OPTIONS] [CLI_NAME]
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `[CLI_NAME]` | text | no | `mycli` | Name of the CLI. The manifest is written to `<cli_name>.yaml`. |
| `--render` | flag | no |  | Print template to terminal directly |
| `--raw` | flag | no |  | Raw template without boilerplate helpers and examples. |
| `--json-schema` | flag | no |  | Write JSON schema (cliffy_schema.json) file to the current directory. Useful for development. |

```console
$ cli init mycli --raw
+ mycli.yaml
```

`--raw` writes a skeleton with every top-level key and no content. Without `--raw` the manifest is a
commented tour of the format with example commands.

`--json-schema` also writes `cliffy_schema.json` and adds a `# yaml-language-server` comment that points
at it. See [Editor setup](../guides/editor-setup.md).

## `cli list`

List all CLIs loaded

```text
cli list [OPTIONS]
```

Alias: `cli ls`

```console
$ cli list
┏━━━━━━━┳━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name  ┃ Version ┃ Age ┃ Manifest                ┃
┡━━━━━━━╇━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ hello │ 0.1.0   │ 5s  │ /home/ada/hello.yaml    │
└───────┴─────────┴─────┴─────────────────────────┘
```

## `cli load`

Load CLI for given manifest(s)

```text
cli load [OPTIONS] [MANIFESTS]...
```

Alias: `cli add`

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `[MANIFESTS]...` | file | no |  | One or more manifest files to load. |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

Loading does three things:

1. generates the CLI code and writes it to `cliffy/clis/<name>.py` inside the installed cliffy package,
2. writes a launcher script called `<name>` into the `bin` directory of the Python environment cliffy
   is installed in,
3. records the manifest path and contents so that `cli list`, `cli info` and `cli update` can find it.

The CLI is therefore available wherever that environment is active. Packages listed under `requires`
must already be installed, otherwise loading stops with `missing requirement`.

A file written in a [blueprint](../blueprints.md)'s spec is loaded the same way. The blueprint comes from
`--blueprint` or from the file's `blueprint:` key and is remembered, so `cli update` applies it again.

```console
$ cli load hello.yaml
✨ Generated hello CLI v0.1.0 ✨
$ hello -h
```

See [Hot-reload dev loop](../guides/dev-loop.md).

## `cli remove`

Remove a loaded CLI by name

```text
cli remove [OPTIONS] [CLI_NAMES]...
```

Alias: `cli rm`

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `[CLI_NAMES]...` | text | no |  | Names of loaded CLIs to remove. |

Deletes the launcher script, the generated module and the stored metadata.

```console
$ cli remove hello
~ hello removed 💥
```

## `cli remove-all`

Remove all loaded CLIs

```text
cli remove-all [OPTIONS]
```

Aliases: `cli rm-all`, `cli rmall`

## `cli render`

Render the CLI manifest generation as code

```text
cli render [OPTIONS] MANIFEST
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `MANIFEST` | file | yes |  | Manifest file to render. |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

Prints the Python module cliffy generates, without loading or running it. Use it to see exactly how
params, shell lines and templates are translated.

```console
$ cli render hello.yaml
```

## `cli run`

Run CLI for a manifest

```text
cli run [OPTIONS] MANIFEST [CLI_ARGS]...
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `MANIFEST` | file | yes |  | Manifest file to run. |
| `[CLI_ARGS]...` | text | no |  | Arguments passed to the generated CLI. Put `--` first when they include options. |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

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

## `cli test`

Run tests defined in a manifest

```text
cli test [OPTIONS] MANIFEST
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `MANIFEST` | file | yes |  | Manifest file whose `tests` section should run. |
| `-x`, `--exitfirst` | flag | no |  | exit instantly on first error or failed test. |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

Runs the `tests` section of a manifest and prints each command, its output and the result. The exit
code is `0` only when every test passes. It is `1` when a test fails or when the manifest has no tests.

See [Testing manifests](../guides/testing.md).

## `cli update`

Reloads CLI by name

```text
cli update [OPTIONS] [CLI_NAMES]...
```

Alias: `cli reload`

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `[CLI_NAMES]...` | text | no |  | Names of loaded CLIs to regenerate from their manifests. |

`update` re-reads the manifest from the path recorded by `cli load`, so it only works while the manifest
is still at that location.

```console
$ cli update hello
✨ Reloaded hello CLI v0.1.0 ✨
$ hello -h
```

## `cli validate`

Validate the syntax and structure of a CLI manifest

```text
cli validate [OPTIONS] MANIFEST
```

| Argument or option | Type | Required | Default | Description |
|---|---|---|---|---|
| `MANIFEST` | file | yes |  | Manifest file to validate. |
| `-b`, `--blueprint` | text | no |  | Blueprint that maps a custom YAML spec onto a CLI: a .py file, module:Class or an installed blueprint name. Overrides the `blueprint:` key of the file. |

Checks that the file is valid YAML, matches the manifest schema and that its `requires` are installed.
It does not check that the generated Python is valid; run `cli test` or `cli run` for that.

```console
$ cli validate hello.yaml
Manifest hello.yaml is valid
```
