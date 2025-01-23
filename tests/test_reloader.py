import pytest
import io
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from cliffy.reloader import Reloader
from watchdog.events import FileModifiedEvent


@pytest.mark.parametrize(
    "manifest_path, run_cli, run_cli_args, cli_name, cli_version, cli_code",
    [
        ("manifest.yaml", True, ("arg1", "arg2"), "test_cli", "0.1.0", "print('Hello')"),  # id: happy_path_run_cli
        ("manifest.json", False, (), "another_cli", "1.0.0", "print('World')"),  # id: happy_path_no_run_cli
        (
            "nested/path/manifest.yaml",
            True,
            ("--flag",),
            "complex_cli",
            "2.3.4",
            "import os; print(os.environ)",
        ),  # id: happy_path_nested
    ],
)
@patch("cliffy.reloader.out")
@patch("cliffy.reloader.save_metadata")
@patch("cliffy.reloader.Loader.load_from_cli")
@patch("cliffy.reloader.cli_runner")
@patch("cliffy.reloader.Transformer")
@patch("cliffy.reloader.open")
def test_reload_happy_path(
    mock_open,
    MockTransformer,
    mock_cli_runner,
    mock_load_from_cli,
    mock_save_metadata,
    mock_out,
    manifest_path,
    run_cli,
    run_cli_args,
    cli_name,
    cli_version,
    cli_code,
):
    # Arrange
    mock_manifest_io = io.StringIO("")
    mock_open.return_value = mock_manifest_io
    MockTransformer.return_value.cli.name = cli_name
    MockTransformer.return_value.cli.version = cli_version
    MockTransformer.return_value.cli.code = cli_code

    # Act
    Reloader.reload(manifest_path, run_cli, run_cli_args)

    # Assert
    MockTransformer.assert_called_once_with(mock_manifest_io)
    mock_load_from_cli.assert_called_once_with(MockTransformer.return_value.cli)
    mock_save_metadata.assert_called_once_with(manifest_path, MockTransformer.return_value.cli)
    mock_out.assert_called_once_with(f"✨ Reloaded {cli_name} CLI v{cli_version} ✨", fg="green")
    if run_cli:
        mock_cli_runner.assert_called_once_with(cli_name, cli_code, run_cli_args)
    else:
        mock_cli_runner.assert_not_called()


@pytest.mark.parametrize(
    "event, manifest_path",
    [
        (MagicMock(is_directory=True, src_path=""), "manifest.yaml"),  # id: directory_modified
        (MagicMock(is_directory=False, src_path="other_file.txt"), "manifest.yaml"),  # id: other_file_modified
        (
            MagicMock(is_directory=False, src_path="manifest.yaml"),
            "other_manifest.yaml",
        ),  # id: wrong_manifest_modified
        (MagicMock(is_directory=False, src_path="manifest.yaml"), "manifest.yaml"),  # id: file_modified
    ],
)
def test_on_modified(event, manifest_path):
    # Arrange
    reloader = Reloader(manifest_path, False, ())
    reloader.last_modified = datetime.now() - timedelta(seconds=2)
    with patch("threading.Thread") as mock_thread:
        # Act
        reloader.on_modified(event)

        # Assert
        if (
            event.is_directory
            or not str(event.src_path).endswith(manifest_path)
            or not isinstance(event, FileModifiedEvent)
        ):
            mock_thread.assert_not_called()


@pytest.fixture
def reloader():
    return Reloader("manifest.yaml", False, ())


def test_on_modified_rapid_change(reloader):
    # Arrange
    event = MagicMock(is_directory=False, src_path=reloader.manifest_path)
    reloader.last_modified = datetime.now()

    with patch("threading.Thread") as mock_thread:
        # Act
        reloader.on_modified(event)

        # Assert
        mock_thread.assert_not_called()


@patch("cliffy.reloader.Observer")
@patch("cliffy.reloader.time.sleep")
def test_watch_multiple_iterations(mock_sleep, MockObserver):
    # Arrange
    mock_sleep.side_effect = [None, None, KeyboardInterrupt]

    # Act
    Reloader.watch("manifest.yaml", False, ())

    # Assert
    assert mock_sleep.call_count == 3
    MockObserver.return_value.schedule.assert_called_once()
    MockObserver.return_value.start.assert_called_once()
    MockObserver.return_value.stop.assert_called_once()
    MockObserver.return_value.join.assert_called_once()


@patch("cliffy.reloader.Observer")
def test_watch_observer_exception(MockObserver):
    # Arrange
    MockObserver.return_value.start.side_effect = Exception("Observer error")

    # Act & Assert
    with pytest.raises(Exception, match="Observer error"):
        Reloader.watch("manifest.yaml", False, ())

    MockObserver.return_value.stop.assert_not_called()
    MockObserver.return_value.join.assert_not_called()


@patch("cliffy.reloader.Observer")
def test_watch_join_exception(MockObserver):
    # Arrange
    MockObserver.return_value.join.side_effect = Exception("Join error")
    mock_sleep = MagicMock(side_effect=KeyboardInterrupt)

    with patch("time.sleep", mock_sleep):
        # Act & Assert
        with pytest.raises(Exception, match="Join error"):
            Reloader.watch("manifest.yaml", False, ())

        MockObserver.return_value.stop.assert_called_once()


@pytest.mark.parametrize(
    "manifest_path, error_source",
    [
        ("manifest.yaml", "transform"),  # Transform fails
        ("manifest.yaml", "load"),  # Loading fails
        ("manifest.yaml", "save"),  # Save metadata fails
        ("manifest.yaml", "run"),  # CLI run fails
    ],
)
@patch("cliffy.reloader.out")
@patch("cliffy.reloader.save_metadata")
@patch("cliffy.reloader.Loader.load_from_cli")
@patch("cliffy.reloader.cli_runner")
@patch("cliffy.reloader.Transformer")
@patch("cliffy.reloader.open")
def test_reload_error_cases(
    mock_open,
    MockTransformer,
    mock_cli_runner,
    mock_load_from_cli,
    mock_save_metadata,
    mock_out,
    manifest_path,
    error_source,
):
    # Arrange
    mock_manifest_io = io.StringIO("")
    mock_open.return_value = mock_manifest_io

    error_msg = "Operation failed"
    if error_source == "transform":
        MockTransformer.side_effect = Exception(error_msg)
    elif error_source == "load":
        mock_load_from_cli.side_effect = Exception(error_msg)
    elif error_source == "save":
        mock_save_metadata.side_effect = Exception(error_msg)
    else:
        mock_cli_runner.side_effect = Exception(error_msg)

    # Act & Assert
    with pytest.raises(Exception, match=error_msg):
        Reloader.reload(manifest_path, True, ())


@patch("cliffy.reloader.Observer")
def test_watch_cleanup_on_multiple_interrupts(MockObserver):
    # Arrange
    mock_sleep = MagicMock(side_effect=[None, KeyboardInterrupt, KeyboardInterrupt])

    with patch("time.sleep", mock_sleep):
        # Act
        Reloader.watch("manifest.yaml", False, ())

        # Assert
        MockObserver.return_value.stop.assert_called_once()
        MockObserver.return_value.join.assert_called_once()


def test_on_modified_thread_safety(reloader):
    # Arrange
    event = MagicMock(is_directory=False, src_path="manifest.yaml")
    reloader.last_modified = datetime.now() - timedelta(seconds=0.1)

    with patch("threading.Thread") as mock_thread:
        # Act
        for _ in range(5):  # Simulate rapid consecutive modifications
            reloader.on_modified(event)
            time.sleep(0.01)

        # Assert
        assert mock_thread.call_count <= 1  # Should debounce multiple calls


@pytest.mark.parametrize(
    "manifest_path",
    [
        "",  # Empty path
        "   ",  # Whitespace path
        "/invalid/*/path",  # Invalid characters
        "very/deep/nested/path/that/might/exceed/os/limits/manifest.yaml",
    ],
)
@patch("cliffy.reloader.Transformer")
def test_reload_invalid_paths(mock_transformer, manifest_path):
    # Act & Assert
    with pytest.raises(Exception):
        Reloader.reload(manifest_path, False, ())
    mock_transformer.assert_not_called()


def test_thread_daemon_property(reloader):
    # Arrange
    event = FileModifiedEvent(src_path="manifest.yaml")
    reloader.last_modified = datetime.now() - timedelta(seconds=2)

    with patch("threading.Thread") as mock_thread:
        # Act
        reloader.on_modified(event)

        # Assert
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs.get("target") == reloader.reload
        assert kwargs.get("args") == (reloader.manifest_path, reloader.run_cli, reloader.run_cli_args)
        mock_thread.return_value.daemon = True
        mock_thread.return_value.start.assert_called_once()


def test_concurrent_modifications(reloader):
    # Arrange
    event = FileModifiedEvent(src_path="manifest.yaml")
    reloader.last_modified = datetime.now() - timedelta(seconds=2)

    with patch("threading.Thread") as mock_thread:
        # Act
        # Simulate concurrent modifications
        reloader.on_modified(event)
        reloader.on_modified(event)  # Should be ignored due to timing

        # Assert
        mock_thread.assert_called_once()


@pytest.mark.parametrize(
    "time_diff",
    [
        timedelta(milliseconds=500),  # Less than 1 second
        timedelta(milliseconds=999),  # Just under 1 second
        timedelta(seconds=0),  # Immediate subsequent modification
    ],
)
def test_modification_throttling(reloader, time_diff):
    # Arrange
    event = MagicMock(is_directory=False, src_path="manifest.yaml")
    reloader.last_modified = datetime.now() - time_diff

    with patch("threading.Thread") as mock_thread:
        # Act
        reloader.on_modified(event)

        # Assert
        mock_thread.assert_not_called()


def test_thread_exception_handling(reloader):
    # Arrange
    event = FileModifiedEvent(src_path="manifest.yaml")
    reloader.last_modified = datetime.now() - timedelta(seconds=2)

    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value.start.side_effect = RuntimeError("Thread error")

        # Act & Assert
        reloader.on_modified(event)  # Should not raise exception
        mock_thread.assert_called_once()


def test_multiple_thread_creation(reloader):
    # Arrange
    event = FileModifiedEvent(src_path="manifest.yaml")

    with patch("threading.Thread") as mock_thread:
        # Act
        # First modification
        reloader.last_modified = datetime.now() - timedelta(seconds=2)
        reloader.on_modified(event)

        # Second modification after delay
        reloader.last_modified = datetime.now() - timedelta(seconds=2)
        reloader.on_modified(event)

        # Assert
        assert mock_thread.call_count == 2
        for call in mock_thread.call_args_list:
            args, kwargs = call
            assert kwargs.get("target") == reloader.reload
            assert kwargs.get("args") == (reloader.manifest_path, reloader.run_cli, reloader.run_cli_args)
