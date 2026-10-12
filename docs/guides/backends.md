# Click and Typer backends

cliffy can generate two kinds of code from the same manifest.

| | Typer (default) | Click |
|---|---|---|
| Enable with | nothing | `use_click: true` |
| Generated code uses | `typer` | `rich_click` |
| Extra install | none | `pip install "cliffy[rich]"` |
| Supported manifest features | all | a subset, listed below |

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
| Boolean options | `--loud: bool = False` is a `--loud/--no-loud` switch, as with Typer. |
| `types` | Not supported. Type names are passed to Click as written, so only real Python types work. |
| `config` | Ignored. |
| `--version` output | `<program>, version <version>` instead of `<name>, <version>`. |

### Building

The generated module imports `rich_click`. `cli build` reads that from the generated code and bundles
rich-click instead of Typer, so the manifest does not have to list it under `requires`.

## Typer notes

- Typer depends on Rich, so generated CLIs print styled help and tracebacks without extra setup.
- Typer adds `--install-completion` and `--show-completion` to every CLI. Turn them off with:

    ```yaml
    cli_options:
      add_completion: false
    ```

- Anything from the [Typer documentation](https://typer.tiangolo.com/) that fits in a function
  signature or body can be used in `types`, generic params and `run` scripts.
