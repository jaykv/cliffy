# Includes and merging

`includes` merges other YAML files into a manifest. Use it to share functions, types and commands
between several CLIs.

## An include file

An include file looks like a manifest without `name` and `version`:

```yaml title="shared/common.yaml"
--8<-- "docs/snippets/shared/common.yaml"
```

It may contain `commands`, `functions`, `imports`, `types`, `vars`, `requires`, `cli_options` and
`tests`. In an include file, `functions` must be a list.

## Using it

```yaml title="ops.yaml"
--8<-- "docs/snippets/includes.yaml"
```

```console
$ cli run ops.yaml health api
{"service": "api", "status": "ok"}
$ cli run ops.yaml restart api
{"action": "restart", "service": "api"}
$ cli run ops.yaml whoami
platform
```

`restart` is defined in `ops.yaml` and uses the `Service` type and the `as_json` function from the
include. `health` comes entirely from the include.

!!! note "Paths are relative to the manifest"
    `shared/common.yaml` is looked up next to the manifest that includes it first, and in the current
    working directory after that. A manifest that includes itself, directly or through another file,
    is reported as a circular include. `cli dev` watches included files too.

## How files are merged

All included files are merged together first. The result is then merged into your manifest.

| Kind of value | Rule | Example |
|---|---|---|
| Mapping | Merged key by key, at every level. | `commands`, `types`, `vars`, and the keys of a single command |
| List | Items from the include are added, without duplicates. | `requires`, `tests`, `functions` and `imports` when both are lists |
| Anything else | The value in your manifest wins. | a command's `help` or `run` |

In the example, both files define `whoami`. The command keeps its `run` script from the include and
takes `help` from `ops.yaml`.

Two details to keep in mind:

- When the same key holds a list in one file and a block of text in the other, your manifest's value
  is kept and the include's is dropped. Write `imports` as a list in both files if both need imports.
- Include files are merged in the order they are listed. When two of them set the same key to
  different values, the one listed first wins.

## Variables in include files

Each file is rendered on its own. `{{ team }}` works inside `shared/common.yaml`, where `team` is
defined, but not inside `ops.yaml`. The Python variable `team` is available to every command in the
merged CLI, which is why `whoami` can print it. See [Vars and Jinja](vars-and-jinja.md).
