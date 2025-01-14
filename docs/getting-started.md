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
    params:
      - name: str = typer.Option("World", "--name", "-n", help="Name to greet")
    run: |
      print(f"Hello, {name}!")
```

This manifest defines a CLI named `hello` with a single command `hello` that takes an optional `--name` argument.

## Running Your CLI

To run your CLI, use the `cli run` command followed by the path to your manifest file:

```bash
$ cli run hello.yaml -- hello --name "Your Name"
```

This will output:

```
Hello, Your Name!
```

### Loading CLIs

You can load the CLI using the `cli load` command to avoid needing to prefix `cli run hello.yaml` for each trigger:

```bash
$ cli load hello.yaml
```

This command loads the generated CLI into the current Python environment. You can then run the CLI directly from the terminal by its name:

```bash
$ hello -h
```

### Building CLIs

To build a CLI into a portable zipapp, you can run the `cli build` command:

```bash
$ cli build hello.yaml -o dist
```

This command builds a portable zipapp containing the CLI and its package requirements, outputting it to the `dist` directory. You can then run the built CLI:

```bash
$ ./dist/hello -h
```

## Next Steps

This is just a basic example. Cliffy supports many more features, such as:

-   Defining types for arguments and options.
-   Using variables and functions in your manifest.
-   Creating complex command structures.
-   Running shell commands.
-   Testing your CLI.

Explore the [Features](features.md) section to learn more about these capabilities.