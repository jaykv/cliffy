## Mimic rich API methods for rich-less support
import click


class Console:
    def __init__(self) -> None:
        pass

    def print(self, text, **kwargs) -> None:
        if isinstance(text, Table):
            click.echo(text)
        else:
            print(text)


class Syntax:
    def __init__(self, text, *args, **kwargs) -> None:
        self.text = text

    def __str__(self) -> str:
        return self.text


class Table:
    def __init__(self) -> None:
        self.cols = []
        self.rows = []

    def add_column(self, col, style=None) -> None:
        self.cols.append(col)

    def add_row(self, *row) -> None:
        self.rows.append([*row])

    def __str__(self) -> str:
        text = "".join([click.style(f"{col:10}", fg="magenta") for col in self.cols]) + "\n"
        for row in self.rows:
            for col in row:
                text += f"{col:10}"
            text += "\n"
        return text
