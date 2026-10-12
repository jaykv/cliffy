# Click and Typer backends

cliffy can generate two kinds of code from the same manifest.

| | Typer (default) | Click |
|---|---|---|
| Enable with | nothing | `use_click: true` |
| Generated code uses | `typer` | `rich_click`, or plain `click` when rich-click is not installed |
| Extra install | none | none. `pip install "cliffy[rich]"` adds rich-formatted help |
| Supported manifest features | all | all, with the differences listed below |

**Use Typer unless you have a specific reason to generate Click code.** Typer is the backend the rest
of this documentation describes.

## The Click backend

```yaml title="click.yaml"
--8<-- "docs/snippets/click.yaml"
```

```console
$ cli run click.yaml -- hello Ada --times 2
hello Ada
hello Ada
$ cli run click.yaml -- resize cat.jpg -w 100
cat.jpg 100
$ cli run click.yaml -- tag --loud a b
A
B
$ cli run click.yaml db migrate
migrating
```

### What works

- Commands, groups (`db.migrate`) and aliases (`hello|hi`)
- Shorthand and explicit params with the same meaning as for Typer: a name with `--` is an option,
  anything else is a positional argument, `!` or `required: true` makes it required, and `short`,
  `default` and `help` are passed on
- `types`, command `config`, `global_params`, `callbacks`, `pre_run`, `post_run` and command templates
- Generic params, written as Click decorators
- `vars`, `imports`, `functions`, `includes`, shell lines and `cli test`

### What differs from Typer

| Feature | With `use_click: true` |
|---|---|
| Generic params | A string param is a Click decorator such as `"@click.option('--loud', is_flag=True)"`. A Typer signature entry is rejected. |
| `types` | A plain type (`Count: int`, `Count: int = 1`) works with both backends. A full definition is a Click decorator, `Loud: "@click.option('--loud', is_flag=True)"`; a `typer.Option(...)` definition is rejected with an error that names the command. |
| Inline `typer.Option(...)` in a shorthand param | Rejected. Use a Click decorator. |
| List types | `--tag: list[str]` can be given several times and arrives as a tuple, not a list. |
| Boolean options | `--loud: bool = False` is a `--loud/--no-loud` switch, also when it has a short form. |
| `config.rich_help_panel` | Passed to rich-click as `panel`. The generated code then requires rich-click. |
| `--version` output | `<program>, version <version>` instead of `<name>, <version>`. |

A manifest that uses something the Click backend cannot express stops with an error such as:

```text
~ error in tools.yaml: command `pack`: param `level` uses types.Level, which is a Typer definition (...)
```

### rich-click is optional

The generated module starts with:

```python
try:
    import rich_click as click
except ImportError:  # plain help output when rich-click is not installed
    import click
```

With rich-click installed the help is formatted with Rich. Without it the same CLI runs on plain
Click, which cliffy always installs. `cli build` reads this import and ships rich-click with the
built CLI.

### Building

`cli build` reads the import of `rich_click` from the generated code and bundles rich-click instead of
Typer, so the manifest does not have to list it under `requires`.

## Typer notes

- Typer depends on Rich, so generated CLIs print styled help and tracebacks without extra setup.
- Typer adds `--install-completion` and `--show-completion` to every CLI. Turn them off with:

    ```yaml
    cli_options:
      add_completion: false
    ```

- Anything from the [Typer documentation](https://typer.tiangolo.com/) that fits in a function
  signature or body can be used in `types`, generic params and `run` scripts.
