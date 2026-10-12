# Vars and Jinja

A manifest is rendered as a [Jinja2](https://jinja.palletsprojects.com/) template before it is read
as YAML. `vars` supplies the values. Use them for anything you would otherwise repeat: file names,
URLs, defaults.

## Defining vars

```yaml
--8<-- "docs/snippets/vars.yaml:vars"
```

There are two kinds of value:

| You write | The var is |
|---|---|
| `app: shop` | The string `shop`. |
| `region: "{{ env['DEPLOY_REGION'] or 'eu-west-1' }}"` | A string computed by a Jinja expression. |
| `retries: {"3"}` | The Python expression `3`, an integer. |
| `workdir: {os.getcwd()}` | The Python expression `os.getcwd()`, evaluated each time the CLI starts. |

String values must be YAML strings, so quote numbers (`port: "8080"`) and any value that starts with
`{{`. Braces around a value turn it into a Python expression; quote it inside the braces when it
would otherwise not be a string, as in `{"3"}`.

## Using vars

Every var is available in two ways.

```yaml
--8<-- "docs/snippets/vars.yaml:use"
```

```console
$ cli run vars.yaml show
app=shop region=eu-west-1
app=shop retries=4 cwd=True
```

1. **As a placeholder.** `{{ app }}` is replaced with the value when the manifest is loaded. This
   works anywhere in the file: in scripts, help text, params, even in command names.
2. **As a Python variable.** The generated module defines `app = 'shop'`, so `run` scripts and
   functions can use `app` directly. Vars written with braces, like `retries` and `workdir`, are
   only useful this way.

A placeholder for a name that is not defined is replaced with nothing, without an error. If output
is unexpectedly empty, check the spelling with `cli render`.

## Environment variables

`env` holds the environment of the process that loads the manifest.

```yaml
vars:
  region: "{{ env['DEPLOY_REGION'] or 'eu-west-1' }}"
```

```console
$ DEPLOY_REGION=us-east-2 cli run vars.yaml show
app=shop region=us-east-2
app=shop retries=4 cwd=True
```

The value is read **when the manifest is loaded or built** and then fixed in the generated code. A
CLI installed with `cli load` keeps the value it saw at load time. To read the environment each
time a command runs, use Python instead:

```yaml
imports:
  - import os

commands:
  region: print(os.environ.get("DEPLOY_REGION", "eu-west-1"))
```

## Loops and conditions

Jinja statements such as `{% for %}` and `{% if %}` work as long as the file is still valid YAML
before rendering. Put them in YAML comments:

```yaml
--8<-- "docs/snippets/vars.yaml:loop"
```

```console
$ cli run vars.yaml deploy staging
deploying shop to staging in eu-west-1
$ cli run vars.yaml deploy production
deploying shop to production in eu-west-1
```

The loop produces one `deploy.<stage>` command per item.

## Literal braces

To keep double braces in your Python code, wrap them in `{% raw %}`:

```yaml
--8<-- "docs/snippets/vars.yaml:raw"
```

Single braces, as used in f-strings (`f"{name}"`), need no escaping.

## Limits

- Placeholders are resolved in one pass. A var whose value uses a Jinja expression, such as `region`
  above, should not be used inside the value of another var. Combine them in Python instead:
  `print(f"{app} in {region}")`.
- A string var is written into the generated code between single quotes, so its value cannot
  contain a single quote.
- Vars defined in an [include file](includes.md) can be used as placeholders only inside that file.

## The complete example

```yaml title="vars.yaml"
--8<-- "docs/snippets/vars.yaml"
```
