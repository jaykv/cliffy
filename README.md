# commandeer
$ cli generate --dynamic --from-yaml

## Features
* Generate and load YAML-defined CLIs
* Easily sharable- just send the CLI manifest and load it wherever
* Dynamic abstractions to streamline CLI building
* Shell and Python script support


## Usage
`commandeer load <manifest>`

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
$ commandeer load hello.yaml
```

3. Run CLI directly
![hello-demo](docs/images/hello.png)


## Development
```
poetry shell
commandeer -h
```
