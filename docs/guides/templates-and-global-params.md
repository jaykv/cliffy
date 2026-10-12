# Command templates and global params

Two features keep a manifest free of repetition. **Global params** add the same params to your
commands. **Command templates** bundle params, hooks and settings under a name that commands opt
into.

## Global params

`global_params` is a list of [params](params.md), in any of the three forms.

```yaml
types:
  Verbose: bool = typer.Option(False, "--verbose", "-v", help="Print extra detail")

--8<-- "docs/snippets/templates.yaml:global"
```

The param is passed to the command itself, so it goes after the command name
(`files delete notes.txt --verbose`) and is available in `run` as a normal variable.

Global params are added to every command, whether or not it has params of its own.

## Command templates

A template can hold `params`, `pre_run`, `post_run` and `config`.

```yaml
--8<-- "docs/snippets/templates.yaml:template"
```

A command uses it with `template: <name>`:

```yaml
--8<-- "docs/snippets/templates.yaml:commands"
```

```console
$ cli run templates.yaml -- delete notes.txt --yes --verbose
about to delete notes.txt
deleted notes.txt
cleaning up
done
$ cli run templates.yaml delete notes.txt
Are you sure? [y/N]: n
Aborted.
```

### How a template is merged into a command

| Part | Result |
|---|---|
| `params` | Template params first, then the command's own. |
| `pre_run` | Template `pre_run`, then the command's. |
| `post_run` | The command's `post_run`, then the template's. |
| `config` | Combined. A key set on the command overrides the same key from the template. |

Together with global params, a command's arguments are ordered: global params, template params,
command params.

The scripts therefore always run in this order:

1. template `pre_run`
2. command `pre_run`
3. command `run`
4. command `post_run`
5. template `post_run`

All five are placed in one function, so a variable set in `pre_run` can be used in `run`.

In the example, `wipe` sets its own `epilog`, which replaces the one from the template, while
`delete` keeps the template's:

```console
$ cli run templates.yaml -- delete --help
...
╭─ Options ──────────────────────────────────────────────────────────────────╮
│ --verbose  -v        Print extra detail                                    │
│ --yes      -y                                                              │
│ --help     -h        Show this message and exit.                           │
╰────────────────────────────────────────────────────────────────────────────╯

 This command changes files on disk.
```

A command can use one template. Naming a template that does not exist is an error when the manifest
is loaded.

## The complete example

```yaml title="templates.yaml"
--8<-- "docs/snippets/templates.yaml"
```
