def run() -> None:
    from cliffy.cli import cli

    try:
        from cliffy.ai import ai

        cli.add_command(ai)
    except Exception as e:
        print(e)

    cli()  # type: ignore
