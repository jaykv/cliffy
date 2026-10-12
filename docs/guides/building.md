# Building executables

`cli build` turns a manifest into one executable file that you can copy to another machine. The
file is a Python [zipapp](https://docs.python.org/3/library/zipapp.html) built with
[shiv](https://shiv.readthedocs.io/): it contains the generated CLI, Typer and the packages from
`requires`. The target machine needs Python, and nothing else.

## Build

```console
$ cli build notes.yaml -o dist
+ notes built 📦
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

Manifests that set `use_click: true` must list `rich-click` under `requires`. See
[Click and Typer backends](backends.md#building).

## Choosing the interpreter

The file starts with a `#!` line that selects the Python to run it. The default is
`/usr/bin/env python3`. Change it with `--python`:

```console
$ cli build notes.yaml -o dist --python "/usr/bin/env python3.12"
```

## Compatibility

- The executable does not need cliffy on the target machine.
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
