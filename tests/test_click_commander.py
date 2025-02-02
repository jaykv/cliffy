import pytest
from cliffy.commanders.click import ClickCommander, ClickParser
from cliffy.manifest import RunBlock, CLIManifest, Command, CommandParam, SimpleCommandParam


@pytest.fixture
def basic_manifest():
    return CLIManifest(
        name="test-cli",
        version="1.0.0",
        commands={"hello": Command(name="hello", run=RunBlock("print('Hello World')"))},
    )


@pytest.fixture
def click_commander(basic_manifest):
    return ClickCommander(basic_manifest)


@pytest.fixture
def click_parser(basic_manifest):
    return ClickParser(basic_manifest)


def test_click_commander_initialization(click_commander):
    assert click_commander.manifest.name == "test-cli"
    assert click_commander.manifest.version == "1.0.0"
    assert "import rich_click as click" in click_commander.base_imports


def test_parse_simple_param():
    parser = ClickParser(CLIManifest(name="test", version="1.0.0", commands={}))
    param = SimpleCommandParam({"name": "str!"})
    result = parser._parse_simple_param(param)
    assert "@click.argument('name', type=str)" in result


def test_parse_command_with_params():
    manifest = CLIManifest(
        name="test-cli",
        version="1.0.0",
        commands={
            "greet": Command(
                name="greet",
                params=[
                    CommandParam(name="name", type="str", required=True, help="Name to greet"),
                    SimpleCommandParam({"--count": "int=1"}),
                ],
                run=RunBlock("print(f'Hello {name} ' * count)"),
            )
        },
    )
    ClickCommander(manifest)
    parser = ClickParser(manifest)
    assert isinstance(manifest.commands, dict) and isinstance(manifest.commands["greet"], Command)
    command = manifest.commands["greet"]
    parsed_params = parser.parse_params(command)

    assert "--name" in parsed_params
    assert "type=str" in parsed_params
    assert "--count" in parsed_params
    assert "type=int" in parsed_params


def test_get_command_func_name(click_parser):
    command = Command(name="hello-world", run=RunBlock("print('test')"))
    assert click_parser.get_command_func_name(command) == "hello_world"


def test_get_parsed_command_name(click_parser):
    command = Command(name="group.subcommand", run=RunBlock("print('test')"))
    assert click_parser.get_parsed_command_name(command) == "subcommand"


def test_parse_run_block(click_parser):
    command = Command(name="test", run=RunBlock("$ echo 'hello'"))
    parsed_run = click_parser.parse_run_block(command.run)
    assert "subprocess.run" in parsed_run


def test_invalid_command_name():
    with pytest.raises(ValueError):
        parser = ClickParser(CLIManifest(name="test", version="1.0.0", commands={}))
        command = Command(name="invalid@name", run=RunBlock("print('test')"))
        parser.get_command_func_name(command)


def test_command_with_aliases():
    manifest = CLIManifest(
        name="test-cli",
        version="1.0.0",
        commands={"greet": Command(name="greet", aliases=["hi", "hello"], run=RunBlock("print('Hello!')"))},
    )
    commander = ClickCommander(manifest)
    commander.add_base_imports()
    commander.add_base_cli()
    assert isinstance(manifest.commands, dict) and isinstance(manifest.commands["greet"], Command)
    commander.add_root_command(manifest.commands["greet"])

    assert 'name="greet"' in commander.cli
    assert 'name="hi"' in commander.cli
    assert 'name="hello"' in commander.cli
