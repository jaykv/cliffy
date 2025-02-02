from cliffy.manifest import CLIManifest, Example, RunBlock, RunBlockList, SimpleCommandParam, CommandParam
from cliffy.helper import write_to_file
from pydantic import BaseModel


class CommandDoc(BaseModel):
    help: str
    params: list[str]
    aliases: list[str] = []


class CLIDoc(BaseModel):
    name: str
    version: str
    help: str
    commands: dict[str, CommandDoc]
    examples: list[Example]


class DocGenerator:
    def __init__(self, manifest: CLIManifest):
        self.manifest = manifest

    def generate(self, format: str, output_dir: str) -> None:
        docs = self._build_docs()
        if format == "md":
            self._write_markdown(docs, output_dir)
        elif format == "rst":
            self._write_rst(docs, output_dir)
        elif format == "html":
            self._write_html(docs, output_dir)

    def _build_docs(self) -> CLIDoc:
        manifest_examples: list[Example] = []
        for ex in self.manifest.examples:
            if isinstance(ex, str):
                manifest_examples.append(Example(command=ex))
            else:
                manifest_examples.append(ex)

        return CLIDoc(
            name=self.manifest.name,
            version=self.manifest.version,
            help=self.manifest.help,
            commands=self._document_commands(),
            examples=manifest_examples,
        )

    def _document_commands(self) -> dict[str, CommandDoc]:
        documented_commands = {}
        if isinstance(self.manifest.commands, list):
            self.manifest.commands = {command.name: command for command in self.manifest.commands}
        for cmd_name, cmd in self.manifest.commands.items():
            cmd_name = cmd_name.replace(".", " ")
            if isinstance(cmd, (RunBlock, RunBlockList)):
                documented_commands[cmd_name] = CommandDoc(help="", params=[])
                continue

            params_doc = []
            for param in cmd.params:
                if isinstance(param, SimpleCommandParam):
                    params_doc.append(
                        f"{param.name}: {param.type}"
                        + (f" (default: {param.default})" if param.default else "")
                        + (f" - {param.help}" if param.help else "")
                    )
                elif isinstance(param, CommandParam):
                    params_doc.append(
                        f"{param.name}: {param.type}"
                        + (f" (default: {param.default})" if param.default else "")
                        + (f" - {param.help}" if param.help else "")
                    )

            documented_commands[cmd_name] = CommandDoc(
                help=cmd.help, params=params_doc, aliases=cmd.aliases if hasattr(cmd, "aliases") else []
            )
        return documented_commands

    def _write_markdown(self, docs: CLIDoc, output_dir: str) -> None:
        md = f"# {docs.name} v{docs.version}\n\n"
        md += f"{docs.help}\n\n"
        md += "## Commands\n\n"
        for cmd_name, cmd in docs.commands.items():
            md += f"### {cmd_name}\n{cmd.help}\n\n"
            if cmd.params:
                md += "Parameters:\n"
                for param in cmd.params:
                    md += f"- {param}\n"
            if cmd.aliases:
                md += f"\nAliases: {', '.join(cmd.aliases)}\n"
            md += "\n"

        md += "## Examples\n\n"
        for example in docs.examples:
            md += f"```bash\n{example.command}\n```\n"
            md += f"{example.description}\n\n"

        path = f"{output_dir}/{docs.name}.md" if output_dir else f"{docs.name}.md"
        write_to_file(path, md)

    def _write_rst(self, docs: CLIDoc, output_dir: str) -> None:
        rst = f"{docs.name} v{docs.version}\n"
        rst += "=" * len(f"{docs.name} v{docs.version}") + "\n\n"
        rst += f"{docs.help}\n\n"

        rst += "Commands\n"
        rst += "--------\n\n"
        for cmd_name, cmd in docs.commands.items():
            rst += f"{cmd_name}\n"
            rst += "~" * len(cmd_name) + "\n\n"
            rst += f"{cmd.help}\n\n"

            if cmd.params:
                rst += "Parameters:\n\n"
                for param in cmd.params:
                    rst += f"* {param}\n"
                rst += "\n"

            if cmd.aliases:
                rst += "Aliases: " + ", ".join(cmd.aliases) + "\n\n"

        rst += "Examples\n"
        rst += "--------\n\n"
        for example in docs.examples:
            rst += f".. code-block:: bash\n\n    {example.command}\n\n"
            rst += f"{example.description}\n\n"

        path = f"{output_dir}/{docs.name}.rst" if output_dir else f"{docs.name}.rst"
        write_to_file(path, rst)

    def _write_html(self, docs: CLIDoc, output_dir: str) -> None:
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{docs.name} v{docs.version}</title>
    <style>
        body {{ font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 20px; }}
        pre {{ background: #f6f8fa; padding: 16px; border-radius: 6px; }}
        .command {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        .params {{ margin-left: 20px; }}
    </style>
</head>
<body>
    <h1>{docs.name} v{docs.version}</h1>
    <p>{docs.help}</p>
    
    <h2>Commands</h2>
"""
        for cmd_name, cmd in docs.commands.items():
            html += f"""
    <div class="command">
        <h3>{cmd_name}</h3>
        <p>{cmd.help}</p>
"""
            if cmd.params:
                html += "        <h4>Parameters:</h4>\n        <div class='params'>\n"
                for param in cmd.params:
                    html += f"            <p>{param}</p>\n"
                html += "        </div>\n"

            if cmd.aliases:
                html += f"        <p><em>Aliases: {', '.join(cmd.aliases)}</em></p>\n"
            html += "    </div>\n"

        html += """
    <h2>Examples</h2>
"""
        for example in docs.examples:
            html += f"""
    <pre><code>{example.command}</code></pre>
    <p>{example.description}</p>
"""
        html += """
</body>
</html>"""

        path = f"{output_dir}/{docs.name}.html" if output_dir else f"{docs.name}.html"
        write_to_file(path, html)
