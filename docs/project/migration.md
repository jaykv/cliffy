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

### Shell lines follow shell quoting

cliffy 0.7.0 uses pybash 0.4, which parses `$` lines the way a shell does. Most lines behave as
before. These changed:

| Line | Before | Now |
|---|---|---|
| `$ echo 'a\nb'` | Python read the backslash: two lines of output | The command gets `a\nb`, as in a shell |
| `> echo f{name}` | The value was pasted into the shell command | The value is quoted and is always one word |
| `> grep "two words" file` | The quotes were removed before the shell saw them | The shell gets the line as written |
| `out = $ ls \| wc -l` | `out` was a process object | `out` is the output of the pipeline, as `bytes` |
| `$ echo a > one.txt > two.txt` | The second file got a copy of the first | Both files get the output |
| `$ make && echo ok` | `NotImplementedError` | Runs `echo ok` when `make` succeeds |

**Action:** run `cli test` on your manifests. If a `>` line relied on a value being pasted in as
shell syntax, for example a glob pattern, see
[When you need a real shell](../guides/shell-commands.md#when-you-need-a-real-shell).

A script that is not valid Python, or a `$` line that cannot be translated, now stops `cli load`
with a message that names the command and the line. Before, the CLI was generated and failed when
it ran.

### `cli build` output

`cli build` prints two more things after a build, the size of the file and how to run it. Scripts
that read that output need to be adjusted. The file itself is built as before; the new
`--target` option is described in [Building executables](../guides/building.md).

### Manifests

The manifest format did not change. Manifests written for 0.5.x and 0.6.x (schema v3) load without
changes, apart from the shell lines described above.

## From 0.4.x to 0.5.0 (schema v3)

The main change is that `args` on a command was renamed to `params`.

**Action:** rename the key in every command, and set `manifestVersion: v3` or remove the line. Then
run `cli validate` on the manifest to find anything else the schema no longer accepts.

## From 0.3.x to 0.4.0 (schema v2)

Manifests written for 0.3.x use the v1 format, which later releases do not read.

**Action:** rewrite the manifest in the current format. The [Quickstart](../quickstart.md) and the
[manifest reference](../reference/manifest.md) describe it, and `cli init mycli --raw` writes an empty
skeleton to start from.
