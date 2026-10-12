import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from watchdog.events import FileModifiedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from cliffy.builder import run_cli as cli_runner
from cliffy.helper import out, out_err
from cliffy.homer import save_metadata
from cliffy.loader import Loader
from cliffy.transformer import Transformer


class Reloader(FileSystemEventHandler):
    def __init__(self, manifest_path: str, run_cli: bool, run_cli_args: tuple, blueprint: str | None = None) -> None:
        self.manifest_path = manifest_path
        self.manifest_realpath = os.path.realpath(manifest_path)
        self.run_cli = run_cli
        self.run_cli_args = run_cli_args
        self.blueprint = blueprint
        self.last_modified = datetime.now()

        super().__init__()

    def on_modified(self, event: FileSystemEvent) -> None:
        # compared as full paths: `endswith` also matched other-x.yaml when watching x.yaml
        if event.is_directory or os.path.realpath(os.fsdecode(event.src_path)) != self.manifest_realpath:
            return

        if not isinstance(event, FileModifiedEvent):
            return

        if datetime.now() - self.last_modified < timedelta(seconds=1):
            return

        self.last_modified = datetime.now()

        t = threading.Thread(
            target=self.reload,
            args=(self.manifest_path, self.run_cli, self.run_cli_args),
            kwargs={"blueprint": self.blueprint},
            daemon=True,
        )
        try:
            t.start()
        except RuntimeError as e:
            # Log the error or handle it as needed
            out_err(f"Failed to start thread: {e}")

    @classmethod
    def watch(cls, manifest_path: str, run_cli: bool, run_cli_args: tuple, blueprint: str | None = None) -> None:
        event_handler = cls(manifest_path, run_cli, run_cli_args, blueprint)
        observer = Observer()
        observer.schedule(event_handler, path=str(Path(manifest_path).parent), recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            # also stops the observer thread when the loop dies of anything else
            observer.stop()
            observer.join()

    @staticmethod
    def reload(manifest_path: str, run_cli: bool, run_cli_args: tuple, blueprint: str | None = None) -> None:
        with open(manifest_path, encoding="utf-8") as manifest_io:
            T = Transformer(manifest_io, blueprint=blueprint) if blueprint else Transformer(manifest_io)
        Loader.load_from_cli(T.cli)
        save_metadata(manifest_path, T.cli)
        out(f"✨ Reloaded {T.cli.name} CLI v{T.cli.version} ✨", fg="green")

        if run_cli:
            cli_runner(T.cli.name, T.cli.code, run_cli_args)
