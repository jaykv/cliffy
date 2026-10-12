# Installation

cliffy supports **Python 3.11, 3.12, 3.13, 3.14 and 3.15** on macOS and Linux.

## Install

Install cliffy into the virtual environment you want your CLIs to live in.

=== "pip"

    ```console
    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install cliffy
    ```

=== "uv"

    ```console
    $ uv venv
    $ uv pip install cliffy
    $ source .venv/bin/activate
    ```

Check the install:

```console
$ cli --help
```

The package provides two identical commands, `cli` and `cliffy`. The documentation uses `cli`.

!!! note "Why a virtual environment?"
    `cli load` writes a launcher for your CLI into the `bin` directory of the environment cliffy runs
    in, and packages listed under `requires` in a manifest are looked up in that same environment.
    Keeping cliffy, those packages and your loaded CLIs in one environment is the simplest setup.

## Run without installing

[`uvx`](https://docs.astral.sh/uv/guides/tools/) runs cliffy from a cached, isolated environment:

```console
$ uvx cliffy run hello.yaml greet Ada
$ uvx cliffy build hello.yaml -o dist
```

A CLI loaded this way lives inside that cached environment. Call it through `uvx` as well:

```console
$ uvx cliffy load hello.yaml
$ uvx --from cliffy hello greet Ada
```

## Install as a tool

`pipx install cliffy` and `uv tool install cliffy` put `cli` on your `PATH` and keep cliffy in its
own environment. This works well for `cli run`, `cli test`, `cli render` and `cli build`.

Two things differ from a virtual environment install:

- `cli load` writes the launcher into the tool's private `bin` directory, which is not on your
  `PATH`. Use `cli run` or `cli build`, or add that directory to your `PATH`.
- Packages a manifest `requires` must be installed into the tool environment, for example
  `pipx inject cliffy tabulate` or `uv tool install cliffy --with tabulate`.

## Extras

| Extra | Install | Adds |
|---|---|---|
| `rich` | `pip install "cliffy[rich]"` | [rich-click](https://github.com/ewels/rich-click). Styled help for the `cli` command itself, and required for manifests that set `use_click: true`. |
| `ai` | `pip install "cliffy[ai]"` | [pydantic-ai](https://ai.pydantic.dev/). Enables the `cli ai generate` and `cli ai ask` commands. |

Install both with `pip install "cliffy[rich,ai]"`.

[Rich](https://rich.readthedocs.io/) itself is always installed because Typer depends on it, so the
CLIs you generate have styled help output with or without the `rich` extra.

### AI commands

With the `ai` extra installed, `cli ai generate` writes a manifest from a description and `cli ai ask`
answers questions about cliffy. Models are named in pydantic-ai's `provider:model` form and need that
provider's API key in the environment:

```console
$ export OPENAI_API_KEY=...
$ cli ai generate mycli "a CLI that manages docker containers" --model openai:gpt-4o
```

Add `--preview` to print the prompt without calling a model. Model selection, validation of the
generated manifest and `cli ai ask` are covered in [AI commands](ai.md); the options are listed in the
[CLI reference](reference/cli.md#cli-ai).

## What gets installed

| Package | Used for |
|---|---|
| Typer, Click | The generated CLIs and the `cli` command |
| pydantic | Validating manifests |
| PyYAML, Jinja2, deepmerge | Reading, templating and merging manifests |
| pybash | Translating `$` lines into `subprocess` calls |
| shiv | `cli build` |
| watchdog | `cli dev` |
| packaging | Checking `requires` versions |

## Next step

Build your first CLI in the [Quickstart](quickstart.md).
