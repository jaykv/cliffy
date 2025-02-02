import pytest
from cliffy.doc import DocGenerator
from cliffy.manifest import CLIManifest, Command, Example, RunBlock, SimpleCommandParam, CommandParam


@pytest.fixture
def sample_manifest():
    return CLIManifest(
        name="sample-cli",
        version="1.0.0",
        help="Sample CLI for testing",
        commands={
            "sample_command": Command(
                help="Sample command help",
                params=[
                    SimpleCommandParam(root={"param1": "str"}),
                    CommandParam(name="param2", type="int", help="Parameter 2", default=42),
                ],
                aliases=["sc"],
                run=RunBlock("test"),
            )
        },
        examples=[Example(command="sample_command --param1 value", description="Sample example")],
    )


def test_build_docs(sample_manifest):
    doc_gen = DocGenerator(sample_manifest)
    docs = doc_gen._build_docs()
    assert docs.name == "sample-cli"
    assert docs.version == "1.0.0"
    assert docs.help == "Sample CLI for testing"
    assert "sample_command" in docs.commands
    assert docs.commands["sample_command"].help == "Sample command help"
    assert len(docs.commands["sample_command"].params) == 2
    assert docs.examples[0].command == "sample_command --param1 value"


def test_document_commands(sample_manifest):
    doc_gen = DocGenerator(sample_manifest)
    commands = doc_gen._document_commands()
    assert "sample_command" in commands
    assert commands["sample_command"].help == "Sample command help"
    assert len(commands["sample_command"].params) == 2
    assert commands["sample_command"].params[0] == "param1: str"
    assert commands["sample_command"].params[1] == "param2: int (default: 42) - Parameter 2"
    assert commands["sample_command"].aliases == ["sc"]


def test_generate_markdown(sample_manifest, tmp_path):
    doc_gen = DocGenerator(sample_manifest)
    output_dir = tmp_path / "docs"
    output_dir.mkdir()
    doc_gen.generate("md", str(output_dir))
    output_file = output_dir / "sample-cli.md"
    assert output_file.exists()
    content = output_file.read_text()
    assert "# sample-cli v1.0.0" in content
    assert "Sample CLI for testing" in content
    assert "### sample_command" in content
    assert "Sample command help" in content
    assert "param1: str" in content
    assert "param2: int (default: 42) - Parameter 2" in content
    assert "Aliases: sc" in content
    assert "```bash\nsample_command --param1 value\n```" in content


def test_generate_rst(sample_manifest, tmp_path):
    doc_gen = DocGenerator(sample_manifest)
    output_dir = tmp_path / "docs"
    output_dir.mkdir()
    doc_gen.generate("rst", str(output_dir))
    output_file = output_dir / "sample-cli.rst"
    assert output_file.exists()
    content = output_file.read_text()
    assert "sample-cli v1.0.0" in content
    assert "Sample CLI for testing" in content
    assert "sample_command" in content
    assert "Sample command help" in content
    assert "* param1: str" in content
    assert "* param2: int (default: 42) - Parameter 2" in content
    assert "Aliases: sc" in content
    assert ".. code-block:: bash\n\n    sample_command --param1 value" in content


def test_generate_html(sample_manifest, tmp_path):
    doc_gen = DocGenerator(sample_manifest)
    output_dir = tmp_path / "docs"
    output_dir.mkdir()
    doc_gen.generate("html", str(output_dir))
    output_file = output_dir / "sample-cli.html"
    assert output_file.exists()
    content = output_file.read_text()
    assert "<title>sample-cli v1.0.0</title>" in content
    assert "<h1>sample-cli v1.0.0</h1>" in content
    assert "<p>Sample CLI for testing</p>" in content
    assert "<h3>sample_command</h3>" in content
    assert "<p>Sample command help</p>" in content
    assert "<p>param1: str</p>" in content
    assert "<p>param2: int (default: 42) - Parameter 2</p>" in content
    assert "<em>Aliases: sc</em>" in content
    assert "<pre><code>sample_command --param1 value</code></pre>" in content
    assert "<p>Sample example</p>" in content
