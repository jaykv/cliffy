# Building executables

`cli build` turns a manifest into one file that you can hand to someone else. The manifest stays the
same; `--target` chooses what kind of file you get.

| | `zipapp` (default) | `script` | `native` |
|---|---|---|---|
| What you get | `notes`, a Python [zipapp](https://docs.python.org/3/library/zipapp.html) with the dependencies inside | `notes.py`, readable Python with the dependencies declared at the top | `notes`, a compiled executable with its own Python inside |
| The other machine needs | A compatible Python | [uv](https://docs.astral.sh/uv/), or Python with the dependencies installed | Nothing. Same operating system and CPU as the build machine |
| Network on the other machine | No | The first run, to download the dependencies | No |
| The build machine needs | Network or a pip cache for the dependencies | Nothing | [Rust](https://rustup.rs) (`cargo`), uv and network |
| Build time | 2 s | Under 1 s | 1 min |
| File size | 1.8 MB | 1 to 12 kB | 30 MB |
| First start | 0.2 s | 0.2 s with the dependencies in uv's cache | 1.5 s |
| Later starts | 0.05 s | 0.05 s | 0.05 s |
| Written to disk on the other machine | 8 MB in `~/.shiv` | uv's cache | 110 MB in the user's data and cache directories |

The numbers were measured on an Apple Silicon Mac with Python 3.11 for a CLI whose only dependency is
Typer. They show the proportions; yours will differ.

Whatever the target, the file holds the generated CLI and does not need cliffy. `$` lines with pipes,
redirects or `&&` use a small helper from pybash; `cli build` copies it into the file, so pybash is
not needed either.

## Build

```console
$ cli build notes.yaml -o dist
+ notes built 📦
  dist/notes (single file, needs Python >=3.10, 1.8 MB)
  run it with: ./dist/notes
$ ./dist/notes --version
notes, 0.1.0
```

Without `-o`, the file is written to the current directory. Several manifests can be built in one
call, and a CLI that is already loaded can be built by name:

```console
$ cli build notes.yaml hello.yaml -o dist
$ cli build notes -o dist --target script
```

When a build fails, the reason is printed and `cli build` exits with 1.

A file written in a [blueprint](../blueprints.md#building-a-single-file-executable)'s spec is built
the same way for every target; the blueprint is applied at build time and is not shipped.

## Dependencies

Every target ships the packages under `requires`:

```yaml
requires:
  - tabulate>=0.9.0
```

Unlike `cli load`, building from a manifest does not need those packages to be installed in your
environment.

The framework the generated code imports (Typer, or rich-click with `use_click`) is added for you,
pinned to the version installed next to cliffy unless `requires` names it.

## zipapp

The default. A zipapp built with [shiv](https://shiv.readthedocs.io/) contains the CLI and its
dependencies, downloaded with pip at build time. The other machine needs Python and nothing else.

- The line printed after a build says which Python the file needs. The file checks this when it
  starts and stops with a readable message on an unsupported interpreter.
- The file starts with a `#!` line that selects the Python to run it, `/usr/bin/env python3` by
  default. Change it with `--python`:

    ```console
    $ cli build notes.yaml -o dist --python "/usr/bin/env python3.12"
    ```

- Packages with compiled code are bundled for the platform and Python version you build on. Build
  on the same kind of system you will run on, or stick to pure-Python dependencies.
- Building the same manifest twice in the same environment gives an identical file.
- On first run, shiv unpacks the bundled packages to `~/.shiv`. Set the `SHIV_ROOT` environment
  variable to use another directory.

## script

```console
$ cli build notes.yaml -o dist --target script
+ notes built 📦
  dist/notes.py (single file, needs uv, or Python >=3.11 with typer==0.27.3 installed, 3.6 kB)
  run it with: ./dist/notes.py (or: uv run dist/notes.py)
  uv downloads the dependencies the first time the script runs
```

The result is the Python that `cli render` shows, with three things in front of it: a `#!` line, the
dependencies as [inline script metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/)
and a check of the Python version.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer==0.27.3",
# ]
# ///
```

- With uv installed, `./dist/notes.py` and `uv run dist/notes.py` both work. uv creates an environment
  with exactly the listed dependencies, downloads them on the first run and reuses them afterwards.
- Without uv, install the dependencies yourself and run `python dist/notes.py`.
- Nothing is downloaded at build time, so the build works offline and gives the same file every time.
- The file is plain text: it can be read, reviewed in a diff and edited. This is the target to pick
  when the reader should see what they run.
- `--python` replaces the `#!` line, for example `--python "/usr/bin/env python3"` for machines
  without uv.

## native

```console
$ cli build notes.yaml -o dist --target native
+ notes built 📦
  dist/notes (single file, needs nothing installed, runs on macOS arm64, 30.1 MB)
  run it with: ./dist/notes
  the first run unpacks its Python 3.11 (75.0 MB) into the user's data directory, without network access; later runs start right away
```

The result is one compiled executable. It contains a complete Python with the CLI and its
dependencies already installed, so the other machine needs neither Python nor network access.

### What the build machine needs

- **Rust.** `cargo` compiles the launcher. Install it from [rustup.rs](https://rustup.rs).
- **uv.** It downloads the standalone Python and installs the CLI into it. See
  [Installing uv](https://docs.astral.sh/uv/getting-started/installation/).
- **Network access**, for that Python, the dependencies and the source of the launcher.
- About a minute, and 700 MB of temporary disk space that is freed when the build ends.

When `cargo` or `uv` is missing, `cli build` says so and how to install it before it starts.

### How it is built

1. uv downloads a [standalone Python](https://github.com/astral-sh/python-build-standalone) of the
   version cliffy runs on.
2. The generated CLI is packaged as a wheel and installed into that Python together with its
   dependencies.
3. The result is embedded in [PyApp](https://ofek.dev/pyapp/), a launcher written in Rust, which is
   compiled into the executable.

### What happens on the other machine

- The executable runs on the operating system and CPU architecture it was built on. Build on each
  platform you want to support. The target is available on macOS and Linux.
- The first run unpacks the embedded Python, which takes a second or two, and then starts the CLI.
  Nothing is downloaded and nothing is installed with pip. Later runs only check that the directory
  exists.
- The Python is unpacked to `pyapp/<name>` in the user's data directory
  (`~/Library/Application Support` on macOS, `~/.local/share` on Linux), and a copy of the archive is
  kept in the cache directory (`~/Library/Caches/pyapp`, `~/.cache/pyapp`). Together that is about
  110 MB for a small CLI. Set `PYAPP_INSTALL_DIR_<NAME>`, with the name of the CLI in upper case, to
  unpack somewhere else. Delete the directory to reclaim the space; the next run unpacks it again.
- Every argument goes to your CLI. PyApp's own `self` commands are turned off.

`--python` does not apply to this target.

## Things that hold for every target

- Values taken from `env` in `vars` are fixed at build time. See
  [Vars and Jinja](vars-and-jinja.md#environment-variables).
- External commands that the CLI runs with `$` lines are not bundled. They have to exist on the
  other machine.

## Check before you ship

```console
$ cli test notes.yaml
$ cli build notes.yaml -o dist
$ ./dist/notes --help
```
