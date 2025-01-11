# Getting Started with Cliffy

This guide will walk you through the basics of setting up and using Cliffy to create your own CLI tools.

## Installation

To get started with Cliffy, you'll need to install it using pip:

```bash
$ pip install cliffy
$ cli --help
```

You can also use uv to run cliffy directly with:
```bash
$ uvx cliffy --help
```

## Creating Your First CLI

Let's create a simple "hello" CLI. Create a file named `hello.yaml` with the following content:

```yaml
name: hello
version: 0.1.0
help: A simple CLI that greets the user.

commands:
  hello:
    help: Greet the user
    args:
      - name: str = typer.Option("World", "--name", "-n", help="Name to greet")
    run: |
      print(f"Hello, {name}!")
```

This manifest defines a CLI named `hello` with a single command `hello` that takes an optional `--name` argument.

## Running Your CLI

To run your CLI, use the `cliffy` command followed by the path to your manifest file:

```bash
cli run cliffy.yaml hello --name "Your Name"
```

This will output:

```
Hello, Your Name!
```

## Next Steps

This is just a basic example. Cliffy supports many more features, such as:

-   Defining types for arguments and options.
-   Using variables and functions in your manifest.
-   Creating complex command structures.
-   Running shell commands.
-   Testing your CLI.

Explore the [Features](features.md) section to learn more about these capabilities.