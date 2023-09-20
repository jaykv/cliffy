## rich-click compat for rich-less support
from typing import Any, Type

__all__ = ["click", "Console", "ClickGroup", "Table"]

try:
    import rich_click as click  # type: ignore
    from rich.console import Console  # type: ignore
    from rich.table import Table  # type: ignore

    from rich_click.rich_group import RichGroup  # type: ignore

    ClickGroup = RichGroup  # type: ignore[no-redef]
except ImportError:
    import click  # type: ignore[no-redef]
    from click import Group

    ClickGroup: Type[Group] = Group  # type: ignore[no-redef]

    class Console:  # type: ignore[no-redef]
        def __init__(self) -> None:
            pass

        def print(self, text: Any, **kwargs) -> None:
            if isinstance(text, Table):
                click.echo(text)
            else:
                print(text)

    class Table:  # type: ignore[no-redef]
        __slots__ = ("cols", "rows", "styles")

        def __init__(self) -> None:
            self.cols: list[str] = []
            self.rows: list[list[str]] = []
            self.styles: list[str] = []

        def add_column(self, col: str, style: str = "") -> None:
            self.cols.append(col)
            self.styles.append(style)

        def add_row(self, *row) -> None:
            self.rows.append([*row])

        def __str__(self) -> str:
            text = "".join([click.style(f"{col:10}", fg=self.styles.pop(0)) for col in self.cols]) + "\n"
            for row in self.rows:
                for col in row:
                    text += f"{col:10}"
                text += "\n"
            return text


def print_rich_table(cols: list[str], rows: list[list[str]], styles: list[str]) -> None:
    table = Table()
    for style, col in zip(styles, cols):
        table.add_column(col, style=style)
    for row in rows:
        table.add_row(*row)

    Console().print(table)
