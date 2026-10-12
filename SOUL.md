# The soul of cliffy

This document says what cliffy is for and how to decide what belongs in it.
It is written for anyone changing the project: the maintainer, a contributor, or a coding agent.
When a design question has no obvious answer, the answer should be derivable from here.

## The one-sentence version

**One readable file in, one runnable tool out.**

A cliffy manifest is a short YAML file that describes a command-line tool.
Cliffy turns it into a real CLI you can run now, test, document, and ship as a single file.

## Who it serves, all at once

Cliffy has three users, and a feature is only finished when it works for all three.

**The non-developer** has a task and no wish to learn packaging.
They should be able to read a manifest and know what the tool does, change a line and see the tool change,
and hand a colleague one file that just runs.
They never need to know what a virtualenv, an entry point, or a wheel is.

**The developer** has a script that deserves to be a tool and no time to write the scaffolding.
They want arguments, help text, subcommands, completion, tests and a build without boilerplate,
and they want to see and own exactly what gets generated.
They can leave whenever they like: the output is ordinary Python.

**The agent** is asked to produce or operate a tool on someone's behalf.
It needs a format small enough to write correctly on the first try, a schema to validate against,
errors precise enough to repair from without a human, and output a human can review in one diff.
A fifty-line manifest is reviewable. Five hundred lines of generated argparse is not.

These needs overlap more than they conflict. A format a non-developer can read is a format an agent can
write and a developer can review. That overlap is the project.

## Principles

### 1. The manifest is the source of truth

Everything about a tool lives in its manifest: commands, parameters, help, dependencies, examples and tests.
There is no second place to look and no hidden state that changes what a manifest means.
The same manifest produces the same CLI on every machine, every time.

### 2. Nothing is hidden

`cli render` shows the exact Python that will run. Generated code is plain, formatted, and readable
by someone who has never heard of cliffy. If cliffy disappeared tomorrow, every generated CLI would keep working
and every user could keep maintaining theirs by hand. No lock-in is a feature we test for, not a hope.

### 3. Errors point at what the user wrote

A failure is reported against the manifest, in the manifest's terms: which key, which command, what was expected,
what to change. A traceback into generated code or into cliffy internals is a bug in cliffy.
An error message is good when an agent can fix the manifest from the message alone
and a non-developer can tell which line to look at.

### 4. Simple things are one line; hard things are still possible

`hello: print("hi")` is a complete command. `name: str!` is a required parameter.
The shorthand exists so the common case reads like a sentence.
The escape hatch always exists too: any parameter can drop down to the full Typer or Click expression,
any command can be arbitrary Python or shell. Shorthand must never block the long form.

### 5. Bring your own vocabulary

Not every tool is best described as "commands and params". A team may think in terms of jobs, endpoints,
checklists, or MCP tools. A blueprint lets them define that vocabulary as their own typed YAML spec
and tell cliffy how it maps to a CLI. People then write in the words of their domain,
and everything else in cliffy (render, test, docs, build) works unchanged.
The core manifest is just the default blueprint.

### 6. Shipping is one command

A tool that only runs on its author's machine is not finished.
`cli build` produces one file to hand to someone else, and the author chooses the trade-off:

| Target | What you get | Needs on the other machine |
|---|---|---|
| script | A single `.py` file with its dependencies declared inline | Python and a script runner such as uv |
| zipapp (shiv) | A single `.pyz` executable with dependencies bundled | A compatible Python |
| native | A single compiled binary that brings its own Python | Nothing |

The manifest does not change between targets. Choosing how to ship is a flag, never a rewrite.

### 7. Every generated tool is a good citizen

A CLI built by cliffy should be easy for the next person or program to use:
complete `--help` at every level, a `--version`, meaningful exit codes, examples in the help,
and output that can be consumed by a script. Tools made with cliffy are themselves agent-friendly by default,
because the author already wrote the descriptions, types and examples in the manifest.

### 8. Tests live next to the thing they test

A manifest can carry its own tests, and `cli test` runs them. A tool that travels as one file
should be verifiable from that one file. This is also how an agent proves its work:
write the manifest, write the tests, run them, show the result.

### 9. The author is trusted; data is not

Run blocks are code and the manifest author is allowed to run code. That is the point.
But plain data in a manifest (a help string, a name, a default value) must never be able to change
what code is generated. Text is text. Cliffy generates code, so it holds itself to the standard of a compiler:
escape correctly, validate identifiers, and fail loudly instead of emitting something surprising.

### 10. Stay small

Cliffy is a generator, not a framework and not a runtime. Generated CLIs depend on Typer or Click, not on cliffy.
A feature that requires cliffy to be present when the tool runs needs a very good reason.
Prefer one obvious way over three configurable ways. Prefer deleting an option to documenting it.

## What cliffy is not

- **Not a new language.** The logic is Python and shell. YAML holds structure and words, not control flow.
- **Not a framework to build inside.** If a tool outgrows its manifest, `cli render` hands over the code and cliffy steps aside.
- **Not an AI product.** The AI commands are a convenience. The format is what makes cliffy useful to agents, and it works with no model at all.
- **Not magic.** Anything cliffy does can be seen, diffed, and reproduced by hand.

## How to decide

Before adding or changing something, ask:

1. Can a non-developer read the resulting manifest and say what the tool does?
2. Can an agent write it correctly from the schema and fix it from the error message?
3. Can a developer see exactly what it generates, and walk away with it?
4. Does the same manifest still build to every target?
5. Does it make the manifest shorter or clearer, or only cliffy bigger?

If a change helps one audience by making things worse for another, it is not ready.
Look for the version that serves all three; in this project there almost always is one.
