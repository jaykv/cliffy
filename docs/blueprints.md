# Blueprints

A cliffy manifest describes a CLI in cliffy's own vocabulary: `commands`, `params`, `run`. A **blueprint** lets you
bring your own vocabulary instead. You define the YAML schema that fits your domain and tell cliffy how it maps
onto a CLI. Files written in that schema then work with `cli load`, `cli run`, `cli render`, `cli test`, `cli dev`,
`cli docs` and `cli build`, which turns them into a single-file executable.

```
your YAML spec ──▶ Blueprint (validate, to_manifest) ──▶ cliffy manifest ──▶ Typer or Click code ──▶ one executable file
```

## Writing a blueprint

A blueprint is a [pydantic](https://docs.pydantic.dev) model with one required method. The fields are your schema,
and `to_manifest` returns the cliffy manifest for a validated file.

```python title="tasks.py"
from pydantic import BaseModel, Field

from cliffy.blueprint import Blueprint
from cliffy.manifest import CLIManifest, Command, RunBlock


class Task(BaseModel):
    run: str | list[str] = Field(description="Shell line(s) to run, in order.")
    help: str = Field(default="", description="What the task does, shown in --help.")


class Tasks(Blueprint):
    """Task runner: every entry under `tasks` becomes a command that runs shell lines"""

    name: str = Field(description="Name of the CLI.")
    version: str = Field(default="0.1.0", description="Version of the CLI.")
    help: str = Field(default="", description="Description of the CLI.")
    tasks: dict[str, str | list[str] | Task] = Field(min_length=1, description="Tasks by name.")

    def to_manifest(self) -> CLIManifest:
        commands = {}
        for name, entry in self.tasks.items():
            task = entry if isinstance(entry, Task) else Task(run=entry)
            lines = [task.run] if isinstance(task.run, str) else task.run
            script = "\n".join(f"subprocess.run({line!r}, shell=True, check=True)" for line in lines)
            commands[name] = Command(help=task.help, run=RunBlock(script))

        return CLIManifest(name=self.name, version=self.version, help=self.help, commands=commands)
```

A file written in that spec names its blueprint with a top-level `blueprint:` key:

```yaml title="tasks.yaml"
blueprint: tasks.py

name: tasks
help: Project tasks

tasks:
  greet: echo "hello from tasks"
  check:
    - echo "linting"
    - echo "testing"
  release:
    help: Check, then tag the release
    run:
      - echo "linting"
      - echo "tagging"
```

```
$ cli run tasks.yaml -- greet
hello from tasks

$ cli load tasks.yaml
$ tasks check
linting
testing
```

`to_manifest` may return a `CLIManifest` or a plain mapping that validates as one. Because the result is an
ordinary manifest, everything cliffy does with manifests applies: both the Typer and the Click generator
(`use_click`), `requires`, `tests`, command aliases, callbacks and so on.

The whole file is rendered with Jinja2 before the blueprint sees it, exactly like a manifest.

## Selecting a blueprint

Either in the file, or on the command line. The command line wins.

```yaml
blueprint: tasks.py
```

```
cli run jobs.yaml --blueprint tasks.py -- greet
```

`--blueprint` / `-b` is available on `load`, `run`, `render`, `build`, `dev`, `test`, `validate` and `docs`.
`cli update` reuses the blueprint a CLI was loaded with, and `cli info` shows it.

A blueprint reference is one of:

| Reference | Meaning |
|---|---|
| `tasks.py`, `./bp/tasks.py:Tasks` | A Python file. In a YAML file the path is relative to that file; on the command line it is relative to the working directory. Add `:ClassName` when the file defines several blueprints. |
| `mypackage.blueprints:Tasks` | An importable class. `mypackage.blueprints` alone works when the module defines exactly one blueprint. |
| `tasks` | A blueprint provided by an installed package (see [Sharing blueprints](#sharing-blueprints)). |

Cliffy reports a reference it cannot use and says why: the file or module does not exist, the name is provided by
more than one package, the module defines no blueprint or more than one, or the target is not a blueprint.

## Validation errors

Unknown keys are rejected by default, so typos are caught. Errors are reported against your spec, with the path
to the offending key:

```
$ cli validate server.yaml
~ server.yaml is not a valid MCPTools spec
  tools[0].name: Value error, `serve` is a reserved name (got 'serve')
  tools[1].parameters[0].type: Input should be 'string', 'integer', 'number', 'boolean' or 'array' (got 'strng')
  tols: Extra inputs are not permitted 💔
```

Use pydantic validators for rules that go beyond types. To accept unknown keys, set
`model_config = ConfigDict(extra="ignore")` on your blueprint.

## Hooks

Three optional hooks run around `to_manifest`:

```
pre_validate(raw) ──▶ validation ──▶ to_manifest() ──▶ post_manifest(manifest) ──▶ code generation ──▶ post_codegen(code)
```

| Hook | Receives | Use it to |
|---|---|---|
| `pre_validate(cls, raw)` (classmethod) | The YAML mapping, without the `blueprint` key | Accept shorthand forms, set defaults, rename legacy keys |
| `post_manifest(self, manifest)` | The `CLIManifest` | Adjust the manifest, i.e. add commands every CLI of this kind gets |
| `post_codegen(self, code)` | The generated Python source | Adjust the generated code, i.e. prepend a license header |

```python
class Tasks(Blueprint):
    ...

    @classmethod
    def pre_validate(cls, raw):
        # allow `jobs:` as an older name for `tasks:`
        if "jobs" in raw:
            raw = {**raw, "tasks": raw.pop("jobs")}
        return raw

    def post_codegen(self, code):
        return "# generated from a Tasks spec, do not edit\n" + code
```

## Editor completion

`cli blueprint schema` prints the JSON schema of a blueprint's spec.

```
cli blueprint schema tasks.py -o tasks.schema.json
```

Reference it from your YAML files to get validation and completion from the YAML language server:

```yaml
# yaml-language-server: $schema=tasks.schema.json
blueprint: tasks.py
```

Field descriptions (`Field(description=...)`) show up as hover documentation.

## Building a single-file executable

`cli build` applies the blueprint at build time and bundles the generated CLI with its dependencies into one
executable [zipapp](https://docs.python.org/3/library/zipapp.html). With `--target script` or `--target native`
the same file becomes a single Python script or a compiled executable instead; see
[Building executables](guides/building.md).

```
$ cli build tasks.yaml -o dist
+ tasks built 📦
  dist/tasks (single file, needs Python >=3.10, 1.8 MB)
  run it with: ./dist/tasks

$ ./dist/tasks greet
hello from tasks
```

The file runs on any machine with a matching Python. It does not need cliffy, the blueprint, pydantic or the YAML
file.

* **Dependencies.** Whatever the manifest lists under `requires` is bundled. Let your blueprint set `requires`
  for the packages its generated code imports. The CLI framework (typer, or rich-click with `use_click`) is added
  automatically, pinned to the version installed next to cliffy unless `requires` names it.
* **Interpreter.** `--python` / `-p` sets the shebang, by default `/usr/bin/env python3`. The build reports which
  Python versions the bundle supports. A bundle of pure-Python packages runs on every version its packages accept.
  A bundle with compiled extensions only runs on the Python minor version it was built with, so build with the
  version you deploy to. Started with an unsupported Python, the executable exits with a message that says so.
* **Reproducible.** Building the same input twice with the same package versions gives a byte-identical file.
* **Errors.** When a dependency cannot be installed, the build prints pip's reason and writes no file.

On first run the executable unpacks its packages into `~/.shiv` (set `SHIV_ROOT` to change the location).

## Sharing blueprints

A package can register blueprints under the `cliffy.blueprints` entry-point group:

```toml title="pyproject.toml"
[project.entry-points."cliffy.blueprints"]
tasks = "mypackage.blueprints:Tasks"
```

Once the package is installed, the blueprint is available by name:

```yaml
blueprint: tasks
```

```
$ cli blueprints
┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name  ┃ Blueprint                  ┃ Package   ┃ Description                       ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ tasks │ mypackage.blueprints:Tasks │ mypackage │ Task runner: every entry under... │
└───────┴────────────────────────────┴───────────┴───────────────────────────────────┘
```

`cli blueprints` is short for `cli blueprint list`. The description is the first line of the class docstring.

## Examples

Two worked examples live in [`examples/blueprints`](https://github.com/jaykv/cliffy/tree/main/examples/blueprints):

* `tasks.py` with `tasks.yaml`: the task runner from this page.
* `mcp_tools.py` with `text-tools.yaml`: an [MCP](https://modelcontextprotocol.io) tool server. The spec lists
  tools with typed parameters and a Python body. The generated CLI has one command per tool, a `tools` command
  that prints the tool definitions, and a `serve` command that speaks MCP over stdio without extra dependencies.
  `cli build examples/blueprints/text-tools.yaml` gives a single file you can register as an MCP server.

## Callbacks

Callbacks are a manifest feature that blueprints often need: code that runs before every command of the CLI, or
of one command group. They work with both Typer and Click, and the built-in `--version` and `--aliases` options
stay in place.

```yaml
callbacks:
  # no `group`: runs before every command, its params become options of the CLI itself
  - params:
      - name: --verbose
        type: bool
        default: false
        short: -v
        help: Print what is about to run
    invoke_without_command: true
    run: |
      ctx.obj = {"verbose": verbose}
      if ctx.invoked_subcommand is None:
          print("no command given, try --help")
      elif verbose:
          print(f"running {ctx.invoked_subcommand}")

  # runs before every command of the `db` group
  - group: db
    run: print("connecting to db")

commands:
  hello: print("hello")
  db.migrate: print("migrating")
```

```
$ mycli --verbose db migrate
running db
connecting to db
migrating
```

| Key | Meaning |
|---|---|
| `run` | Code to run. The Typer or Click context is available as `ctx`. |
| `group` | Command group the callback belongs to, i.e. `db` or `db.tables`. Leave it out for the CLI itself. |
| `params` | Options given before the command name, in the same syntax as command params. |
| `invoke_without_command` | Also run when no command is given, instead of showing the help. |

Several callbacks for the same target run in the order given. A manifest with only callbacks and no `commands`
is valid, which makes a single-purpose CLI.
