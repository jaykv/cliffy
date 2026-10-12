<!--
  GENERATED FILE - do not edit by hand.
  Source: scripts/docs.py. Regenerate with `make docs-generate`.
-->

# Examples gallery

The manifests in the [`examples/`](https://github.com/jaykv/cliffy/tree/main/examples) directory of the
repository. Each entry shows the file as it is in the repository. The code cliffy generates for them is
committed next to them in
[`examples/generated/`](https://github.com/jaykv/cliffy/tree/main/examples/generated).

To try one, clone the repository and run the command shown from its root.

Files written in a custom spec, and the blueprints that turn them into CLIs, are in
[`examples/blueprints/`](https://github.com/jaykv/cliffy/tree/main/examples/blueprints) and
described in [Blueprints](../blueprints.md#examples).

| Example | Backend | Requires | Has tests |
|---|---|---|---|
| [hello.yaml](#hello) | Typer | nothing | yes |
| [nested-cli.yaml](#nested-cli) | Typer | nothing | no |
| [town.yaml](#town) | Typer | nothing | no |
| [template.yaml](#template) | Typer | nothing | no |
| [environ.yaml](#environ) | Typer | nothing | no |
| [db.yaml](#db) | Typer | `rich` | no |
| [penv.yaml](#penv) | Typer | nothing | no |
| [pydev.yaml](#pydev) | Typer | nothing | no |
| [taskmaster.yaml](#taskmaster) | Typer | `tabulate>=0.9.0` | yes |
| [todo.yaml](#todo) | Typer | `tabulate`, `rich` | no |
| [requires.yaml](#requires) | Typer | `requests >= 2.30.0`, `six < 1.0.0` | no |
| [callbacks.yaml](#callbacks) | Typer | nothing | yes |
| [click_hello.yaml](#clickhello) | Click | nothing | no |
| [aiprompt.yaml](#aiprompt) | Typer | `openai>=1.0.0`, `rich>=13.0.0`, `keyring>=24.0.0` | no |

## hello

The smallest useful manifest: one shell command, one Python command and a `tests` section.

```console
$ cli run examples/hello.yaml python
```

??? example "examples/hello.yaml"

    ```yaml
    --8<-- "examples/hello.yaml"
    ```

## nested-cli

Command groups nested two levels deep with dotted keys.

```console
$ cli run examples/nested-cli.yaml group1 subgroup command1
```

??? example "examples/nested-cli.yaml"

    ```yaml
    --8<-- "examples/nested-cli.yaml"
    ```

## town

A larger CLI: groups with help text, shared `types`, short option aliases, command aliases and a `(*).list` command that is added to every group.

```console
$ cli run examples/town.yaml land list
```

??? example "examples/town.yaml"

    ```yaml
    --8<-- "examples/town.yaml"
    ```

## template

A command template that gives two commands the same params, a run script written as a list, and per-command `config`.

```console
$ cli run examples/template.yaml -- debug one --local-arg-2 two
```

??? example "examples/template.yaml"

    ```yaml
    --8<-- "examples/template.yaml"
    ```

## environ

Environment variables read when the manifest is loaded (`vars` with `env`) and when a command runs.

```console
$ cli run examples/environ.yaml hello
```

??? example "examples/environ.yaml"

    ```yaml
    --8<-- "examples/environ.yaml"
    ```

## db

Prompting options defined in `types`, YAML anchors to share params, `pre_run`, command aliases and `cli_options`.

```console
$ cli run examples/db.yaml -- mk --name demo
```

??? example "examples/db.yaml"

    ```yaml
    --8<-- "examples/db.yaml"
    ```

## penv

A virtualenv manager: `vars` holding Python expressions, helper `functions` and shell lines that interpolate Python values with `f{...}`.

```console
$ cli run examples/penv.yaml -- --help
```

??? example "examples/penv.yaml"

    ```yaml
    --8<-- "examples/penv.yaml"
    ```

## pydev

Developer chores as run-script lists that mix shell and Python lines, with helper functions.

```console
$ cli run examples/pydev.yaml -- --help
```

??? example "examples/pydev.yaml"

    ```yaml
    --8<-- "examples/pydev.yaml"
    ```

## taskmaster

A task manager with JSON storage, a `vars` placeholder used inside functions, shared `types`, nested groups and a full `tests` section.

```console
$ cli test examples/taskmaster.yaml
```

??? example "examples/taskmaster.yaml"

    ```yaml
    --8<-- "examples/taskmaster.yaml"
    ```

## todo

A sqlite-backed todo list that depends on `tabulate` and `rich`.

```console
$ cli run examples/todo.yaml -- --help
```

??? example "examples/todo.yaml"

    ```yaml
    --8<-- "examples/todo.yaml"
    ```

## requires

Version specifiers in `requires`. Loading fails on purpose unless `requests>=2.30.0` and `six<1.0.0` are installed, which is what the test suite checks.

```console
$ cli validate examples/requires.yaml
```

??? example "examples/requires.yaml"

    ```yaml
    --8<-- "examples/requires.yaml"
    ```

## callbacks

Callbacks: code that runs before every command of the CLI or of one group, with params that become options of the CLI itself and access to the context as `ctx`.

```console
$ cli run examples/callbacks.yaml -- --verbose db migrate
```

??? example "examples/callbacks.yaml"

    ```yaml
    --8<-- "examples/callbacks.yaml"
    ```

## clickhello

The Click backend (`use_click: true`) with a command alias. Needs the `rich` extra.

```console
$ cli run examples/click_hello.yaml hello
```

??? example "examples/click_hello.yaml"

    ```yaml
    --8<-- "examples/click_hello.yaml"
    ```

## aiprompt

An OpenAI client written by an LLM: explicit params with help text, `global_params` and nested groups. Needs `openai`, `rich` and `keyring`.

```console
$ cli render examples/aiprompt.yaml
```

??? example "examples/aiprompt.yaml"

    ```yaml
    --8<-- "examples/aiprompt.yaml"
    ```
