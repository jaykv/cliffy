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

`$` lines work in `run`, `pre_run`, `post_run`, in callbacks, in `functions` written as a list, and
as steps in [`tests`](testing.md#shell-steps). Run `cli render` to see the translation.

## Using Python values

`f{expression}` inserts the value of a Python expression into the command. The value is passed as a
single argument, whatever it contains: spaces, quotes and `;` are just text.

```yaml
--8<-- "docs/snippets/shell.yaml:interpolate"
```

```console
$ cli run shell.yaml say "two words"
two words 9
```

Everything an f-string accepts after the expression works too, and `f{ }` can be used inside
quotes:

```yaml
--8<-- "docs/snippets/shell.yaml:format"
```

### Double braces are Jinja's

pybash also has a `{{ expression }}` form, which inserts `str(expression)`. In a manifest, cliffy
renders [Jinja](vars-and-jinja.md) first, so `{{ name }}` is replaced with a *var* when the manifest
is loaded and never reaches pybash. That is what you want for vars:

```yaml
vars:
  data_file: tasks.json
commands:
  backup: $ cp {{ data_file }} {{ data_file }}.backup
```

For a value that only exists when the command runs, such as a param, use `f{ }`. If you prefer the
double-brace form, put the lines in a Jinja `raw` block so they are left alone:

```yaml
--8<-- "docs/snippets/shell.yaml:braces"
```

To write the markers themselves as text, escape them: `\f{` and, inside a `raw` block, `\{{`.

## Capturing output

Assign a shell line to a variable, or wrap it in parentheses, to get its output as `bytes`.
`$(command)` does the same in the middle of an expression:

```yaml
--8<-- "docs/snippets/shell.yaml:capture"
```

```console
$ cli run shell.yaml upper
CAPTURED
$ cli run shell.yaml words
3 words
```

A capture that is not wrapped in brackets runs to the end of the line.

## Pipes and redirection

Pipes and redirects are carried out by the generated CLI itself, without a shell:

```yaml
--8<-- "docs/snippets/shell.yaml:pipes"
```

| Operator | Meaning |
|---|---|
| `a | b` | Pipe the output of `a` into `b` |
| `a |& b` | Pipe output and errors |
| `< file` | Read input from a file |
| `> file`, `>> file` | Write or append output |
| `2> file`, `2>> file` | Write or append errors |
| `&> file`, `&>> file` | Write or append both |
| `2>&1`, `>&2` | Send errors to the output, or the output to the errors |

## Chaining commands

`&&` runs the next command when the previous one succeeded, `||` when it failed, and `;` in either
case:

```yaml
--8<-- "docs/snippets/shell.yaml:operators"
```

Capturing a chain captures the output of every command that ran.

## Long commands and comments

A `$` or `>` line that ends with a backslash continues on the next line. An unquoted `#` starts a
comment that runs to the end of the line:

```yaml
--8<-- "docs/snippets/shell.yaml:layout"
```

A captured command (`out = $ ...`) has to fit on one line.

## When you need a real shell

`$` lines never expand glob patterns (`*.txt`), `~` or environment variables (`$HOME`), and they do
not support background jobs (`&`) or here-documents (`<<`). For those, start the line with `>`
instead of `$`. The line is handed to the shell as written:

```yaml
--8<-- "docs/snippets/shell.yaml:shell"
```

This becomes `subprocess.run("ls *.txt", shell=True)`. A one-line command that starts with `>` must
be quoted, because `>` also has a meaning in YAML.

Values inserted with `f{ }` are quoted for the place they appear in, so a value is always one word
of data and never shell syntax. Here `name` can be `; rm -rf ~` and nothing is removed:

```yaml
--8<-- "docs/snippets/shell.yaml:shell-values"
```

`{{! expression }}` is the exception: it splices the value in unquoted, so that it can be a glob
pattern or several arguments. Like every double-brace form it has to sit in a `raw` block.

!!! danger "Never pass user input to `{{! }}`"
    A spliced value is interpreted by the shell. A parameter value such as `; rm -rf ~` would be
    executed. Use `f{ }` for anything that comes from a user, and prefer `$` lines, which have no
    shell to inject into. See the Python documentation on
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

A shell line that cannot be translated is reported when the manifest is loaded, with the command it
is in, the line and the column:

```console
$ cli load deploy.yaml
~ error in deploy.yaml: command `ship`, run, line 2, column 11: running in the background with & is not supported in a $ command; use a > shell command
    $ sleep 5 &
              ^ 💔
```

## Things to know

- Output of `$` lines goes straight to the terminal. It is not part of `result.output` in
  [manifest tests](testing.md); capture it and `print` it if you want to assert on it.
- A CLI that only uses plain commands imports nothing but `subprocess`. Pipes, redirects, chains and
  values in `>` lines go through a small helper, `pybash.runtime`, which the generated code imports
  as `_pybash`. `cli build` copies that helper into the file it builds, so a built CLI does not need
  pybash.
- Quoting follows POSIX shell rules: single quotes are literal, double quotes allow `\"` and `\\`,
  and a backslash escapes the next character. Quote or escape an operator to pass it as text:
  `$ echo 'a && b' \| c`.

## The complete example

```yaml title="shell.yaml"
--8<-- "docs/snippets/shell.yaml"
```
