"""Click, Console and Table: from rich-click and rich when the `rich` extra is installed, plain otherwise.

For the type checker `click` is always Click itself. rich-click has the same API, and whether it is
installed must not change what type-checks.
"""

from typing import TYPE_CHECKING, Any

__all__ = ["ClickGroup", "Console", "Table", "click", "print_rich_table"]


class PlainConsole:
    """Stand-in for `rich.console.Console`"""

    def __init__(self) -> None:
        pass

    def print(self, text: Any, **kwargs: Any) -> None:
        if isinstance(text, PlainTable):
            click.echo(text)
        else:
            print(text, end=kwargs.get("end", "\n"))


class PlainTable:
    """Stand-in for `rich.table.Table`"""

    __slots__ = ("columns", "rows", "styles")

    def __init__(self) -> None:
        self.columns: list[str] = []
        self.rows: list[list[str]] = []
        self.styles: list[str] = []

    def add_column(self, col: str, style: str = "") -> None:
        self.columns.append(col)
        self.styles.append(style)

    def add_row(self, *row: Any) -> None:
        self.rows.append([*row])

    def __str__(self) -> str:
        text = (
            "".join(
                [
                    click.style(f"{col:10}", fg=style or None)
                    for col, style in zip(self.columns, self.styles, strict=True)
                ]
            )
            + "\n"
        )
        for row in self.rows:
            for col in row:
                text += f"{col:10}"
            text += "\n"
        return text


if TYPE_CHECKING:
    import click
    from click import Group

    ClickGroup = Group
    Console = PlainConsole
    Table = PlainTable
else:
    try:
        import rich_click as click
        from rich.console import Console
        from rich.table import Table
        from rich_click import RichGroup

        ClickGroup = RichGroup
    except ImportError:
        import click
        from click import Group

        ClickGroup = Group
        Console = PlainConsole
        Table = PlainTable


def print_rich_table(cols: list[str], rows: list[list[str]], styles: list[str]) -> None:
    table = Table()
    for style, col in zip(styles, cols, strict=False):
        table.add_column(col, style=style)
    for row in rows:
        table.add_row(*row)

    Console().print(table)
