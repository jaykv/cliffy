from cliffy.commanders.typer import TyperCommander
from cliffy.manifest import CLIManifest, Command, CommandArg, CommandConfig


def test_greedy_command_expand():
    manifest = CLIManifest(
        name="test",
        help="",
        version="",
        commands={
            "homes.buy": Command(help="buy home", run="print('buying home')"),
            "shops.buy": Command(help="buy shop", run="print('buying shop')"),
            "(*).list": Command(args=[{"--limit|-l": "int"}], run='"""Get a list of {(*)}"""\nprint(f"listing {(*)}")'),
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
#         "(*).list": Command(args=[{"--limit|-l": "int"}],
#           run="\"\"\"Get a list of {(*)}\"\"\"\nprint(f\"listing {(*)}\")")
#     }
#     )
#     cmdr = TyperCommander(manifest=manifest)
#     cmdr.generate_cli()

#     assert "Get a list of homes" in cmdr.cli
#     assert "Get a list of shops" in cmdr.cli
#     assert "(*)" not in cmdr.cli
#     assert "limit" in cmdr.cli


def test_command_arg_parsing():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "greet": Command(
                name="greet",
                help="Greet someone",
                args=[
                    # Test Argument kind
                    CommandArg(
                        name="name", kind="Argument", type="str", required=True, help="Name to greet", short="n"
                    ),
                    # Test Option kind
                    CommandArg(
                        name="greeting", kind="Option", type="str", default='"Hello"', help="Custom greeting", short="g"
                    ),
                ],
                run='print(f"{greeting} {name}!")',
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Verify Argument kind parsing
    assert 'name: str = typer.Argument(..., help="Name to greet")' in cmdr.cli
    # Verify Option kind parsing
    assert 'greeting: str = typer.Option("Hello", "--greeting", "-g", help="Custom greeting")' in cmdr.cli


def test_command_arg_with_global_args():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        global_args=[
            CommandArg(
                name="verbose", kind="Option", type="bool", default=False, help="Enable verbose output", short="v"
            )
        ],
        commands={
            "test": Command(
                name="test",
                help="Test command",
                args=[CommandArg(name="input", kind="Argument", type="str", required=True, help="Input to process")],
                run="print(input)",
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Verify global Option arg
    assert 'verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")' in cmdr.cli
    # Verify command Argument
    assert 'input: str = typer.Argument(..., help="Input to process")' in cmdr.cli


def test_command_arg_mixed_with_dict():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "list": Command(
                name="list",
                help="List items",
                args=[
                    CommandArg(name="--page", kind="Option", type="int", default=1, help="Page number"),
                    {"--limit|-l": "int = 10"},  # Dict-style arg
                ],
                run="print(f'Page {page}, Limit {limit}')",
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()

    # Verify CommandArg Option
    assert 'page: int = typer.Option(1, help="Page number")' in cmdr.cli
    # Verify dict-style arg
    assert 'limit: int = typer.Option(10, "--limit", "-l")' in cmdr.cli


def test_command_arg_required_option():
    manifest = CLIManifest(
        name="test",
        version="0.1.0",
        help="Test CLI",
        commands={
            "config": Command(
                name="config",
                help="Configure settings",
                args=[CommandArg(name="--token", kind="Option", type="str", required=True, help="API token")],
                run="print(f'Token: {token}')",
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
                run="print('test')",
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
                run="print('test')",
            ),
            "test2": Command(
                name="test2",
                help="Test command",
                config=CommandConfig(),
                run="print('test')",
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
                run="print('test')",
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
                run="print('test')",
            )
        },
    )

    cmdr = TyperCommander(manifest=manifest)
    cmdr.generate_cli()
    assert 'help="Test commandwith newline",' in cmdr.cli
