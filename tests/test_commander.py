import pytest
from cliffy.commanders.typer import TyperCommander
from cliffy.manifest import CLIManifest, Command, CommandTemplate, SimpleCommandParam, RunBlock


@pytest.mark.parametrize(
    "id, command_name, expected_result",
    [
        ("greedy_command", "(*)", True),
        ("non_greedy_command", "group.command", False),
        ("greedy_group_command", "group.(*)", True),
    ],
)
def test_is_greedy(id, command_name, expected_result):
    commander = TyperCommander(CLIManifest(name="mycli", help="", version="0.1.0", commands={}))
    result = commander.is_greedy(command_name)
    assert result == expected_result


@pytest.mark.parametrize(
    "id, command_name, group, expected_lazy_command_name",
    [
        ("simple_greedy_command", "(*)", "mygroup", "mygroup"),
        ("complex_greedy_command", "group.(*).command", "mygroup", "group.mygroup.command"),
    ],
)
def test_from_greedy_make_lazy_command(id, command_name, group, expected_lazy_command_name):
    greedy_command = Command(name=command_name, run=RunBlock("echo hello"))
    commander = TyperCommander(CLIManifest(name="mycli", help="", version="0.1.0", commands={}))

    lazy_command = commander.from_greedy_make_lazy_command(greedy_command, group)
    assert lazy_command.name == expected_lazy_command_name


def test_setup_command_aliases():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={"command1 | alias1 | alias2": RunBlock("echo hello")},
    )
    commander = TyperCommander(manifest)
    assert commander.commands[0].name == "command1"
    assert commander.commands[0].aliases == ["alias1", "alias2"]
    assert commander.aliases_by_commands["command1"] == ["alias1", "alias2"]


def test_build_groups():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={
            "group1.command1": RunBlock("echo hello"),
            "group1.command2": RunBlock("echo world"),
            "group2.command3": RunBlock("echo foo"),
        },
    )
    commander = TyperCommander(manifest)
    assert len(commander.groups) == 2
    assert "group1" in commander.groups
    assert "group2" in commander.groups
    assert len(commander.groups["group1"].commands) == 2
    assert len(commander.groups["group2"].commands) == 1


def test_build_groups_with_template():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={
            "group1.command1": Command(run=RunBlock("echo hello"), template="my_template"),
        },
        command_templates={"my_template": CommandTemplate(params=[SimpleCommandParam(root={"name": "name"})])},
    )
    commander = TyperCommander(manifest)
    assert commander.groups["group1"].commands[0].params == [SimpleCommandParam(root={"name": "name"})]


def test_build_groups_with_missing_template():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={
            "group1.command1": Command(run=RunBlock("echo hello"), template="missing_template"),
        },
        command_templates={},
    )

    with pytest.raises(ValueError):
        TyperCommander(manifest)
