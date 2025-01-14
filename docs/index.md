![Cliffy logo](images/logo.svg)

# Welcome to Cliffy Documentation

Cliffy is a powerful CLI framework that simplifies the creation of command-line interfaces using YAML-defined CLI manifests.

!!! example "Simplest example"
    1. Define a manifest
    ```yaml
    # hello.yaml
    name: hello
    version: 0.1.0

    commands:
    shell: 
        help: Print hello in shell
        run: $echo "hello from shell"
    python: print("hello from python")
    ```

    2. Load CLI
    ```
    $ cli load hello.yaml
    ```
    `hello.yaml` automatically gets parsed to generate a Typer CLI and gets loaded into the running Python environment.

    3. Run CLI directly

    ![hello -h](images/hello.png)

    For more examples, check [examples](examples/) directory.


!!! example "Build example"
    Also easy to build CLI into a single-file executable.

    1. Define a manifest
    ```yaml
    # requires.yaml
    name: requires
    version: 0.1.0

    requires:
    - requests >= 2.30.0
    - six

    imports:
    - import six

    commands:
    shell: $echo "hello from shell"
    python: print("hello from python")
    py: |
        if six.PY2:
            print("python 2")
        if six.PY3:
            print("python 3")
    ```

    1. Build CLI
    ```
    $ cli build requires.yaml -o dist
    ```

    A portable [zipapp](https://docs.python.org/3/library/zipapp.html) is generated containing the CLI and its dependencies.

    2. Run CLI
    ```
    ./dist/requires -h
    ```


- [Getting Started](getting-started.md)
- [Features](features.md)
- [Schema](schema.md)
- [Examples](https://github.com/jaykv/cliffy/tree/main/examples)


## Similar frameworks

- [Bashly](https://github.com/DannyBen/bashly) - An awesome YAML to Bash CLI builder
- [Fire](https://github.com/google/python-fire) - Python objects to CLI builder