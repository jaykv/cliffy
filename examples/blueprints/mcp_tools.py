"""A realistic blueprint: an MCP tool server.

The spec describes tools the way the Model Context Protocol does: a name, a description, typed parameters
and a Python body. The generated CLI has

* one command per tool, to call it from a shell: ``text-tools format-text " hi " --trim``
* ``tools``, which prints the tool definitions as MCP ``tools/list`` JSON
* ``serve``, a dependency-free MCP server over stdio (JSON-RPC 2.0, one message per line)

    cli run examples/blueprints/text-tools.yaml -- count-words "one two three"
    cli build examples/blueprints/text-tools.yaml -o dist   # single file, serves MCP with `dist/text-tools serve`
"""

import re
import textwrap
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from cliffy.blueprint import Blueprint
from cliffy.manifest import CLIManifest, Command, CommandParam, RunBlock

# names the generated module already uses: built-in commands, imports and the typer app
RESERVED_NAMES = {"serve", "tools", "main", "cli", "json", "sys", "typer", "subprocess"}
PYTHON_TYPES = {"string": "str", "integer": "int", "number": "float", "boolean": "bool", "array": "list[str]"}

# Shared by every generated server. Kept free of third-party imports so that a built CLI stays small.
RUNTIME = '''
def _describe_tools():
    return [
        {"name": name, "description": tool["description"], "inputSchema": tool["inputSchema"]}
        for name, tool in TOOLS.items()
    ]


def _render_result(value):
    return value if isinstance(value, str) else json.dumps(value, indent=2, default=str)


def _call_tool(name, arguments):
    if name not in TOOLS:
        raise KeyError(f"unknown tool: {name}")
    schema = TOOLS[name]["inputSchema"]
    unknown = sorted(set(arguments) - set(schema["properties"]))
    missing = [key for key in schema["required"] if key not in arguments]
    if unknown or missing:
        raise ValueError(f"invalid arguments for {name}: missing {missing}, unknown {unknown}")
    return _render_result(TOOLS[name]["function"](**arguments))


def _error(message_id, code, text):
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": text}}


def _handle_message(message):
    """Answer one JSON-RPC message. Returns None for notifications, which get no reply."""
    if isinstance(message, list):
        # MCP has no batches since revision 2025-06-18: one message per line
        return _error(None, -32600, "Invalid Request: batch messages are not supported, send one message per line")
    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid Request: a message must be a JSON object")

    method, params, message_id = message.get("method"), message.get("params"), message.get("id")
    if not isinstance(method, str):
        # a response to a request is not answered: this server never sends one
        if "result" in message or "error" in message:
            return None
        return _error(message_id, -32600, "Invalid Request: `method` must be a string")
    if message_id is None:
        return None
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _error(message_id, -32602, "Invalid params: `params` must be an object")

    if method == "initialize":
        result = {
            "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": _describe_tools()}
    elif method == "tools/call":
        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return _error(message_id, -32602, "Invalid params: `arguments` must be an object")
        try:
            text, failed = _call_tool(params.get("name"), arguments), False
        except Exception as e:
            text, failed = f"{type(e).__name__}: {e}", True
        result = {"content": [{"type": "text", "text": text}], "isError": failed}
    else:
        return _error(message_id, -32601, f"Method not found: {method}")
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _serve():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            reply = _error(None, -32700, "Parse error")
        else:
            reply = _handle_message(message)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\\n")
            sys.stdout.flush()
'''


class ToolParameter(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", description="Name of the parameter, a Python identifier.")
    type: Literal["string", "integer", "number", "boolean", "array"] = Field(
        default="string", description="JSON schema type. An `array` holds strings."
    )
    description: str = Field(default="", description="What the parameter means, shown to the model and in --help.")
    required: bool = Field(default=False, description="Required parameters become positional arguments.")
    default: Any = Field(default=None, description="Value used when an optional parameter is not given.")

    @model_validator(mode="after")
    def check_shape(self) -> "ToolParameter":
        if self.required and self.default is not None:
            raise ValueError("a required parameter cannot have a default")
        if self.required and self.type == "boolean":
            raise ValueError("a boolean parameter is a flag and cannot be required")
        return self

    @property
    def python_type(self) -> str:
        return PYTHON_TYPES[self.type]

    @property
    def python_default(self) -> str:
        if self.type == "boolean":
            return repr(bool(self.default))
        return repr(self.default)

    def to_json_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": self.type}
        if self.type == "array":
            schema["items"] = {"type": "string"}
        if self.description:
            schema["description"] = self.description
        return schema

    def to_param(self) -> CommandParam:
        # the generated code puts help in double quotes
        help_text = self.description.replace('"', "'")
        if self.required:
            return CommandParam(name=self.name, type=self.python_type, required=True, help=help_text)

        default = self.default if self.type == "string" else self.python_default
        if self.default is None and self.type != "boolean":
            default = None
        return CommandParam(
            name=f"--{self.name.replace('_', '-')}", type=self.python_type, default=default, help=help_text
        )


class Tool(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", description="Name of the tool, as the model calls it.")
    description: str = Field(description="What the tool does, shown to the model and in --help.")
    parameters: list[ToolParameter] = Field(default=[], description="Inputs of the tool.")
    run: str = Field(description="Python body of the tool. Parameters are local variables. Return the result.")

    @field_validator("name")
    @classmethod
    def not_reserved(cls, name: str) -> str:
        if name in RESERVED_NAMES:
            raise ValueError(f"`{name}` is a reserved name")
        return name

    @field_validator("parameters")
    @classmethod
    def unique_parameters(cls, parameters: list[ToolParameter]) -> list[ToolParameter]:
        names = [parameter.name for parameter in parameters]
        if duplicates := sorted({name for name in names if names.count(name) > 1}):
            raise ValueError(f"duplicate parameter names: {', '.join(duplicates)}")
        return parameters

    @property
    def function_name(self) -> str:
        return f"_tool_{self.name}"

    def to_function(self) -> str:
        ordered = sorted(self.parameters, key=lambda parameter: not parameter.required)
        signature = ", ".join(
            f"{p.name}: {p.python_type}" if p.required else f"{p.name}: {p.python_type} = {p.python_default}"
            for p in ordered
        )
        body = textwrap.indent(textwrap.dedent(self.run).strip() or "pass", " " * 4)
        return f"def {self.function_name}({signature}):\n{body}\n"

    def to_definition(self) -> str:
        """Python source of this tool's entry in the generated TOOLS registry."""
        input_schema = {
            "type": "object",
            "properties": {parameter.name: parameter.to_json_schema() for parameter in self.parameters},
            "required": [parameter.name for parameter in self.parameters if parameter.required],
        }
        return (
            f"    {self.name!r}: {{\n"
            f"        'function': {self.function_name},\n"
            f"        'description': {self.description!r},\n"
            f"        'inputSchema': {input_schema!r},\n"
            f"    }},\n"
        )

    def to_command(self) -> Command:
        arguments = ", ".join(f"{parameter.name}={parameter.name}" for parameter in self.parameters)
        return Command(
            help=re.sub(r"\s+", " ", self.description).replace('"', "'"),
            params=[parameter.to_param() for parameter in self.parameters],
            run=RunBlock(f"print(_render_result({self.function_name}({arguments})))"),
        )


class MCPTools(Blueprint):
    """MCP tool server: every tool becomes a command, `serve` speaks MCP over stdio"""

    name: str = Field(description="Name of the CLI and of the MCP server.")
    version: str = Field(default="0.1.0", description="Version of the CLI and of the MCP server.")
    description: str = Field(default="", description="What the server offers.")
    protocol_version: str = Field(default="2025-06-18", description="MCP protocol revision the server reports.")
    imports: list[str] = Field(default=[], description="Import lines the tool bodies need, i.e. `import re`.")
    requires: list[str] = Field(default=[], description="Packages the tool bodies need. Bundled by `cli build`.")
    tools: list[Tool] = Field(min_length=1, description="The tools, as a list or as a mapping keyed by tool name.")

    @classmethod
    def pre_validate(cls, raw: dict[str, Any]) -> dict[str, Any]:
        # `tools` may be written as a mapping of name -> tool, which reads better for a handful of tools
        tools = raw.get("tools")
        if isinstance(tools, dict):
            raw = {**raw, "tools": [{"name": name, **(tool or {})} for name, tool in tools.items()]}
        return raw

    @field_validator("tools")
    @classmethod
    def unique_tools(cls, tools: list[Tool]) -> list[Tool]:
        names = [tool.name for tool in tools]
        if duplicates := sorted({name for name in names if names.count(name) > 1}):
            raise ValueError(f"duplicate tool names: {', '.join(duplicates)}")
        return tools

    def to_manifest(self) -> CLIManifest:
        functions = "\n\n".join(tool.to_function() for tool in self.tools)
        functions += "\n\nTOOLS = {\n" + "".join(tool.to_definition() for tool in self.tools) + "}\n"
        functions += f"SERVER_INFO = {{'name': {self.name!r}, 'version': {self.version!r}}}\n"
        functions += f"PROTOCOL_VERSION = {self.protocol_version!r}\n"
        functions += RUNTIME

        commands = {tool.name.replace("_", "-"): tool.to_command() for tool in self.tools}
        commands["tools"] = Command(
            help="Print the tool definitions as MCP tools/list JSON",
            run=RunBlock("print(json.dumps(_describe_tools(), indent=2))"),
        )
        commands["serve"] = Command(help="Serve the tools over MCP on stdio", run=RunBlock("_serve()"))

        return CLIManifest(
            name=self.name,
            version=self.version,
            help=self.description,
            requires=self.requires,
            imports=["import json", "import sys", *self.imports],
            functions=functions,
            commands=commands,
            tests=[{"tools": f"assert {self.tools[0].name!r} in result.output"}],
        )
