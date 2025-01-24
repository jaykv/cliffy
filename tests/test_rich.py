from cliffy.rich import print_rich_table, Table, Console


def test_print_rich_table_basic(capsys):
    cols = ["Name", "Age", "City"]
    rows = [["John", "25", "NYC"], ["Alice", "30", "LA"]]
    styles = ["red", "blue", "green"]
    print_rich_table(cols, rows, styles)
    result_out = capsys.readouterr().out

    assert "Name" in result_out
    assert "Age" in result_out
    assert "City" in result_out
    assert "John" in result_out
    assert "25" in result_out
    assert "NYC" in result_out
    assert "Alice" in result_out
    assert "30" in result_out
    assert "LA" in result_out


def test_import_error(monkeypatch):
    import sys

    original_import = __import__

    # Simulate ImportError for rich_click and rich modules
    def mock_import(name, *args):
        if name in ("rich_click", "rich.console", "rich.table", "rich_click.rich_group"):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args)

    monkeypatch.setattr(sys, "modules", sys.modules.copy())
    monkeypatch.setattr("builtins.__import__", mock_import)

    # Re-import the module to trigger the ImportError handling
    import importlib
    import cliffy.rich

    importlib.reload(cliffy.rich)

    # Test the fallback behavior
    from cliffy.rich import Console, Table, ClickGroup

    console = Console()
    table = Table()
    table.add_column("Test", style="red")
    table.add_row("Data")
    console.print(table)
    assert isinstance(console, cliffy.rich.Console)
    assert isinstance(table, cliffy.rich.Table)
    assert isinstance(ClickGroup, type(cliffy.rich.Group))


def test_table_creation():
    table = Table()
    assert table.columns == []
    assert table.rows == []
    if hasattr(table, "styles"):
        assert getattr(table, "styles") == []


def test_table_add_column():
    table = Table()
    table.add_column("Name", style="red")
    assert table.columns
    if hasattr(table, "styles"):
        assert getattr(table, "styles") == ["red"]


def test_table_add_row():
    table = Table()
    table.add_row("John", "25", "NYC")
    assert table.rows


def test_console_print_table(capsys):
    console = Console()
    table = Table()
    table.add_column("Test", style="red")
    table.add_row("Data")
    console.print(table)
    result_out = capsys.readouterr().out

    assert "Data" in result_out
    assert "Test" in result_out


def test_console_print_text(capsys):
    console = Console()
    console.print("Simple text")
    assert "Simple text" in capsys.readouterr().out


def test_print_rich_table_empty(capsys):
    cols = []
    rows = []
    styles = []
    print_rich_table(cols, rows, styles)
    result_out = capsys.readouterr().out

    assert "\n" in result_out


def test_print_rich_table_single_column(capsys):
    cols = ["Header"]
    rows = [["Data"]]
    styles = ["red"]
    print_rich_table(cols, rows, styles)
    result_out = capsys.readouterr().out

    assert "Data" in result_out
    assert "Header" in result_out
