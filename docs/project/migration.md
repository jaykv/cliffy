# Migration notes

What to change when you upgrade. Each section lists the breaking changes of one release and the
action to take. The full list of changes is in the [changelog](changelog.md).

## From 0.6.x to 0.7.0

### Python 3.11 or newer is required

cliffy 0.7.0 supports Python 3.11 to 3.15. On Python 3.9 or 3.10, pip keeps installing 0.6.1.

**Action:** upgrade the interpreter of the environment cliffy is installed in, then reinstall:

```console
$ python --version
$ pip install --upgrade cliffy
```

Loaded CLIs are tied to an environment. After moving to a new environment, load your manifests
again with `cli load`.

### `typer` replaces `typer-slim`

cliffy now depends on the full `typer` package, which always installs `rich` and `shellingham`.
Generated CLIs therefore always have Rich-formatted help.

**Action:** none in most cases. If you pinned `typer-slim` next to cliffy in a requirements file,
replace it with `typer`.

### The `dev` extra is gone

`pip install "cliffy[dev]"` no longer exists.

**Action:** contributors set up the project with `uv sync --all-extras`. See
[Contributing](contributing.md).

### AI commands: model names need a provider

The `ai` extra now requires pydantic-ai 2, which only accepts model names in `provider:model` form.

| Before | Now |
|---|---|
| `--model gpt-4o` | `--model openai:gpt-4o` |
| `--model gemini-2.0-flash` | `--model google:gemini-2.0-flash` |

**Action:** add the provider prefix wherever you pass `--model` or `-m`. The default model is
`google:gemini-2.0-flash`.

### `cli dev --run-cli`

In 0.6.x with Click 8.2 or later, the CLI was run after every reload even without `--run-cli`. Now
it only runs when the flag is given.

**Action:** add `--run-cli` to your `cli dev` command if you relied on the old behavior.

### Manifests

The manifest format is still schema v3, and most manifests written for 0.5.x and 0.6.x load without
changes. A few things that used to be accepted silently are now checked, and the Click backend
follows the documented meaning of params.

| What | Before | Now | Action |
|---|---|---|---|
| `manifestVersion: v1` or `v2` | Ignored | An error | Set `manifestVersion: v3` or remove the line. |
| A `vars` key such as `my-var`, `cli` or `class` | Generated code that did not compile | An error | Rename the var, for example to `my_var`. |
| A var that refers to itself | Left as literal `{{ }}` text | An error | Remove the reference, or wrap literal braces in `{% raw %}`. |
| `types: {Count: int}` with `--n: Count` (Typer) | The positional argument `n` | The option `--n` | None if you meant an option. For an argument, write `n: Count`. |
| `types: {Count: int = 1}` with `n: Count` (Typer) | The option `--n` | An optional argument | Write `--n: Count` for an option. |
| `use_click`: explicit param `name: width` | The option `--width` | A positional argument | Write `name: --width`. |
| `use_click`: shorthand `name: str` | A required argument | An optional argument, `None` when omitted | Write `name: str!`. |
| `use_click`: `config` on a command | Ignored | Applied | Remove settings you did not mean, such as `hidden: true`. |
| `use_click`: a `typer.Option(...)` definition | Copied into code that failed at run time | An error when the manifest is loaded | Write a Click decorator, see [Click and Typer backends](../guides/backends.md). |
| First line of the generated code | `## Generated <name> on <time>` | `## Generated <name> with cliffy <version>` | None, unless a script of yours reads that line. |

Run `cli validate` on each manifest after upgrading. It now also compiles and imports the generated
code.

## From 0.4.x to 0.5.0 (schema v3)

The main change is that `args` on a command was renamed to `params`.

**Action:** rename the key in every command, and set `manifestVersion: v3` or remove the line. Then
run `cli validate` on the manifest to find anything else the schema no longer accepts.

## From 0.3.x to 0.4.0 (schema v2)

Manifests written for 0.3.x use the v1 format, which later releases do not read.

**Action:** rewrite the manifest in the current format. The [Quickstart](../quickstart.md) and the
[manifest reference](../reference/manifest.md) describe it, and `cli init mycli --raw` writes a
minimal manifest to start from.
