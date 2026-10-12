import itertools
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

# One reload at a time, for all manifests: a reload reads the manifest and writes the launcher, the module
# and the metadata record, and two of them must not interleave.
RELOAD_LOCK = threading.Lock()
GENERATIONS = itertools.count(1)
# manifest path -> generation of the newest change a reload was started for
NEWEST_GENERATION: dict[str, int] = {}

FileSignature = tuple[int, int] | None


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
        # what the watched files looked like at the last change a reload was started for
        self.reloaded_signature: dict[str, FileSignature] | None = None
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

        # A save is reported more than once. Within a second of the last reload an event is only a new
        # change when a watched file differs from what that reload was started for.
        signature = self.watched_signature()
        if datetime.now() - self.last_modified < timedelta(seconds=1) and signature == self.reloaded_signature:
            return

        self.last_modified = datetime.now()
        self.refresh_watched_files()
        self.reloaded_signature = self.watched_signature()

        generation = next(GENERATIONS)
        t = threading.Thread(
            target=self.reload,
            args=(self.manifest_path, self.run_cli, self.run_cli_args),
            kwargs={"blueprint": self.blueprint, "generation": generation},
            daemon=True,
        )
        try:
            t.start()
        except RuntimeError as e:
            # Log the error or handle it as needed
            out_err(f"Failed to start thread: {e}")
            return
        # only once its reload runs: reloads of older changes that are still waiting can then be skipped
        NEWEST_GENERATION[self.manifest_realpath] = max(generation, NEWEST_GENERATION.get(self.manifest_realpath, 0))

    def watched_signature(self) -> dict[str, FileSignature]:
        """Modification time and size of every watched file, None for one that cannot be read."""
        signature: dict[str, FileSignature] = {}
        for path in sorted(self.watched_files):
            try:
                status = os.stat(path)
                signature[path] = (status.st_mtime_ns, status.st_size)
            except OSError:
                signature[path] = None
        return signature

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
    def reload(
        manifest_path: str,
        run_cli: bool,
        run_cli_args: tuple,
        blueprint: str | None = None,
        generation: int | None = None,
    ) -> None:
        """Generate the CLI from the manifest as it is now and load it.

        Reloads run one after the other, and each reads the manifest only once it is its turn: the one
        that runs last loads the newest text, whatever order the threads were started in.

        Args:
            generation: Number of the change this reload was started for. A reload is skipped when a
                reload for a newer change of the same manifest has been started: that one does the work.
        """

        def superseded() -> bool:
            newest = NEWEST_GENERATION.get(os.path.realpath(manifest_path), 0)
            return generation is not None and generation < newest

        with RELOAD_LOCK:
            if superseded():
                return
            with open(manifest_path, encoding="utf-8") as manifest_io:
                T = Transformer(manifest_io, blueprint=blueprint) if blueprint else Transformer(manifest_io)
            Loader.load_from_cli(T.cli)
            save_metadata(manifest_path, T.cli)
            out(f"✨ Reloaded {T.cli.name} CLI v{T.cli.version} ✨", fg="green")

        # not under the lock: a CLI that keeps running must not hold up the next reload
        if run_cli and not superseded():
            cli_runner(T.cli.name, T.cli.code, run_cli_args)
