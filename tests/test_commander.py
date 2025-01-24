import pytest
from cliffy.commanders.typer import TyperCommander
from cliffy.manifest import (
    CLIManifest,
    Command,
    CommandTemplate,
    SimpleCommandParam,
    RunBlock,
    PreRunBlock,
    PostRunBlock,
    RunBlockList,
    CommandParam,
    GenericCommandParam,
)


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


def test_build_groups_with_pre_run_template():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={
            "group1.command1": Command(run=RunBlock("echo hello"), template="my_template"),
        },
        command_templates={
            "my_template": CommandTemplate(pre_run=PreRunBlock("echo pre_run"), post_run=PostRunBlock("echo post_run"))
        },
    )
    commander = TyperCommander(manifest)
    assert commander.groups["group1"].commands[0].pre_run.root == "echo pre_run\n"
    assert commander.groups["group1"].commands[0].post_run.root == "\necho post_run"


def test_from_greedy_make_lazy_command_with_run_block_list():
    greedy_command = Command(
        name="(*).command", run=RunBlockList([RunBlock("echo {(*)}"), RunBlock("echo {(*)} again")])
    )
    commander = TyperCommander(CLIManifest(name="mycli", help="", version="0.1.0", commands={}))

    lazy_command = commander.from_greedy_make_lazy_command(greedy_command, "test")
    assert isinstance(lazy_command.run, RunBlockList)
    assert lazy_command.run[0].root == "echo test"
    assert lazy_command.run[1].root == "echo test again"


def test_from_greedy_make_lazy_command_with_params():
    greedy_command = Command(
        name="(*).command",
        run=RunBlock("echo hello"),
        params=[
            CommandParam(name="param1", type="str", help="Help for {(*)}"),
            SimpleCommandParam(root={"name": "{(*)}"}),
            GenericCommandParam(root="--{(*)}-flag"),
        ],
    )
    commander = TyperCommander(CLIManifest(name="mycli", help="", version="0.1.0", commands={}))

    lazy_command = commander.from_greedy_make_lazy_command(greedy_command, "test")
    assert lazy_command.params[0].help == "Help for test"
    assert lazy_command.params[1].root == {"name": "test"}
    assert lazy_command.params[2].root == "--test-flag"


def test_setup_command_aliases_with_group_commands():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={
            "group1.command1 | alias1 | alias2": RunBlock("echo hello"),
            "group2.command2 | alias3": RunBlock("echo world"),
        },
    )
    commander = TyperCommander(manifest)
    group1_command = next(cmd for cmd in commander.groups["group1"].commands)
    group2_command = next(cmd for cmd in commander.groups["group2"].commands)
    assert group1_command.aliases == ["alias1", "alias2"]
    assert group2_command.aliases == ["alias3"]


@pytest.mark.xfail
def test_build_groups_with_complex_hierarchy():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={
            "group1.subgroup.command1": RunBlock("echo hello"),
            "group1.subgroup.command2": RunBlock("echo world"),
            "group2.command3": RunBlock("echo foo"),
        },
    )
    commander = TyperCommander(manifest)
    assert len(commander.groups) == 3
    assert "group1" in commander.groups
    assert "group2" in commander.groups
    assert "subgroup" in commander.groups


def test_add_lazy_command_multiple_groups():
    manifest = CLIManifest(
        name="mycli",
        help="",
        version="0.1.0",
        commands={
            "group1.command1": RunBlock("echo hello"),
            "group2.command2": RunBlock("echo world"),
            "(*).lazy": RunBlock("echo {(*)}"),
        },
    )
    commander = TyperCommander(manifest)
    assert len(commander.greedy) == 1
    assert len([cmd for cmd in commander.commands if "lazy" in cmd.name]) == 1
    assert not any(cmd.name == "group1.lazy" for cmd in commander.commands)
    assert not any(cmd.name == "group2.lazy" for cmd in commander.commands)

    # only after generate_cli should greedy commands be turned into lazy
    commander.generate_cli()
    assert len(commander.greedy) == 1
    assert len([cmd for cmd in commander.commands if "lazy" in cmd.name]) == 3
    assert any(cmd.name == "group1.lazy" for cmd in commander.commands)
    assert any(cmd.name == "group2.lazy" for cmd in commander.commands)
