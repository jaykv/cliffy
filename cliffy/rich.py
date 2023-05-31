## Mimic rich API methods for rich-less support
from typing import Any

import click


class Console:
    def __init__(self) -> None:
        pass

    def print(self, text: Any, **kwargs) -> None:
        if isinstance(text, Table):
            click.echo(text)
        else:
            print(text)


class Table:

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
