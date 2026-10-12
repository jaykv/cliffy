# Hot-reload dev loop

While you are writing a manifest, there are three ways to try your changes. They differ in how much
they install.

| Command | Installs the CLI | Use it for |
|---|---|---|
| `cli run notes.yaml -- <args>` | no | A quick one-off call. |
| `cli load notes.yaml`, then `cli update notes` | yes | Using the CLI by name; reload by hand. |
| `cli dev notes.yaml` | yes | Reloading automatically on every save. |

## `cli dev`

```console
$ cli dev notes.yaml
🔄 Watching notes.yaml for changes...
```

Leave this running and edit the manifest. Each time you save, cliffy regenerates and reloads the
CLI:

```console
✨ Reloaded notes CLI v0.1.0 ✨
```

In a second terminal, with the same environment active, the `notes` command always reflects the
last save. Stop the watcher with Ctrl+C.

The watcher follows every file the CLI is generated from: the manifest, the manifests it lists under
[`includes`](includes.md) and, for a file written in a [blueprint](../blueprints.md)'s spec, the
blueprint's Python file. Saving any of them reloads the CLI.

!!! note
    Nothing is loaded until the first change. Save the file once, or run `cli load notes.yaml`
    before starting, to get the command right away.

### Run a command on every reload

`--run-cli` runs your CLI after each reload with the arguments that follow. It is a quick way to
re-check one command while you work on it:

```console
$ cli dev notes.yaml --run-cli tags list
🔄 Watching notes.yaml for changes...

✨ Reloaded notes CLI v0.1.0 ✨
general (1)
travel (1)
```

Put `--` before the arguments when they include options:

```console
$ cli dev notes.yaml --run-cli -- list --tag home
$ cli dev notes.yaml --run-cli -- --help
```

A mistake in the manifest prints an error in the watcher's terminal. Fix the file and save again;
the watcher keeps running.

## Managing loaded CLIs

```console
$ cli list            # what is loaded, from which manifest, and how long ago
$ cli info notes      # version, requirements and the stored manifest
$ cli update notes    # regenerate from the manifest path recorded at load time
$ cli remove notes    # uninstall
$ cli remove-all      # uninstall everything cliffy loaded
```

`cli ls`, `cli reload`, `cli rm` and `cli rm-all` are aliases for these. Details are in the
[CLI reference](../reference/cli.md).

Loaded CLIs belong to the Python environment cliffy is installed in. They are available whenever
that environment is active and disappear with it.
