# Known issues

Behavior in cliffy 0.7.0 that differs from what you might expect, with the way around each. Every
item was reproduced against this release. The guides already recommend the forms that work; this
page explains why.

## Commands

### Only `cli validate` and `cli test` check the generated code

`cli load`, `cli render` and `cli build` write or print the generated Python without compiling it. A
manifest whose code does not import can be loaded, and fails when the CLI is started.

**Do this instead:** run `cli validate` first. It compiles and imports the generated code and reports
problems against the command they come from.

### Some manifest errors are shown as a Python traceback

A problem that is found while the code is generated (a command or param name that cannot become a
Python name, an unknown `template`, a Typer definition used with `use_click`) ends `cli load`,
`cli render`, `cli run` and `cli test` with a traceback. The last line names the command:

```text
ValueError: commands.pack: Invalid param name: --from. A param becomes a Python variable, ...
```

**Do this instead:** run `cli validate`, which prints the same message without the traceback.

### A `run` script with an unclosed bracket or quote is dropped

Shell lines are translated before the code is generated. When a script cannot be split into tokens,
for example `print((`, the translation returns nothing. With Typer, `cli validate` then reports an
`IndentationError` for the command. With `use_click` the command is generated without a body and
silently does nothing.

**Do this instead:** if a command prints nothing, look at its function in `cli render`.

### `cli test` does not check shell steps

A `$` or `>` step that exits with an error does not fail the run, and a step whose program does not
exist ends the run with a traceback. See [Testing manifests](../guides/testing.md#things-to-know).

### `cli init` without `--raw` rejects names with a hyphen

`cli init my-cli --raw` works, `cli init my-cli` stops with `CLI name must be a valid Python
identifier`.

**Do this instead:** create the manifest with a name such as `my_cli` and change `name:` afterwards.

## Manifests

### Includes fall back to the working directory

An include path is looked up next to the including manifest first. When it is not found there, it is
looked up in the directory `cli` is run from, so the same manifest can pick up a different file
depending on where you are.

**Do this instead:** keep include files next to (or below) the manifest that lists them.

### A full Typer definition in `types` replaces the param's own settings

A `types` entry with `typer.Option(...)` or `typer.Argument(...)` is the complete definition. A
default, `help` or `short` written on a param that uses it is ignored. Plain types such as
`Count: int` do not have this effect. See [Params and types](../guides/params.md#types).

## Click backend

`use_click: true` supports every manifest feature. Generic params and full definitions in `types`
are written as Click decorators instead of Typer expressions. The details are in
[Click and Typer backends](../guides/backends.md#what-differs-from-typer).
