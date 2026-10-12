# Quickstart

In this tutorial you build `notes`, a small CLI that stores notes in a JSON file. Along the way you
use every core part of a manifest: commands, params, helper functions, groups, aliases, shell
commands and tests. It takes about 15 minutes.

You need cliffy installed in an active virtual environment. See [Installation](installation.md).

The finished manifest is at the [end of this page](#the-finished-manifest).

## 1. A manifest with one command

Create a file called `notes.yaml`:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes-step1.yaml"
```

- `name` is what you will type to run the CLI. `version` is shown by `notes --version`.
- Each key under `commands` is a command. `run` holds its Python code.
- `text: str!` declares a parameter called `text` of type `str`. The `!` makes it required.
  Parameters are ordinary variables inside `run`.
- `tests` is optional. You will come back to it in [step 7](#7-test-it).

Run the command without installing anything:

```console
$ cli run notes.yaml add "buy milk"
Added buy milk
```

`cli run` generates the CLI, runs it once and throws it away. To see the Python it generated, use
`cli render`:

```console
$ cli render notes.yaml
```

```python
def add(text: str = typer.Argument(...)):
    print(f"Added {text}")


cli.command("add", help="Add a note",)(add)
```

Your `run` script became the body of a Typer command function.

## 2. Store the notes

The CLI needs to read and write a file. Add `imports`, `vars` and `functions` between `help` and
`commands`:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml:storage"
```

- `imports` is copied to the top of the generated module.
- `functions` is a list of helper functions that every command can call.
- `vars` defines manifest variables. `{{ default_file }}` is replaced with `notes.json` when the
  manifest is loaded. More in [Vars and Jinja](guides/vars-and-jinja.md).

## 3. Describe parameters once with types

`text: str!` is short, but it has no help text. The `types` section lets you name a full
[Typer parameter definition](https://typer.tiangolo.com/tutorial/arguments/) and reuse it. Add this
after `functions`:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml:types"
```

Now replace the `add` command so that it uses those types and saves the note:

```yaml title="notes.yaml"
commands:
--8<-- "docs/snippets/notes.yaml:add"
```

Try it:

```console
$ cli run notes.yaml add "buy milk"
Added note 1 [general]
$ cli run notes.yaml -- add "book flights" --tag travel
Added note 2 [travel]
```

!!! tip "The `--` separator"
    When the arguments for your CLI include options such as `--tag`, put `--` after the manifest
    path. Without it, `cli run` tries to interpret `--tag` as one of its own options.

## 4. Add options and an alias

Add a second command under `commands`:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml:list"
```

- The key `list|ls` creates the command `list` and the alias `ls`.
- `--tag|-t: str = ""` is an option (the name starts with `--`) with the short form `-t` and an
  empty string as its default.

```console
$ cli run notes.yaml list
1. [general] buy milk
2. [travel] book flights
$ cli run notes.yaml -- ls -t travel
2. [travel] book flights
```

## 5. Exit codes and groups

Commands can stop with an error code by raising `typer.Exit`. Add `remove`:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml:remove"
```

A dot in a command key creates a group. These two commands are run as `notes tags list` and
`notes tags rename`. The entry `tags`, which has `help` and no `run`, sets the help text of the group:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml:tags"
```

```console
$ cli run notes.yaml tags list
general (1)
travel (1)
$ cli run notes.yaml tags rename general home
Renamed general to home
$ cli run notes.yaml remove 7
No note 7
```

## 6. Call a shell command

A line that starts with `$` is run as a shell command. `f{...}` inserts the value of a Python
expression into it:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml:backup"
```

```console
$ cli run notes.yaml backup
Backed up to notes.json.bak
```

More in [Shell commands](guides/shell-commands.md).

## 7. Test it

Replace the `tests` section at the end of the file:

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml:tests"
```

- An entry that starts with `$` is a shell step. Here it removes leftover files before and after
  the run.
- Every other entry maps a command line to Python assertions. `result` is the outcome of the
  command, with `result.output` and `result.exit_code`. `result_text` is the output with
  surrounding whitespace removed.

```console
$ cli test notes.yaml
✨ Invoking tests ✨
...
💚 All tests passed!
```

More in [Testing manifests](guides/testing.md).

## 8. Load it as a real command

So far every call went through `cli run`. Load the manifest to get a `notes` command:

```console
$ cli load notes.yaml
✨ Generated notes CLI v0.1.0 ✨
$ notes -h
$ notes add --help

 Usage: notes add [OPTIONS] {text}

 Add a note

╭─ Arguments ────────────────────────────────────────────────────────────────╮
│ *    text      <str>  Text of the note [required]                          │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────╮
│ --tag   -t      <str>  Tag to file the note under [default: general]       │
│ --help  -h             Show this message and exit.                         │
╰────────────────────────────────────────────────────────────────────────────╯
```

`notes` stays available in this environment until you run `cli remove notes`. After you edit the
manifest, run `cli update notes` to regenerate it, or let [`cli dev`](guides/dev-loop.md) do that
on every save.

## 9. Ship it as one file

```console
$ cli build notes.yaml -o dist
+ notes built 📦
$ ./dist/notes --version
notes, 0.1.0
```

`dist/notes` is a self-contained zipapp. It runs on any machine with a compatible Python 3 and does
not need cliffy. More in [Building executables](guides/building.md).

## The finished manifest

```yaml title="notes.yaml"
--8<-- "docs/snippets/notes.yaml"
```

The `examples` section at the end is used by [`cli docs`](guides/generating-docs.md).

## Next steps

- [Manifest basics](guides/manifest-basics.md) explains how a manifest is put together.
- [Params and types](guides/params.md) covers every way to declare a parameter.
- [Command templates and global params](guides/templates-and-global-params.md) shows how to share
  params between commands.
