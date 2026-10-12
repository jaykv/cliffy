# Changelog

Notable changes per release. Entries before 0.7.0 were reconstructed from the git history and tags,
because no changelog was kept at the time; they list the main changes, not every commit. Release
artifacts are on [PyPI](https://pypi.org/project/cliffy/#history).

## 0.7.0 (unreleased)

The first release after a long pause. It brings the project up to date with current Python and
dependency versions. Read the [migration notes](migration.md#from-06x-to-070) before upgrading.

### Changed

- **Supported Python versions are now 3.11 to 3.15.** Python 3.9 and 3.10 are no longer supported.
- Depends on `typer` instead of `typer-slim`, so `rich` and `shellingham` are always installed.
- Minimum dependency versions were raised to current releases, among them `click>=8.2.1`,
  `typer>=0.24.0`, `pydantic>=2.12.0`, `rich-click>=1.9.0` and `pydantic-ai>=2.0.0`.
- The `ai` extra requires pydantic-ai 2. Model names need a provider prefix. Without `--model`, the
  `CLIFFY_AI_MODEL` environment variable or a default for the provider whose API key is set is used,
  and generated manifests are validated before they are written. See [AI commands](../ai.md).
- `cli build` bundles the framework the generated code imports (Typer or rich-click), pinned to the
  installed version, writes a reproducible file and reports the Python version it needs.
- Commands exit with 1 on failure, among them `cli test` when any test fails, `cli build` when a build
  fails and `cli validate` for an invalid manifest.
- Include paths are looked up next to the including manifest first.
- With the Click backend a `bool` option is a `--flag/--no-flag` switch, and short option names,
  `global_params` and `cli test` work as they do with Typer.
- `cli dev --run-cli` is a real flag. It no longer re-runs the CLI on every reload when the flag is
  not given.
- `cli build` prints the build output when a build fails.
- Requires pybash 0.4. Shell lines are parsed like a shell parses them: quotes and backslashes reach
  the command unchanged, a value inserted into a `>` line is quoted, and `>` lines keep their quotes.
  See the [migration notes](migration.md#from-06x-to-070).
- A CLI imports `pybash.runtime` when it uses pipes, redirects or chains in `$` lines, and nothing
  but `subprocess` otherwise. Built CLIs carry that helper themselves and do not need pybash.
- A shell line that cannot be translated, or a Python syntax error in a script, is reported when the
  manifest is loaded, with the command, the line and the column.
- After a build, `cli build` prints the size of the file and how to run it. `--python` has no fixed
  default any more: each target has its own.
- The source distribution only contains the package, tests and examples.
- Documentation: new site structure with a tutorial, task guides and reference pages generated from
  the code. Every manifest shown in the guides is run by `make docs-check`.
- **`cli validate` compiles and imports the generated code** and reports a problem against the command
  it comes from. It used to check only the YAML, the schema and `requires`.
- **`manifestVersion` is checked.** `v1`, `v2` and unknown values stop the load with an error that says
  what to change, also in include files and blueprint specs. The key used to be ignored.
- **Click backend, explicit params:** a `name` without `--` is a positional argument, as it is with
  Typer. It used to become an option. Write `name: --width` for an option.
- **Click backend, shorthand arguments:** `label: str` is optional and `None` when omitted, as it is
  with Typer. Write `label: str!` for a required argument.
- **Plain types in `types` are aliases for both backends.** With `Count: int`, the param `--n: Count`
  is the option `--n` and an explicit param keeps its `default` and `help`. The Typer backend used to
  replace the whole definition, which made `--n: Count` a positional argument.
- The Click backend supports `types`, command `config` (`rich_help_panel` becomes rich-click's `panel`),
  argument help, and `Optional[...]` and `list[...]` types. A Typer definition in a Click manifest is
  rejected with an error that names the command.
- A manifest no code can be generated for (a command or param name that cannot be a Python name, an
  unknown `template`) stops every command with `~ error in <file>: command <name>: ...` instead of a
  traceback.
- Generated Click code imports rich-click when it is installed and plain Click otherwise, so
  `use_click: true` no longer needs the `rich` extra. `cli build` ships rich-click with such a CLI.
- Generated code no longer starts with the time of generation. The first line is
  `## Generated <name> with cliffy <version>`, so the same manifest renders the same code every time.
- `vars` keys must be valid Python identifiers that the generated code does not use itself. `my-var`
  used to produce code that did not compile.
- A var that refers to itself, or vars that refer to each other in a circle, are an error.
- `cli init --raw` writes a manifest with one command and one test instead of an empty skeleton.
- A corrupt metadata file is listed under the name of its CLI (`hello`, not `hello.json`), so it can be
  removed with `cli rm`.
- `make generate-clis` renders `examples/generated/` with `scripts/examples.py` and no longer installs
  packages. The `generate-cleanup` target is gone.

### Added

- `cli build --target` chooses what is built from the same manifest: `zipapp` (the default, as
  before), `script` for a single Python file with its dependencies declared inline, to run with uv,
  and `native` for a compiled executable that brings its own Python. See
  [Building executables](../guides/building.md).
- Shell lines support `&&`, `||`, `;`, `|&`, `2>`, `&>`, `2>&1`, `$(command)`, continuation lines and
  comments. See [Shell commands](../guides/shell-commands.md).
- [Blueprints](../blueprints.md): custom YAML specs that map onto a CLI, selected with `--blueprint`
  or a `blueprint:` key, and the `cli blueprint list` and `cli blueprint schema` commands.
- [`callbacks`](../blueprints.md#callbacks) in manifests: code that runs before the commands of the
  CLI or of a group, for both backends.
- `vars` values can be numbers and booleans, and a var can be built from other vars in any order.
- `cli dev` also watches included manifests and the Python file of a file blueprint.

### Security

- Text from a manifest (help, names, defaults, versions) is escaped in the generated code and names
  are validated, so manifest data cannot change the code that is generated.

### Removed

- The `cliffy[dev]` extra. Development dependencies are a dependency group (`uv sync`).

### Fixed

- Manifest file handles are closed after `cli update` and after loading a manifest.
- `cli --version` prints cliffy's version. With the `rich` extra it printed the version of rich-click.
- Line breaks in command and group help become spaces (`Greet\nuser` was shown as `Greetuser`) and
  blank lines stay paragraph breaks.
- Two manifest names that map to the same Python name (command `db-app` and group `db`, a command and
  a name from `imports`, `functions` or `vars`) no longer break the generated module.
- The `cli test` counter counts test cases only; it could print `10 of 9`.
- `cli test` removes colors and styles from the output before the assertions run. On a CI system rich
  styles help output, which made tests that passed locally fail there.
- A Jinja error in a manifest is reported with file, line and the text of the line instead of a
  traceback.
- The field descriptions in the JSON schema and the `cli init` template were wrong in places.
- cliffy type-checks and its test suite passes without the optional extras. The test suite no longer
  extracts zipapps into `~/.shiv`.
- Compatibility with Click 8.2 and later, rich-click 1.9 and Python 3.12 and later (deprecated APIs
  replaced).

## 0.6.1 (2025-02-05)

- Changed the default model of the AI commands.
- Documentation updates.

## 0.6.0 (2025-02-02)

- Added the `cli ai generate` and `cli ai ask` commands behind the new `ai` extra.
- Added `cli docs` to generate Markdown, reStructuredText or HTML documentation for a CLI, and the
  `examples` manifest key that feeds it.
- Expanded the documentation site.

## 0.5.3 (2025-01-24)

- Added the Click backend (`use_click: true`) and refactored code generation into per-framework
  commanders.
- Moved the project to uv.
- Added Python 3.13 to the test matrix and extended the test suite.

## 0.5.2 (2025-01-16)

- Reworked command parameter parsing.

## 0.5.1 (2025-01-16)

- Added the `todo` example and documentation updates.

## 0.5.0 (2025-01-14)

- **Manifest schema v3.** `args` was renamed to `params`; v2 manifests are rejected.
- Added `global_params`.
- Added the JSON schema for manifests and `cli init --json-schema`.

## 0.4.0 (2025-01-11)

- **Manifest schema v2**; v1 manifests are rejected.
- Added command templates and the `pre_run` and `post_run` hooks.
- First version of the documentation site.

## 0.3.8 (2024-08-26)

- Added `cli test` and the `tests` manifest key.
- Added Python 3.12 to the test matrix.
- Fixed path handling on Windows.

## 0.3.7 (2024-08-07)

- Added command aliases.

## 0.3.6 (2024-08-02)

- Added `cli dev` (hot reload) and `cli rm-all`.

## 0.3.5 (2023-09-19)

- Declared Click as an explicit dependency.

## 0.3.4 (2023-08-06)

- CLI metadata is stored inside the installed package.

## 0.3.3 (2023-07-17)

- Merged the `bundle` command into `cli build`.
- Type-checking fixes.

## 0.3.0 to 0.3.2 (2023-06)

- Internal refactoring and a newer pybash.

## 0.2.9 (2023-05-22)

- Environment variables can be used in `vars`.

## 0.2.8 (2023-05-21)

- Added `cli run`.
- Executables are built with shiv.

## 0.2.7 (2023-05-02)

- Rich became optional.
- Windows fixes.

## 0.2.6 (2023-04-27)

- Added `requires`.

## 0.2.5 (2023-04-16)

- Added `vars` with Jinja2 templating.
- Added `includes` with deep merging.

## 0.2.3 (2023-04-03)

- Added loading, unloading and listing of CLIs.

## 0.2.2 (2023-03-15)

- Added `cli init`.
- Several manifests can be loaded in one call.
- Added manifest versioning.

## 0.2.0 and 0.2.1 (2023-03-09)

- Renamed the project to cliffy.
- Added `help`, `cli_options`, option aliases, custom imports and a shorter param syntax.

## 0.1.0 (2023-01-29)

- First release.
