# Generating docs

`cli docs` writes a reference page for your CLI from its manifest: the description, every command
with its params and aliases, and the examples you provide.

## Add examples

`examples` is a list of command lines with a description each. They are part of the documentation
`cli docs` writes, and the generated CLI shows them at the end of its own `--help`:

```text
 Examples:

 $ notes add "buy milk" --tag home  # Add a note tagged home.

 $ notes ls --tag home  # Show only the notes tagged home.
```

Write an example as you would type it, starting with the name of the CLI. It is shown as written:
quotes, brackets and backslashes are not interpreted. The help of a single command does not repeat
the examples.

```yaml
--8<-- "docs/snippets/notes.yaml:examples"
```

Give every example a `description`. A plain string is accepted too, but is rendered with `None` in
place of the description.

## Generate

```console
$ cli docs notes.yaml
+ notes.md
```

| Option | Values | Default |
|---|---|---|
| `--format`, `-f` | `md`, `rst`, `html` | `md` |
| `--output-dir`, `-o` | an existing directory | the current directory |

```console
$ mkdir -p site
$ cli docs notes.yaml --format html --output-dir site
+ notes.html
```

## What the page contains

For the `notes` manifest from the [Quickstart](../quickstart.md), the Markdown output starts like
this:

````markdown
# notes v0.1.0

Keep short notes in a JSON file

## Commands

### add
Add a note

Parameters:
- text: Text
- tag: Tag

### list|ls
List notes, optionally filtered by tag

Parameters:
- --tag: str (default: "")

Aliases: ls
````

and ends with the examples:

````markdown
## Examples

```bash
notes add "buy milk" --tag home
```
Add a note tagged home.
````

- Commands are listed in manifest order, under the key they have in the manifest.
- Shorthand and explicit params are listed with their type; explicit params also show their help
  text. Generic params (plain strings) are left out.
- Pass a manifest path or the name of a loaded CLI. A loaded CLI is documented from the manifest path
  recorded by `cli load`.
