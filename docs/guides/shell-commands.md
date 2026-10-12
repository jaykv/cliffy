# Shell commands

In any script, a line that starts with `$` is run as an external command. cliffy uses
[pybash](https://github.com/jaykv/pybash) to translate these lines into `subprocess` calls, so you
can move between Python and shell freely.

## The basics

```yaml
--8<-- "docs/snippets/shell.yaml:basic"
```

`$ echo "then shell"` becomes `subprocess.run(["echo", "then shell"])`. The command is split into
arguments the way a shell would split it, and is then started directly, without a shell in between.
Shell lines follow Python indentation, so they can sit inside `if` blocks and loops.

`$` lines work in `run`, `pre_run`, `post_run`, in `functions` written as a list, and as steps in
[`tests`](testing.md#shell-steps). Run `cli render` to see the translation.

## Using Python values

`f{expression}` inserts the value of a Python expression into the command. The value is passed as a
single argument, even when it contains spaces.

```yaml
--8<-- "docs/snippets/shell.yaml:interpolate"
```

```console
$ cli run shell.yaml say "two words"
two words 9
```

## Capturing output

Assign a shell line to a variable, or wrap it in parentheses, to get its output as `bytes`:

```yaml
--8<-- "docs/snippets/shell.yaml:capture"
```

```console
$ cli run shell.yaml upper
CAPTURED
```

## Pipes and redirection

`|`, `>`, `>>` and `<` are supported without a shell:

```yaml
--8<-- "docs/snippets/shell.yaml:pipes"
```

## When you need a real shell

Glob patterns (`*.txt`), `&&`, environment variable expansion and other shell features need a shell.
Start the line with `>` instead of `$`:

```yaml
--8<-- "docs/snippets/shell.yaml:shell"
```

This becomes `subprocess.run("ls *.txt", shell=True)`. A one-line command that starts with `>` must
be quoted, because `>` also has a meaning in YAML.

!!! danger "Never build `>` lines from user input"
    With `shell=True`, the text is interpreted by the shell. A parameter value such as
    `; rm -rf ~` would be executed. Prefer `$`, which passes values as arguments. See the Python
    documentation on
    [subprocess security](https://docs.python.org/3/library/subprocess.html#security-considerations).

## Errors

A shell line that fails does not stop the script. Check the result yourself when it matters:

```yaml
--8<-- "docs/snippets/shell.yaml:errors"
```

Two exceptions:

- A command that does not exist raises `FileNotFoundError`.
- A captured command (`out = $ ...`) raises `subprocess.CalledProcessError` when it exits with a
  non-zero status.

## Things to know

- Output of `$` lines goes straight to the terminal. It is not part of `result.output` in
  [manifest tests](testing.md); capture it and `print` it if you want to assert on it.
- pybash's `{{ }}` interpolation is not available in manifests, because double braces are handled
  by [Jinja](vars-and-jinja.md). Use `f{...}`.

## The complete example

```yaml title="shell.yaml"
--8<-- "docs/snippets/shell.yaml"
```
