# Testing manifests

A manifest can carry its own tests. Each test runs a command of your CLI and checks the result with
Python assertions. `cli test` runs them without loading or building anything.

## Writing tests

```yaml
--8<-- "docs/snippets/testing.yaml:tests"
```

```console
$ cli test testing.yaml
✨ Invoking tests ✨

🪄 > counter show

⚗️ >
0


✅ 1 of 5

...

💚 All tests passed!
```

### Test cases

A test case is a one-key mapping:

```yaml
- <command line>: <assertion code>
```

The command line is everything you would type after the CLI's name. It is split like a shell would
split it, so quotes work: `add "buy milk" --tag home`.

The assertion code is Python. Two variables are available:

| Variable | What it is |
|---|---|
| `result` | The outcome of the command. Use `result.output` (everything the command printed), `result.exit_code` and `result.exception`. |
| `result_text` | `result.output` with leading and trailing whitespace removed. |

Use `assert` statements. A test passes when the code runs without raising.

### Shell steps

An entry that is a plain string is a setup or cleanup step, not a test case. It must start with `$`
or `>` and follows the rules of [shell commands](shell-commands.md): `$` runs the command directly,
`>` runs it through a shell (needed for glob patterns such as `counter.*`). Quote an entry that
starts with `>`.

Entries run from top to bottom, so order the steps and cases accordingly.

## Running tests

```console
$ cli test testing.yaml
$ cli test testing.yaml --exitfirst
```

`--exitfirst` (or `-x`) stops at the first failing test.

A failing assertion is reported with its line:

```text
💔 AssertionError: (line 1) > assert result.output == "1\n"
```

So is an assertion that raises something else, or that is not valid Python:

```text
💔 NameError: name 'reslt' is not defined (line 1) > assert reslt.exit_code == 0
```

When the command itself raises, the exception is reported against the manifest: the command, the
exception, and the line of the `run`, `pre_run` or `post_run` block it was raised on.

```text
💥 command `add` raised KeyError: 'notes'
    run, line 2: data["notes"].append(text)
```

No Python traceback is printed. The assertions still run, so a test can expect the exception with
`assert isinstance(result.exception, KeyError)`. To see the full traceback of the command as well:

```console
$ cli test testing.yaml --traceback
```

The run ends with one of three messages:

| Last line | Meaning | Exit code |
|---|---|---|
| `💚 All tests passed!` | Every test case passed. | 0 |
| `💛 Some tests failed :(` | At least one passed and at least one failed. | 1 |
| `All tests failed 💔` | No test case passed. | 1 |

The exit code is 0 only when every test case passed, so a CI job can run `cli test mycli.yaml` as a
step of its own.

## Things to know

- **Colors and styles are removed from the output** before your assertions run, so a test gives the
  same result in a terminal and on a CI system.
- **Tests run in the current directory** and are not isolated from each other. A command that
  writes a file really writes it. Clean up with shell steps, as the example does.
- **Output of `$` lines is not captured.** It goes to the terminal and is not in `result.output`.
  Assert on the exit code, or capture the output in Python and `print` it. See
  [Shell commands](shell-commands.md#capturing-output).
- **Keep `: ` out of one-line assertions.** YAML reads a colon followed by a space as the end of a
  key, so `- show: assert result.output == "count: 0\n"` is a YAML error. Use a block:

    ```yaml
    - show: |
        assert result.output == "count: 0\n"
    ```

- **The counter counts test cases.** `✅ 2 of 5` is the second test case of five. Shell steps are run
  but not counted, and a failed case keeps its number.
- **Shell steps are not checked.** A step that exits with an error does not fail the run. Assert on
  the state it should have produced in the next test case. A step whose program cannot be started at
  all (it does not exist) ends the run with an error.

## The complete example

```yaml title="testing.yaml"
--8<-- "docs/snippets/testing.yaml"
```
