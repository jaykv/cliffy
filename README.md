# cliffy :mountain:
YAML-defined CLI generator and manager

## Features
* Build and generate YAML-defined CLIs
* Dynamic abstractions to rapidly build and test CLIs
* Manage CLIs- load, enable, disable, update, and remove
* Easily shareable- just send the manifest and load it
* Built-in shell and Python script support


## Usage
* `cli init <cli name>`: Generate a template CLI manifest
* `cli load <manifest>`: Add a new CLI based on the manifest
* `cli render <manifest>`: Render the YAML manifest into executable code
* `cli list`: Ouput a list of loaded CLIs 
* `cli disable <cli name>`: Disable a CLI
* `cli enable <cli name>`: Enable a disabled CLI
* `cli unload <cli name>`: Remove a loaded CLI

### Example:

1. Define a manifest
```yaml
# hello.yaml
name: hello
version: 0.1.0

commands:
  bash: $echo "hello from bash"
  python: print("hello from python")
```

2. Load CLI
```
$ cli load hello.yaml
```

3. Run CLI directly
![hello-demo](docs/images/hello.png)


## Development
```
poetry shell
cli -h
```
