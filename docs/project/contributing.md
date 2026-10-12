# Contributing

Bug reports, fixes and documentation improvements are welcome. Open an issue or a pull request on
[GitHub](https://github.com/jaykv/cliffy).

## Set up

You need [uv](https://docs.astral.sh/uv/) and one of the supported Python versions (3.11 to 3.15).

```console
$ git clone https://github.com/jaykv/cliffy.git
$ cd cliffy
$ make install        # uv sync --frozen --all-extras --group docs
$ uv run cli --help
```

`make install` creates `.venv` with cliffy in editable mode, both extras, the test tools and the
documentation tools. To work on another Python version, run `uv sync --all-extras --python 3.15`.

On macOS with Python 3.14 or 3.15, some dependencies are built from source, which needs the Xcode
command line tools.

## Everyday commands

| Command | What it does |
|---|---|
| `make test` | Runs the test suite in parallel with coverage. |
| `make lint` | Checks formatting and lint rules with ruff, then types with mypy. |
| `make format` | Formats the code and applies ruff's automatic fixes. |
| `make check` | `format`, `lint`, `test` and `clean` in one go. |
| `make docs-serve` | Serves the documentation at `http://127.0.0.1:8000` with live reload. |
| `make docs-generate` | Regenerates the reference pages. |
| `make docs-check` | Checks the reference pages and runs every documentation manifest. |
| `make docs-build` | `docs-check`, then a strict documentation build. |
| `make generate-schema` | Regenerates `examples/cliffy_schema.json` from the models. |
| `make generate-clis` | Regenerates `examples/generated/*.py` from the manifests in `examples/`. |
| `make clean` | Removes build and cache directories. |

Run a single test file or test with pytest directly:

```console
$ uv run pytest tests/test_manifest.py -v
$ uv run pytest tests/test_manifest.py::test_validate_cli_requires -v
```

Run the tests through `uv run` so that the environment's `bin` directory is on the `PATH`; tests
that load CLIs start them by name. Do not run two test sessions in the same checkout at once,
because loaded CLIs are shared state.

CI runs `make lint` and `make test` on Python 3.11 to 3.15 for every pull request.

## How the code is organized

A manifest goes through three stages:

```text
YAML file ─► Transformer ─► CLIManifest ─► Commander ─► Python source ─► Loader / builder
```

| Module | Role |
|---|---|
| `cliffy/transformer.py` | Renders the manifest with Jinja2, resolves `includes`, validates it and checks `requires`. |
| `cliffy/manifest.py` | The pydantic models that define the manifest format and the JSON schema. |
| `cliffy/commander.py` | Builds groups, merges command templates and drives code generation. |
| `cliffy/commanders/typer.py`, `click.py` | Emit Typer or Click code. |
| `cliffy/parser.py` | Translates params and run scripts for the Typer backend. |
| `cliffy/cli.py`, `cliffy/ai.py` | The `cli` command itself. |
| `cliffy/loader.py`, `cliffy/homer.py` | Install generated CLIs and keep their metadata. |
| `cliffy/builder.py` | `cli run` and `cli build`. |
| `cliffy/reloader.py` | `cli dev`. |
| `cliffy/tester.py` | `cli test`. |
| `cliffy/doc.py` | `cli docs`. |

When you add a manifest key, update the model in `cliffy/manifest.py`, handle it in the commanders,
then run `make generate-schema` and `make docs-generate`.

## Working on the documentation

The site is built with [Zensical](https://zensical.org/) from the
`docs/` directory. The build is strict: a broken link or a missing file is an error.

### Generated pages

Three pages are written by `scripts/docs.py` and must not be edited by hand:

| Page | Generated from |
|---|---|
| `docs/reference/cli.md` | The Click commands in `cliffy/cli.py` and `cliffy/ai.py` |
| `docs/reference/manifest.md` | The models in `cliffy/manifest.py` |
| `docs/reference/examples.md` | The manifests in `examples/` |

After changing a command, an option, a model or an example, run `make docs-generate` and commit the
result. The hand-written notes on those pages live in `scripts/docs.py`, next to the code that
renders them. The script stops with a message when a new command, argument, model field or example
has no description yet.

### Manifests in the guides

Guides do not contain copies of YAML. They embed files from `docs/snippets/` (or `examples/`) with
the snippet syntax, optionally limited to a named section:

```text
;--8<-- "docs/snippets/params.yaml:shorthand"
```

A section is the part of the YAML file between a pair of marker comments that carry its name. Open
any file in `docs/snippets/` to see them; the
[snippets extension](https://facelessuser.github.io/pymdown-extensions/extensions/snippets/#snippet-sections)
documents the syntax.

Every manifest in `docs/snippets/` should have a `tests` section. `make docs-check` loads each one,
compiles the generated code and runs its tests, so a guide cannot show a manifest that does not
work. When you add console output to a page, copy it from a real run.

### Preview

```console
$ make docs-serve
```

## Releasing

1. Set the version in `pyproject.toml` and run `uv lock`.
2. Move the "unreleased" entry in `docs/project/changelog.md` under the new version and date, and
   add [migration notes](migration.md) for breaking changes.
3. Merge to `main`, then publish a GitHub release whose tag equals the version (`0.7.0` or
   `v0.7.0`).

The `publish.yaml` workflow builds the package, checks that the tag matches the version and uploads
to PyPI through trusted publishing. Pushing documentation changes to `main` deploys the site.
