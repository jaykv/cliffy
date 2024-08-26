from .transformer import Transformer
from .loader import Loader
from .homer import save_metadata
from .helper import out
from .builder import run_cli as cli_runner

import time
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from pathlib import Path
import threading


class Reloader(FileSystemEventHandler):
    def __init__(self, manifest_path: str, run_cli: bool, run_cli_args: tuple[str]) -> None:
        self.manifest_path = manifest_path
        self.run_cli = run_cli
        self.run_cli_args = run_cli_args
        self.last_modified = datetime.now()

        super().__init__()

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(self.manifest_path):
            return

        if not isinstance(event, FileModifiedEvent):
            return

        if datetime.now() - self.last_modified < timedelta(seconds=1):
            return

        self.last_modified = datetime.now()

        t = threading.Thread(target=self.reload, args=(self.manifest_path, self.run_cli, self.run_cli_args))
        t.daemon = True
        t.start()

    @classmethod
    def watch(cls, manifest_path: str, run_cli: bool, run_cli_args: tuple[str]):
        event_handler = cls(manifest_path, run_cli, run_cli_args)
        observer = Observer()
        observer.schedule(event_handler, path=Path(manifest_path).parent, recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    @staticmethod
    def reload(manifest_path: str, run_cli: bool, run_cli_args: tuple[str]):
        manifest_io = open(manifest_path, "r")

        T = Transformer(manifest_io)
        Loader.load_from_cli(T.cli)
        save_metadata(manifest_io.name, T.cli)
        out(f"✨ Reloaded {T.cli.name} CLI v{T.cli.version} ✨", fg="green")

        if run_cli:
            cli_runner(T.cli.name, T.cli.code, run_cli_args)
