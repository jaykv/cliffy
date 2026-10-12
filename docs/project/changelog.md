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
- The `ai` extra requires pydantic-ai 2. Model names need a provider prefix; the default model is
  `google:gemini-2.0-flash`.
- `cli dev --run-cli` is a real flag. It no longer re-runs the CLI on every reload when the flag is
  not given.
- `cli build` prints the build output when a build fails.
- The source distribution only contains the package, tests and examples.
- Documentation: new site structure with a tutorial, task guides and reference pages generated from
  the code. Every manifest shown in the guides is run by `make docs-check`.

### Removed

- The `cliffy[dev]` extra. Development dependencies are a dependency group (`uv sync`).

### Fixed

- Manifest file handles are closed after `cli update` and after loading a manifest.
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
