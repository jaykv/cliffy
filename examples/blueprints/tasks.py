"""A small blueprint: a task runner.

The spec is a name and a mapping of tasks. Every task becomes a command that runs its shell lines in order
and stops at the first one that fails.

    cli run examples/blueprints/tasks.yaml -- greet
    cli build examples/blueprints/tasks.yaml -o dist
"""

from pydantic import BaseModel, Field

from cliffy.blueprint import Blueprint
from cliffy.manifest import CLIManifest, Command, RunBlock


class Task(BaseModel):
    run: str | list[str] = Field(description="Shell line(s) to run, in order.")
    help: str = Field(default="", description="What the task does, shown in --help.")


class Tasks(Blueprint):
    """Task runner: every entry under `tasks` becomes a command that runs shell lines"""

    name: str = Field(description="Name of the CLI.")
    version: str = Field(default="0.1.0", description="Version of the CLI.")
    help: str = Field(default="", description="Description of the CLI.")
    vars: dict[str, str] = Field(default={}, description="Values for the `{{ name }}` expressions in the file.")
    tasks: dict[str, str | list[str] | Task] = Field(
        min_length=1,
        description="Tasks by name. A task is a shell line, a list of shell lines, or a mapping with `run` and `help`.",
    )

    def to_manifest(self) -> CLIManifest:
        commands = {}
        for name, entry in self.tasks.items():
            task = entry if isinstance(entry, Task) else Task(run=entry)
            lines = [task.run] if isinstance(task.run, str) else task.run
            script = "\n".join(f"subprocess.run({line!r}, shell=True, check=True)" for line in lines)
            commands[name] = Command(help=task.help, run=RunBlock(script))

        return CLIManifest(name=self.name, version=self.version, help=self.help, commands=commands)
