# Params and types

Params are the arguments and options of a command. Inside `run` they are ordinary Python variables.
A `params` list accepts three forms, and you can mix them in one command.

| Form | Looks like | Use it when |
|---|---|---|
| [Shorthand](#shorthand) | `- name: str!` | You want the shortest syntax. |
| [Explicit](#explicit) | `- name: image` and more keys | You want help text. |
| [Generic](#generic) | `- 'path: str = typer.Argument(...)'` | You need the full Typer API for one param. |

To reuse one definition across commands, give it a name under [`types`](#types).

## Shorthand

Each entry is `name: type`.

```yaml
--8<-- "docs/snippets/params.yaml:shorthand"
```

| You write | You get |
|---|---|
| `source: str!` | A required positional argument. |
| `target: str = "out.txt"` | An optional argument with a default. |
| `label: str` | An optional argument that is `None` when omitted. |
| `--count|-c: int = 1` | The option `--count` with the short form `-c`. |
| `--force|-f: bool = False` | A flag. `force` is `True` when `--force` or `-f` is passed. |
| `--owner: str!` | A required option. |
| `--dry-run: bool = False` | An option whose variable is `dry_run`. |

Rules:

- A name that starts with `--` is an option. Anything else is a positional argument.
- `!` after the type makes the param required.
- The text after `=` is a Python expression, so string defaults need quotes: `str = "out.txt"`.
- Hyphens in a name become underscores in the variable.
- Positional arguments are read from the command line in the order you list them, so put required
  ones first.

```console
$ cli run params.yaml -- copy a.txt --owner me
a.txt out.txt None 1 False me False
$ cli run params.yaml -- copy a.txt b.txt c -c 3 -f --owner me --dry-run
a.txt b.txt c 3 True me True
```

!!! note "Boolean options without a short form"
    `--dry-run: bool = False` is generated without explicit option names, so Typer also adds the
    negative form `--no-dry-run`. Options declared with a short form, such as `--force|-f`, get
    only the names you wrote.

## Explicit

Each entry is a mapping. This is the only form with a `help` key.

```yaml
--8<-- "docs/snippets/params.yaml:explicit"
```

| Key | Meaning |
|---|---|
| `name` | Param name. Start it with `--` to make an option; without it the param is a positional argument. |
| `type` | A Python type such as `str`, `int`, `float`, `bool`, or a name from `types`. |
| `default` | Default value. String defaults are quoted for you when `type` is `str`. |
| `help` | Text shown in `--help`. |
| `short` | Short option name including the dash, such as `-w`. Options only. |
| `required` | `true` to make the param required. |

```console
$ cli run params.yaml -- resize cat.jpg -w 100 --format gif
cat.jpg 100 gif
```

## Types

`types` gives a name to a type or to a complete Typer parameter definition. Use the name wherever a
type is expected, in shorthand or explicit params.

```yaml
types:
  Level: int = typer.Option(1, "--level", "-l", min=1, max=5, help="Compression level")
  Source: str = typer.Argument(..., help="File to read")
```

```yaml
--8<-- "docs/snippets/params.yaml:types"
```

A complete definition is everything that follows the param name in a Python signature: the type, then
`typer.Argument(...)` or `typer.Option(...)`. This gives you help text, validation (`min`, `max`),
prompts (`prompt=True`), environment variables (`envvar="NAME"`) and the rest of the
[Typer parameter API](https://typer.tiangolo.com/tutorial/options/). It replaces everything the param
entry says except its name, so a default or `help` written next to it is not used.

A plain type is an alias:

```yaml
types:
  Count: int = 1

commands:
  repeat:
    params:
      - --times: Count       # the option --times, an int, default 1
      - --retries: Count = 3 # a default on the param wins
    run: print(times, retries)
```

The param keeps what its own entry says: `--times` is an option because of its name, and an explicit
param keeps its `help`. Plain types work with both backends.

```console
$ cli run params.yaml -- pack data.csv
data.csv 1
$ cli run params.yaml -- pack data.csv -l 9
╭─ Error ────────────────────────────────────────────────────────────────────╮
│ Invalid value for '--level' / '-l': 9 is not in the range 1<=x<=5.         │
╰────────────────────────────────────────────────────────────────────────────╯
```

## Generic

A plain string is copied into the function signature exactly as written. Quote the whole entry so
that YAML reads it as a string.

```yaml
--8<-- "docs/snippets/params.yaml:generic"
```

!!! tip "A Typer definition also works in a shorthand entry"
    `- name: str = typer.Option("World", "--name")` is passed through as written. Use `types` when
    several commands share the definition.

## Where else params appear

- `global_params` and `command_templates.<name>.params` accept the same three forms. See
  [Command templates and global params](templates-and-global-params.md).
- With `use_click: true`, params are translated to Click decorators. Shorthand and explicit params
  mean the same; generic params and full definitions in `types` are written as Click decorators. See
  [Click and Typer backends](backends.md).

## The complete example

```yaml title="params.yaml"
--8<-- "docs/snippets/params.yaml"
```
