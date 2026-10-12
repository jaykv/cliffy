# Known issues

Behavior in cliffy 0.7.0 that differs from what you might expect, with the way around each. Every
item was reproduced against this release. The guides already recommend the forms that work; this
page explains why.

## Commands

### Some problems are only found by `cli validate` and `cli test`

Every command checks the scripts of a manifest and reports a syntax error with its command, line and
column. A problem that only shows when the generated code is imported is not found by `cli load`,
`cli render` or `cli build`: a type name that does not exist, or params that do not fit together in
one signature. The CLI is then loaded or built and fails when it is started.

**Do this instead:** run `cli validate` first. It imports the generated code and reports such a
problem against the command it comes from.

### `cli test` does not check shell steps

A `$` or `>` step that exits with an error does not fail the run. A step whose program does not
exist ends the run with an error message. See [Testing manifests](../guides/testing.md#things-to-know).

### Examples are shown for the CLI, not per command

`examples` belongs to the manifest. The generated CLI shows all of them at the end of its own
`--help`; the help of a single command has no examples section, because a command has no `examples`
key. With the Typer backend an example that contains an emoji code such as `:rocket:` is shown as
the emoji, like the rest of the help text.

### `cli remove` refuses when the launcher was changed

The launcher of a loaded CLI is only deleted while it is exactly the file cliffy wrote. After an
edit, or when another program replaced it, `cli remove` and `cli remove-all` remove nothing for that
CLI and exit with 1.

**Do this instead:** move or delete the file named in the message, then run `cli remove` again.

### A file can still appear between cliffy's check and its write

cliffy checks a launcher right before it replaces or deletes it, never follows a symbolic link and
creates a new launcher only when nothing has the name. Replacing or deleting an existing launcher
is a check followed by a rename or an unlink: a file that another process puts at exactly that path
in between is replaced or removed. This needs write access to the environment's `bin` directory at
that moment.

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
