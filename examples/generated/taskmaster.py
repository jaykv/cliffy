## Generated taskmaster on 2025-01-09 23:34:10.921034
from typing import Optional, Any
import typer
import subprocess
import json
from datetime import datetime
from tabulate import tabulate


data_file = 'tasks.json'


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="""A task management CLI""")
__version__ = '0.1.0'
__cli_name__ = 'taskmaster'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass

def load_data():
    try:
        with open("tasks.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"projects": [], "tasks": []}

def save_data(data):
    with open("tasks.json", "w") as f:
        json.dump(data, f, indent=2)

def format_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")



def backup():
    subprocess.run(["cp","tasks.json","tasks.json.backup"])
    subprocess.run(["echo","Backup created: tasks.json.backup"])


cli.command("backup", help="Create a backup of the task data",)(backup)
project_app = typer.Typer()
cli.add_typer(project_app, name="project", help="")

def project_add(name: str = typer.Argument(..., help="Name of the project")):
    data = load_data()
    if name not in data["projects"]:
        data["projects"].append(name)
        save_data(data)
        print(f"Project '{name}' added successfully.")
    else:
        print(f"Project '{name}' already exists.")


project_app.command("add", help="",)(project_add)

def project_list():
    data = load_data()
    if data["projects"]:
        print("Projects:")
        for project in data["projects"]:
            print(f"- {project}")
    else:
        print("No projects found.")


project_app.command("list", help="",)(project_list)

def project_remove(name: str = typer.Argument(..., help="Name of the project")):
    data = load_data()
    if name in data["projects"]:
        data["projects"].remove(name)
        data["tasks"] = [task for task in data["tasks"] if task["project"] != name]
        save_data(data)
        print(f"Project '{name}' and its tasks removed successfully.")
    else:
        print(f"Project '{name}' not found.")


project_app.command("remove", help="",)(project_remove)
task_app = typer.Typer()
cli.add_typer(task_app, name="task", help="")

def task_add(project: str = typer.Argument(..., help="Name of the project"), name: str = typer.Argument(..., help="Name of the task"), due_date: str = typer.Option(None, "--due", "-d", help="Due date (YYYY-MM-DD)"), priority: int = typer.Option(1, "--priority", "-p", help="Priority (1-5)", min=1, max=5)):
    data = load_data()
    if project not in data["projects"]:
        print(f"Project '{project}' not found. Please create the project first.")
        return
    task = {
        "project": project,
        "name": name,
        "due_date": due_date,
        "priority": priority,
        "completed": False
    }
    data["tasks"].append(task)
    save_data(data)
    print(f"Task '{name}' added to project '{project}' successfully.")


task_app.command("add", help="",)(task_add)

def task_list(project: str = typer.Argument(..., help="Name of the project")):
    data = load_data()
    tasks = data["tasks"]
    if project:
        tasks = [task for task in tasks if task["project"] == project]
    
    if tasks:
        table_data = [
            [
                task["project"],
                task["name"],
                format_date(task["due_date"]) if task["due_date"] else "N/A",
                task["priority"],
                "x" if task["completed"] else "o"
            ]
            for task in tasks
        ]
        headers = ["Project", "Task", "Due Date", "Priority", "Completed"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    else:
        print("No tasks found.")


task_app.command("list", help="",)(task_list)

def task_complete(project: str = typer.Argument(..., help="Name of the project"), name: str = typer.Argument(..., help="Name of the task")):
    data = load_data()
    for task in data["tasks"]:
        if task["project"] == project and task["name"] == name:
            task["completed"] = True
            save_data(data)
            print(f"Task '{name}' in project '{project}' marked as completed.")
            return
    print(f"Task '{name}' in project '{project}' not found.")


task_app.command("complete", help="",)(task_complete)

def task_remove(project: str = typer.Argument(..., help="Name of the project"), name: str = typer.Argument(..., help="Name of the task")):
    data = load_data()
    data["tasks"] = [task for task in data["tasks"] if task["project"] != project or task["name"] != name]
    save_data(data)
    print(f"Task '{name}' removed from project '{project}' successfully.")


task_app.command("remove", help="",)(task_remove)

if __name__ == "__main__":
    cli()
