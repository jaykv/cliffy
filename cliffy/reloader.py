import os
import threading
import time
from datetime import datetime, timedelta

from watchdog.events import FileModifiedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from cliffy.builder import run_cli as cli_runner
from cliffy.helper import out, out_err
from cliffy.homer import save_metadata
from cliffy.loader import Loader
from cliffy.transformer import Transformer, source_files


class Reloader(FileSystemEventHandler):
    def __init__(self, manifest_path: str, run_cli: bool, run_cli_args: tuple, blueprint: str | None = None) -> None:
        self.manifest_path = manifest_path
        self.manifest_realpath = os.path.realpath(manifest_path)
        self.run_cli = run_cli
        self.run_cli_args = run_cli_args
        self.blueprint = blueprint
        self.last_modified = datetime.now()
        self.observer: BaseObserver | None = None
        self.scheduled_directories: set[str] = set()
        # the manifest, the manifests it includes and the Python file of its blueprint
        self.watched_files: set[str] = set()
        self.refresh_watched_files()

        super().__init__()

    def refresh_watched_files(self) -> None:
        """Reads which files the CLI is generated from. They change with the manifest, i.e. a new include."""
        self.watched_files = source_files(self.manifest_path, self.blueprint)
        if self.observer:
            for directory in sorted(self.watched_directories() - self.scheduled_directories):
                self.observer.schedule(self, path=directory, recursive=False)
                self.scheduled_directories.add(directory)

    def watched_directories(self) -> set[str]:
        return {os.path.dirname(path) for path in self.watched_files}

    def on_modified(self, event: FileSystemEvent) -> None:
        # compared as full paths: `endswith` also matched other-x.yaml when watching x.yaml
        if event.is_directory or os.path.realpath(os.fsdecode(event.src_path)) not in self.watched_files:
            return

        if not isinstance(event, FileModifiedEvent):
            return

        if datetime.now() - self.last_modified < timedelta(seconds=1):
            return

        self.last_modified = datetime.now()
        self.refresh_watched_files()

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
        event_handler.observer = observer
        event_handler.refresh_watched_files()
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
