# Editor setup

cliffy publishes a [JSON schema](https://github.com/jaykv/cliffy/blob/main/examples/cliffy_schema.json)
for manifests. An editor that understands it completes keys, shows their descriptions and marks
mistakes while you type.

## VS Code

Install the
[YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml), then point
a manifest at the schema with a comment on its first line.

=== "Schema from GitHub"

    ```yaml
    # yaml-language-server: $schema=https://raw.githubusercontent.com/jaykv/cliffy/refs/heads/main/examples/cliffy_schema.json
    name: mycli
    version: 0.1.0
    ```

    This always uses the schema of the latest development version.

=== "Local schema"

    ```console
    $ cli init mycli --raw --json-schema
    + mycli.yaml
    + cliffy_schema.json
    ```

    This writes `cliffy_schema.json`, which matches your installed version, next to a new manifest
    that already has the comment:

    ```yaml
    # yaml-language-server: $schema=cliffy_schema.json
    ```

Other editors that use
[yaml-language-server](https://github.com/redhat-developer/yaml-language-server), such as Neovim and
Helix, read the same comment.

## Highlighting Python inside YAML

Run scripts are Python inside YAML strings, which editors show as plain text. The
[YAML Embedded Languages](https://marketplace.visualstudio.com/items?itemName=harrydowning.yaml-embedded-languages)
extension for VS Code adds syntax highlighting to those blocks.

## Checking from the command line

```console
$ cli validate mycli.yaml
Manifest mycli.yaml is valid
```

`cli validate` checks the same schema, plus the `requires` of the manifest and the code that is
generated from it. See the
[CLI reference](../reference/cli.md#cli-validate).
