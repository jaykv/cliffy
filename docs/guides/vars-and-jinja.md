# Vars and Jinja

A manifest is rendered as a [Jinja2](https://jinja.palletsprojects.com/) template before it is read
as YAML. `vars` supplies the values. Use them for anything you would otherwise repeat: file names,
URLs, defaults.

## Defining vars

```yaml
--8<-- "docs/snippets/vars.yaml:vars"
```

There are three kinds of value:

| You write | The var is |
|---|---|
| `app: shop` | The string `shop`. |
| `region: "{{ env['DEPLOY_REGION'] or 'eu-west-1' }}"` | A string computed by a Jinja expression. |
| `image: "registry.example.com/{{ app }}:{{ region }}"` | A string built from other vars. |
| `retries: 3` | The integer `3`. Numbers and booleans keep their type. |
| `workdir: {os.getcwd()}` | The Python expression `os.getcwd()`, evaluated each time the CLI starts. |

Quote a string value that starts with `{{`, and quote a number that should stay text
(`zip_code: "02134"`). Braces around a value turn it into a Python expression.

A var name becomes a Python variable, so it has to be a valid identifier: `data_file`, not
`data-file`. Names the generated code uses itself, such as `cli` and `typer`, are rejected too.

Vars can use each other in any order. cliffy resolves them before the rest of the file, and reports
vars that refer to each other in a circle:

```text
~ error loading manifest: vars.yaml: vars reference each other in a circle: a -> b -> a. A var cannot be built from itself.
```

## Using vars

Every var is available in two ways.

```yaml
--8<-- "docs/snippets/vars.yaml:use"
```

```console
$ cli run vars.yaml show
app=shop region=eu-west-1 image=registry.example.com/shop:eu-west-1
app=shop retries=4 cwd=True
```

1. **As a placeholder.** `{{ app }}` is replaced with the value when the manifest is loaded. This
   works anywhere in the file: in scripts, help text, params, even in command names.
2. **As a Python variable.** The generated module defines `app = 'shop'`, so `run` scripts and
   functions can use `app` directly, and `retries = 3` as a number. A var written with braces, like
   `workdir`, is only useful this way.

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
app=shop region=us-east-2 image=registry.example.com/shop:us-east-2
app=shop retries=4 cwd=True
```

`env` can be used in `vars` and anywhere else in the file.

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

## Comments are part of the template

The whole file is rendered, YAML comments included. That is what makes the loop above possible, and
it means that double braces in a comment are read as a placeholder too. A comment such as
`# use {{ }} for placeholders` is a Jinja syntax error, which is reported with its line:

```text
~ error loading manifest: vars.yaml, line 12: Jinja syntax error: Expected an expression, got 'end of print statement'
    # use {{ }} for placeholders
  The whole file is a Jinja template, comments included. To keep braces as text, wrap them in {% raw %} and {% endraw %}.
```

Write the comment without double braces, or wrap them in `{% raw %}`.

## Limits

- Vars defined in an [include file](includes.md) can be used as placeholders only inside that file.

## The complete example

```yaml title="vars.yaml"
--8<-- "docs/snippets/vars.yaml"
```
