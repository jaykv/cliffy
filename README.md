# commandeer
$ cli generate --dynamic --from-yaml


# Usage
`commandeer generate <manifest>`

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

2. Generate CLI
```
$ commandeer generate hello.yaml
```

3. Run CLI directly
![hello-demo](docs/images/hello.png)


# Development
```
poetry shell
commandeer -h
```
