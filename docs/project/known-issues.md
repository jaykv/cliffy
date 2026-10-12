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
