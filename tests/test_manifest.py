from pydantic import ValidationError
from cliffy.commanders.typer import TyperCommander
from cliffy.manifest import (
    CLIManifest,
    Command,
    CommandParam,
    CommandConfig,
    CommandTemplate,
    PostRunBlock,
    PreRunBlock,
    RunBlock,
    SimpleCommandParam,
)
import pytest


def test_greedy_command_expand():
    manifest = CLIManifest(
        name="test",
        help="",
        version="",
        commands={
            "homes.buy": Command(help="buy home", run=RunBlock("print('buying home')")),
            "shops.buy": Command(help="buy shop", run=RunBlock("print('buying shop')")),
            "(*).list": Command(
                params=[SimpleCommandParam({"--limit|-l": "int"})],
                run=RunBlock('"""Get a list of {(*)}"""\nprint(f"listing {(*)}")'),
            ),
        },
    )
    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    assert "Get a list of homes" in cmdr.cli
    assert "Get a list of shops" in cmdr.cli
    assert "limit" in cmdr.cli
    assert "(*)" not in cmdr.cli


# def test_greedy_command_expand_empty_root():
#     manifest = CLIManifest(
#     name="test",
#     help="",
#     version="",
#     commands={
#         "homes": Command(help="manage homes"),
#         "shops": Command(help="manage shops"),
#         "(*).list": Command(params=[{"--limit|-l": "int"}],
#           run="\"\"\"Get a list of {(*)}\"\"\"\nprint(f\"listing {(*)}\")")
#     }
#     )
#     cmdr = TyperCommander(manifest=manifest)
#     cmdr.generate_cli()

#     assert "Get a list of homes" in cmdr.cli
#     assert "Get a list of shops" in cmdr.cli
#     assert "(*)" not in cmdr.cli
#     assert "limit" in cmdr.cli


def test_command_param_parsing():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "greet": Command(
                name="greet",
                help="Greet someone",
                params=[
                    # Test Argument kind
                    CommandParam(name="name", type="str", required=True, help="Name to greet"),
                    # Test Option kind
                    CommandParam(
                        name="--greeting",
                        type="str",
                        default='"Hello"',
                        help="Custom greeting",
                        short="-g",
                    ),
                ],
                run=RunBlock('print(f"{greeting} {name}!")'),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Verify Argument kind parsing
    assert 'name: str = typer.Argument(..., help="Name to greet")' in cmdr.cli
    # Verify Option kind parsing
    assert 'greeting: str = typer.Option("Hello", "--greeting", "-g", help="Custom greeting")' in cmdr.cli


def test_command_param_with_global_params():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        global_params=[
            CommandParam(name="--verbose", type="bool", default=False, help="Enable verbose output", short="-v")
        ],
        commands={
            "test": Command(
                name="test",
                help="Test command",
                params=[CommandParam(name="input", type="str", required=True, help="Input to process")],
                run=RunBlock("print(input)"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Verify global Option param
    assert 'verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")' in cmdr.cli
    # Verify command Argument
    assert 'input: str = typer.Argument(..., help="Input to process")' in cmdr.cli


def test_command_param_mixed_with_dict():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "list": Command(
                name="list",
                help="List items",
                params=[
                    CommandParam(name="--page", type="int", default=1, help="Page number"),
                    SimpleCommandParam({"--limit|-l": "int = 10"}),  # Dict-style param
                ],
                run=RunBlock("print(f'Page {page}, Limit {limit}')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Verify CommandParam Option
    assert 'page: int = typer.Option(1, help="Page number")' in cmdr.cli
    # Verify dict-style param
    assert 'limit: int = typer.Option(10, "--limit", "-l")' in cmdr.cli


def test_command_param_required_option():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "config": Command(
                name="config",
                help="Configure settings",
                params=[CommandParam(name="--token", type="str", required=True, help="API token")],
                run=RunBlock("print(f'Token: {token}')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Verify required Option
    assert 'token: str = typer.Option(..., help="API token")' in cmdr.cli


def test_command_config_options():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "test": Command(
                name="test",
                help="Test command",
                config=CommandConfig(
                    context_settings={"help_option_names": ["-h", "--helpme"]},
                    epilog="Epilog text",
                    short_help="Short help text",
                    options_metavar="[TEST OPTIONS]",
                    add_help_option=False,
                    no_args_is_help=True,
                    hidden=True,
                    deprecated=True,
                    rich_help_panel="Custom Panel",
                ),
                run=RunBlock("print('test')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    assert "context_settings={'help_option_names': ['-h', '--helpme']}," in cmdr.cli
    assert 'epilog="Epilog text",' in cmdr.cli
    assert 'short_help="Short help text",' in cmdr.cli
    assert 'options_metavar="[TEST OPTIONS]",' in cmdr.cli
    assert "add_help_option=False," in cmdr.cli
    assert "no_args_is_help=True," in cmdr.cli
    assert "hidden=True," in cmdr.cli
    assert "deprecated=True," in cmdr.cli
    assert 'rich_help_panel="Custom Panel"' in cmdr.cli


def test_command_config_empty():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "test": Command(
                name="test",
                help="Test command",
                run=RunBlock("print('test')"),
            ),
            "test2": Command(
                name="test2",
                help="Test command",
                config=CommandConfig(),
                run=RunBlock("print('test')"),
            ),
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    assert "epilog=" not in cmdr.cli
    assert "short_help=" not in cmdr.cli
    assert "options_metavar=" not in cmdr.cli
    assert "add_help_option=" not in cmdr.cli
    assert "no_args_is_help=" not in cmdr.cli
    assert "hidden=" not in cmdr.cli
    assert "deprecated=" not in cmdr.cli
    assert "rich_help_panel=" not in cmdr.cli


def test_command_config_partial():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "test": Command(
                name="test",
                help="Test command",
                config=CommandConfig(hidden=True),  # Partial config
                run=RunBlock("print('test')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    assert "hidden=True" in cmdr.cli
    assert "rich_help_panel=" not in cmdr.cli  # Other options should not be present


def test_command_config_help_newline_removed():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "test": Command(
                name="test",
                help="Test command\nwith newline",
                config=CommandConfig(),
                run=RunBlock("print('test')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()
    assert 'help="Test commandwith newline",' in cmdr.cli


def test_command_pre_run_post_run():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "test": Command(
                name="test",
                help="Test command",
                pre_run=PreRunBlock("print('pre-run')"),
                run=RunBlock("print('run')"),
                post_run=PostRunBlock("print('post-run')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    assert "print('pre-run')" in cmdr.cli
    assert "print('run')" in cmdr.cli
    assert "print('post-run')" in cmdr.cli
    assert cmdr.cli.index("print('pre-run')") < cmdr.cli.index("print('run')")
    assert cmdr.cli.index("print('run')") < cmdr.cli.index("print('post-run')")


def test_command_template_pre_run_post_run():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        command_templates={
            "common": CommandTemplate(
                pre_run=PreRunBlock("print('template pre-run')"),
                post_run=PostRunBlock("print('template post-run')"),
            )
        },
        commands={
            "test": Command(
                name="test",
                help="Test command",
                template="common",
                run=RunBlock("print('run')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    assert "print('template pre-run')" in cmdr.cli
    assert "print('run')" in cmdr.cli
    assert "print('template post-run')" in cmdr.cli


def test_command_and_template_pre_run_post_run():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        command_templates={
            "common": CommandTemplate(
                pre_run=PreRunBlock("print('template pre-run')"),
                post_run=PostRunBlock("print('template post-run')"),
            )
        },
        commands={
            "test": Command(
                name="test",
                help="Test command",
                template="common",
                pre_run=PreRunBlock("print('command pre-run')"),
                run=RunBlock("print('run')"),
                post_run=PostRunBlock("print('command post-run')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()
    # pre_run from template should come before command pre_run
    assert "print('template pre-run')" in cmdr.cli
    assert "print('command pre-run')" in cmdr.cli
    assert "print('run')" in cmdr.cli
    assert cmdr.cli.index("print('template pre-run')") < cmdr.cli.index("print('command pre-run')")
    # post_run from template should come after command post_run
    assert "print('command post-run')" in cmdr.cli
    assert "print('template post-run')" in cmdr.cli
    assert cmdr.cli.index("print('template post-run')") > cmdr.cli.index("print('command post-run')")


def test_command_template_config_merge():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        command_templates={
            "common": CommandTemplate(
                config=CommandConfig(
                    context_settings={"help_option_names": ["-h", "--helpme"]},
                    epilog="Template Epilog",  # Will be overridden
                )
            ),
        },
        commands={
            "test": Command(
                name="test",
                help="Test command",
                template="common",
                config=CommandConfig(
                    epilog="Command Epilog",
                    short_help="Command Short Help",
                ),
                run=RunBlock("print('test')"),
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Assert that values from command.config override template.config
    assert "context_settings={'help_option_names': ['-h', '--helpme']}," in cmdr.cli
    assert 'epilog="Command Epilog",' in cmdr.cli  # Overridden by command config
    assert 'short_help="Command Short Help"' in cmdr.cli

    # Assert that unset values are not included
    assert 'options_metavar="[OPTIONS]",' not in cmdr.cli
    assert "add_help_option=True," not in cmdr.cli


def test_command_template_config_merge_empty_command_config():
    """
    Test merging when the command config is empty or nonexistent - should use
    the CommandConfig from the template.
    """
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        command_templates={
            "common": CommandTemplate(
                config=CommandConfig(
                    context_settings={"help_option_names": ["-h", "--helpme"]},
                    epilog="Template Epilog",
                ),
            )
        },
        commands={
            "test": Command(
                name="test",
                help="Test command",
                template="common",
                # command.config is implicitly an empty CommandConfig in this case
                run=RunBlock("print('test')"),
            ),
            "test2": Command(
                name="test2",
                help="Test command 2",
                template="common",
                config=None,  # Explicitly set config as None - should be equivalent to an empty config
                run=RunBlock("print('test2')"),
            ),
        },
    )
    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()
    generated_cli = cmdr.cli
    # Assertions for both commands using the same template config
    assert "context_settings={'help_option_names': ['-h', '--helpme']}" in generated_cli
    assert 'epilog="Template Epilog"' in generated_cli


def test_command_param_short_without_option():
    """Test that short flag can only be used with -- prefixed name"""
    with pytest.raises(ValidationError) as exc_info:
        CommandParam(
            name="name",
            type="str",
            short="-n",  # Invalid: short flag without --name
            required=True,
            help="Name to greet",
        )
    assert "short can only be used when" in str(exc_info.value)


def test_invalid_template_reference():
    """Test that referencing non-existent template raises error"""
    with pytest.raises(ValueError) as exc_info:
        manifest = CLIManifest(
            name="test",
            version="0.1.0",
            help="Test CLI",
            commands={
                "greet": Command(
                    help="Greet command",
                    template="non_existent",  # Invalid template reference
                    run=RunBlock("print('hello')"),
                )
            },
        )
        cmdr = TyperCommander(manifest=manifest)
        cmdr.generate_cli()

    assert "Template non_existent undefined in command_templates" in str(exc_info.value)


def test_invalid_command_param_type():
    """Test that invalid argument type raises error"""
    with pytest.raises(ValidationError) as exc_info:
        CLIManifest(
            name="test",
            version="0.1.0",
            help="Test CLI",
            commands={
                "greet": Command(
                    help="Greet command",
                    params=[
                        CommandParam(
                            name="count",
                            type=0.1,  # Invalid type # type: ignore
                            required=True,
                        )
                    ],
                    run=RunBlock("print('hello')"),
                )
            },
        )
    assert "type" in str(exc_info.value)


def test_invalid_simple_command_param():
    """Test that invalid SimpleCommandParam structure raises error"""
    with pytest.raises(ValidationError) as exc_info:
        CLIManifest(
            name="test",
            version="0.1.0",
            help="Test CLI",
            commands={
                "list": Command(
                    help="List items",
                    params=[SimpleCommandParam({"invalid format"})],  # Invalid format # type: ignore
                    run=RunBlock("print('listing')"),
                )
            },
        )
    assert "validation error" in str(exc_info.value).lower()
