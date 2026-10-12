# AI commands

Cliffy includes AI-powered commands that generate manifests and answer questions about cliffy. They live in the `cli ai` command group; every option is listed in the [CLI reference](reference/cli.md#cli-ai).

The AI commands are a convenience. Nothing else in cliffy needs a model: a manifest written by hand, or by an agent from the [manifest schema](reference/manifest.md), works the same way.

!!! note
    Requires the `ai` extra: `pip install "cliffy[ai]"`. See [Installation](installation.md#extras).
    Without it, `cli ai` commands exit with an install hint; the rest of cliffy is unaffected.

## Choosing a model

The AI commands are built on [Pydantic AI](https://pydantic.dev/docs/ai/models/overview/) and work with any model it supports. Models are named `provider:model`, and each provider reads its API key from its usual environment variable.

The model is picked in this order:

1. the `--model` / `-m` option
2. the `CLIFFY_AI_MODEL` environment variable
3. a default for the first provider that has an API key set:

    | API key | Default model |
    |---|---|
    | `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) | `google:gemini-flash-latest` |
    | `ANTHROPIC_API_KEY` | `anthropic:claude-sonnet-5-5` |
    | `OPENAI_API_KEY` | `openai:gpt-5.4-mini` |

```bash
# use the default model of the provider whose key is set
export ANTHROPIC_API_KEY='your-api-key'
cli ai generate mycli "Create a todo app"

# pick a model for one command
cli ai generate mycli "Create a todo app" --model openai:gpt-5.5

# or for the whole shell session
export CLIFFY_AI_MODEL=google:gemini-2.5-pro
```

!!! tip
    Use `--preview` to print the fully constructed prompt instead of sending it. This needs neither a model nor an API key.

## Generating a manifest

Generate complete CLI manifests from natural language descriptions:

```bash
cli ai generate mycli "Create a CLI for managing docker containers with commands to list, start, stop and remove containers"
cli load mycli.yaml
```

The model's reply is validated before anything is written: it has to be valid YAML, match the manifest schema, and produce a CLI that is valid Python. A reply that fails is sent back to the model together with the reason, up to `--retries` times (default 2). If no valid manifest comes back, the command fails and writes nothing.

`mycli.yaml` is written to the current directory, or to `--output-dir`. An existing file is only replaced with `--force`.

!!! warning
    Validation checks that the manifest loads, not that the commands do what you asked. Read the generated run blocks before running the CLI.

## Asking questions

Get AI assistance for understanding and working with cliffy:

```bash
cli ai ask "How do I create nested subcommands?"
```

The question is answered from a reference built from your installed cliffy version: its command list, the annotated `cli init` template and the manifest JSON schema.

You can also get targeted help about specific CLIs by referencing a manifest or a loaded CLI:

```bash
cli ai ask --cli mycli.yaml "How do I add input validation to the start command?"
```

The answer is printed to stdout and token usage to stderr, so the answer can be redirected to a file.

## Giving cliffy's documentation to an agent

`cli ai llms-txt` prints cliffy's documentation as a single text file in the [llms.txt](https://llmstxt.org/) layout: the quickstart, the guides and the CLI and manifest references.

```bash
cli ai llms-txt > cliffy-llms.txt
```

The file is bundled with the installed package, so it needs no network access, no model and no `ai` extra, and it always describes the version you have installed. Put it in the context of a coding agent and it can write and fix manifests without looking anything up.

The same file is published with the documentation at [`/llms.txt`](llms.txt).
