## Generated todo on 2025-01-16 04:52:17.506751
import typer
import subprocess
from typing import Optional, Any
import sqlite3
from pathlib import Path
from tabulate import tabulate
from rich import print



CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS)
__version__ = '1.0.0'
__cli_name__ = 'todo'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

def aliases_callback(value: bool):
    if value:
        print("""
Command    Aliases
--------   --------
drop       rm
""")
        raise typer.Exit()

@cli.callback()
def main(
    aliases: Optional[bool] = typer.Option(None, '--aliases', callback=aliases_callback, is_eager=True),
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass


def create(name: str):
    db_path = Path(f"{name}.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, task TEXT NOT NULL, done BOOLEAN NOT NULL)")
    
    # insert example tasks
    conn.execute("INSERT INTO tasks (task, done) VALUES ('Fight for your right!', 0)")
    conn.execute("INSERT INTO tasks (task, done) VALUES ('To party!', 1)")
    conn.commit()
    conn.close()
    print(f"✨ Created database {db_path} with tasks table")


cli.command("create", help="Create a new database with tasks table",)(create)

def drop(name: str = typer.Argument(...)):
    db_path = Path(f"{name}.db")
    db_path.unlink()
    print(f"🗑️ Removed database {db_path}")


cli.command("drop", help="Drop a database",)(drop)

cli.command("rm", hidden=True, epilog="Alias for drop")(drop)

def tasks(name: str = typer.Argument(...)):
    conn = sqlite3.connect(f"{name}.db")
    cursor = conn.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    print(tabulate(tasks, headers=['ID', 'Task', 'Done'], tablefmt='grid'))


cli.command("tasks", help="List tasks in database",)(tasks)

def add(name: str = typer.Argument(...), task: str = typer.Argument(...)):
    conn = sqlite3.connect(f"{name}.db")
    conn.execute("INSERT INTO tasks (task, done) VALUES (?, 0)", (task,))
    conn.commit()
    conn.close()
    print(f"📝 Added task: {task}")


cli.command("add", help="Add a new task",)(add)

def complete(name: str = typer.Argument(...), id: int = typer.Argument(...)):
    conn = sqlite3.connect(f"{name}.db")
    conn.execute("UPDATE tasks SET done = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    print(f"🎉 Marked task {id} as complete")


cli.command("complete", help="Mark a task as complete",)(complete)

if __name__ == "__main__":
    cli()
