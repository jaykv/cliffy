# Known issues

Behavior in cliffy 0.7.0 that differs from what you might expect, with the way around each. Every
item was reproduced against this release. The guides already recommend the forms that work; this
page explains why.

## Params

### Typer definitions written inline in a shorthand param are dropped

```yaml
params:
  - name: str = typer.Option("World", "--name", "-n", help="Name to greet")
```

Only `name: str` reaches the generated code, so `name` becomes a required positional argument and
the option, its default and its help text are lost.

**Do this instead:** define the param under `types` and refer to it, or quote the whole entry so
that it is a generic param. Both are shown in [Params and types](../guides/params.md#types).

### The manifest written by `cli init` without `--raw` does not run

The full template uses the inline form above together with a global param. The code generated from
it is not valid Python, so `cli run` and the loaded CLI fail with
`parameter without a default follows parameter with a default`. `cli validate` does not catch this.

**Do this instead:** start from `cli init mycli --raw`, or from a manifest in the
[Quickstart](../quickstart.md) or the [examples gallery](../reference/examples.md).

### Global params skip commands that have no params

`global_params` are added only to commands that declare at least one param, either their own or
through a template. A command without params that uses a global param in its script fails with
`NameError`.

**Do this instead:** give such a command a param or a template that has one.

## Commands

### `cli validate` does not check the generated code

It validates the YAML, the schema and the `requires`. A manifest can pass and still produce Python
that fails to import or run.

**Do this instead:** add a [`tests` section](../guides/testing.md) and run `cli test`, or call a
command with `cli run`.

### `cli test` exits with 0 when only some tests fail

The exit code is 1 only when every test fails. The progress counter also numbers shell steps, so it
can show `6 of 5`.

**Do this instead:** check for the final line `All tests passed!`, as shown in
[Testing manifests](../guides/testing.md#running-tests).

### `cli docs <name>` fails for a loaded CLI

Passing the name of a loaded CLI instead of a manifest path ends in a validation error.

**Do this instead:** pass the manifest path: `cli docs mycli.yaml`.

### `cli --version` shows the wrong number with the `rich` extra

When rich-click is installed, `cli --version` prints the version of rich-click.

**Do this instead:** run `pip show cliffy`.

## Manifests

### `manifestVersion` is ignored

Any value is accepted when a manifest file is loaded, including `v1` and `v2`. The key has no effect.

### Include paths depend on the working directory

Paths under `includes` are resolved from the directory you run `cli` in, not from the manifest's
directory. See [Includes and merging](../guides/includes.md).

### Vars cannot build on computed vars

A var whose value contains a Jinja expression is not resolved when it is used inside another var's
value. See [Vars and Jinja](../guides/vars-and-jinja.md#limits).

## Click backend

`use_click: true` supports fewer features than the default Typer backend: no short option names in
shorthand params, no `types`, no `config`, and no `cli test`. The details are in
[Click and Typer backends](../guides/backends.md#what-differs-from-typer).
