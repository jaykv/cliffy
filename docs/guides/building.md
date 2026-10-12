# Building executables

`cli build` turns a manifest into one executable file that you can copy to another machine. The
file is a Python [zipapp](https://docs.python.org/3/library/zipapp.html) built with
[shiv](https://shiv.readthedocs.io/): it contains the generated CLI, the framework it imports (Typer,
or rich-click with `use_click`) and the packages from `requires`. The target machine needs Python, and
nothing else.

## Build

```console
$ cli build notes.yaml -o dist
+ notes built 📦
  dist/notes (single file, needs Python >=3.10)
$ ./dist/notes --version
notes, 0.1.0
```

The file is named after the CLI. Without `-o`, it is written to the current directory. Several
manifests can be built in one call:

```console
$ cli build notes.yaml hello.yaml -o dist
```

You can also build a CLI that is already loaded, by name: `cli build notes -o dist`.

## Dependencies

Everything under `requires` is downloaded with pip and packed into the file:

```yaml
requires:
  - tabulate>=0.9.0
```

Unlike `cli load`, building from a manifest does not need those packages to be installed in your
environment. It does need network access, or a pip cache that has them.

The framework is added for you, pinned to the version installed next to cliffy unless `requires` names
it. Building the same manifest twice in the same environment gives an identical file. When a
dependency cannot be installed, the reason is printed and `cli build` exits with 1.

A file written in a [blueprint](../blueprints.md#building-a-single-file-executable)'s spec is built
the same way; the blueprint is applied at build time and is not shipped.

## Choosing the interpreter

The file starts with a `#!` line that selects the Python to run it. The default is
`/usr/bin/env python3`. Change it with `--python`:

```console
$ cli build notes.yaml -o dist --python "/usr/bin/env python3.12"
```

## Compatibility

- The executable does not need cliffy on the target machine.
- The line printed after a build says which Python the file needs. The file checks this when it
  starts and stops with a readable message on an unsupported interpreter.
- Packages with compiled code are bundled for the platform and Python version you build on. Build
  on the same kind of system you will run on, or stick to pure-Python dependencies.
- On first run, shiv unpacks the bundled packages to `~/.shiv`. Set the `SHIV_ROOT` environment
  variable to use another directory.
- Values taken from `env` in `vars` are fixed at build time. See
  [Vars and Jinja](vars-and-jinja.md#environment-variables).

## Check before you ship

```console
$ cli test notes.yaml
$ cli build notes.yaml -o dist
$ ./dist/notes --help
```
