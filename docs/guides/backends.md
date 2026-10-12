# Click and Typer backends

cliffy can generate two kinds of code from the same manifest.

| | Typer (default) | Click |
|---|---|---|
| Enable with | nothing | `use_click: true` |
| Generated code uses | `typer` | `rich_click` |
| Extra install | none | `pip install "cliffy[rich]"` |
| Supported manifest features | all | a subset, listed below |

**Use Typer unless you have a specific reason to generate Click code.** Typer is the backend the rest
of this documentation describes, and the only one `cli test` supports.

## The Click backend

```yaml title="click.yaml"
--8<-- "docs/snippets/click.yaml"
```

```console
$ cli run click.yaml -- hello Ada --times 2
hello Ada
hello Ada
$ cli run click.yaml -- tag --loud a b
A
B
$ cli run click.yaml db migrate
migrating
```

### What works

- Commands, groups (`db.migrate`) and aliases (`hello|hi`)
- Shorthand params: arguments (`name: str`) and options with a default (`--times: int = 1`)
- Explicit params, which always become options. Write the `name` **without** `--`.
- Generic params, written as Click decorators
- `pre_run`, `post_run` and command templates
- `vars`, `imports`, `functions`, `includes` and shell lines

### What differs from Typer

| Feature | With `use_click: true` |
|---|---|
| Short option names (`--times|-t`) | Not supported in shorthand params. Use a generic param: `"@click.option('--times', '-t', type=int, default=1)"`. |
| Boolean options | `--loud: bool = False` expects a value (`--loud true`). For a flag, use a generic param with `is_flag=True`. |
| `types` | Not supported. Type names are passed to Click as written, so only real Python types work. |
| `config` | Ignored. |
| `global_params` | Added to commands that have params, as with Typer. |
| `cli test` | Not supported. |
| `--version` output | `<program>, version <version>` instead of `<name>, <version>`. |

### Building

The generated module imports `rich_click`. `cli build` bundles Typer automatically but not
rich-click, so list it in the manifest:

```yaml
requires:
  - rich-click
```

## Typer notes

- Typer depends on Rich, so generated CLIs print styled help and tracebacks without extra setup.
- Typer adds `--install-completion` and `--show-completion` to every CLI. Turn them off with:

    ```yaml
    cli_options:
      add_completion: false
    ```

- Anything from the [Typer documentation](https://typer.tiangolo.com/) that fits in a function
  signature or body can be used in `types`, generic params and `run` scripts.
