# Commands, groups and aliases

Everything under `commands` becomes a command of your CLI. The key decides where the command lives
and what it is called; the value decides what it does.

The snippets on this page come from one manifest, shown in full [at the end](#the-complete-example).

## Three ways to write a command

```yaml
--8<-- "docs/snippets/commands.yaml:forms"
```

Use the short forms for one-liners and the mapping when you need `help`, `params` or anything else.
The keys of the mapping are listed in the [manifest reference](../reference/manifest.md#command).

```console
$ cli run commands.yaml ping
pong
$ cli run commands.yaml greet
Welcome, friend!
```

Command names may contain letters, digits, `-` and `_`.

## Groups

A dot in the key puts the command in a group. Groups are created as needed and can be nested.

```yaml
--8<-- "docs/snippets/commands.yaml:groups"
```

```console
$ cli run commands.yaml orders create book
created order for book
$ cli run commands.yaml stock warehouse count
42 items
$ cli run commands.yaml -- orders --help
...
╭─ Commands ─────────────────────────────────────────────────────────────────╮
│ create  Create an order                                                    │
│ ship    Ship an order                                                      │
│ list    List all orders                                                    │
╰────────────────────────────────────────────────────────────────────────────╯
```

To describe a group, add an entry with the group's name that has `help` and no `run`, like `orders`
above. A name is either a group or a command: if `orders` had a `run` script while `orders.create`
exists, the group would take the name and the script could not be reached.

## Aliases

```yaml
--8<-- "docs/snippets/commands.yaml:aliases"
```

- `|` in the key adds aliases to the last part of the name: `customers.add|new` gives
  `customers add` and `customers new`.
- The `aliases` list does the same from inside the command.

Aliases are hidden from `--help`. When a manifest defines aliases in its keys, the CLI gets an
`--aliases` option that lists them:

```console
$ cli run commands.yaml -- --aliases

Command             Aliases
--------            --------
customers.add       new
```

## One command for every group

A key that starts with `(*)` is added to every group. Inside that command, `{(*)}` is replaced with
the group's name, in `help`, `run`, `pre_run`, `post_run` and params.

```yaml
--8<-- "docs/snippets/commands.yaml:wildcard"
```

```console
$ cli run commands.yaml orders list
listing 10 orders
$ cli run commands.yaml -- customers list -l 3
listing 3 customers
```

## Run scripts

`run` is Python. Write it as a block (`run: |`) or as a list of lines. Lines that start with `$` are
shell commands, described in [Shell commands](shell-commands.md).

Two hooks wrap the script. `pre_run` runs before `run` and `post_run` after it, in the same function,
so all three share variables.

```yaml
--8<-- "docs/snippets/commands.yaml:hooks"
```

```console
$ cli run commands.yaml deploy
1. pre_run
2. run
3. post_run
```

Hooks are most useful together with [command templates](templates-and-global-params.md), which let
several commands share them.

To stop a command with an exit code, raise `typer.Exit`:

```yaml
run: |
  if not ready:
      print("not ready")
      raise typer.Exit(code=1)
```

## Help text

`help` on a command is shown in the command list and at the top of the command's own `--help`.
Because `run` is the body of a Python function, a docstring on its first line works as well:

```yaml
--8<-- "docs/snippets/commands.yaml:docstring"
```

## Command settings

`config` passes extra settings to Typer for one command.

```yaml
--8<-- "docs/snippets/commands.yaml:config"
```

| Key | Effect |
|---|---|
| `hidden` | Leave the command out of `--help`. |
| `deprecated` | Mark the command as deprecated and print a warning when it runs. |
| `epilog` | Text shown at the end of the command's help. |
| `short_help` | Text for the command list, when it should differ from `help`. |
| `no_args_is_help` | Show help when the command is called without arguments. |
| `context_settings` | Click context settings, for example `help_option_names`. |

All keys are in the [manifest reference](../reference/manifest.md#commandconfig).

## The complete example

```yaml title="commands.yaml"
--8<-- "docs/snippets/commands.yaml"
```
