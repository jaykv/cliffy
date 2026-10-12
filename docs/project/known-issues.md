# Known issues

Behavior in cliffy 0.7.0 that differs from what you might expect, with the way around each. Every
item was reproduced against this release. The guides already recommend the forms that work; this
page explains why.

## Commands

### `cli validate` does not check the generated code

It validates the YAML, the schema and the `requires`. A manifest can pass and still produce Python
that fails to import or run.

**Do this instead:** add a [`tests` section](../guides/testing.md) and run `cli test`, or call a
command with `cli run`.

### The `cli test` counter can exceed the total

The progress counter also numbers shell steps, so it can show `6 of 5`. The final line and the exit
code are what count; see [Testing manifests](../guides/testing.md#running-tests).

### `cli --version` shows the wrong number with the `rich` extra

When rich-click is installed, `cli --version` prints the version of rich-click.

**Do this instead:** run `pip show cliffy`.

## Manifests

### `manifestVersion` is ignored

Any value is accepted when a manifest file is loaded, including `v1` and `v2`. The key has no effect.

### Vars cannot build on computed vars

A var whose value contains a Jinja expression is not resolved when it is used inside another var's
value. See [Vars and Jinja](../guides/vars-and-jinja.md#limits).

## Click backend

`use_click: true` supports fewer features than the default Typer backend: no `types` and no `config`.
The details are in
[Click and Typer backends](../guides/backends.md#what-differs-from-typer).
