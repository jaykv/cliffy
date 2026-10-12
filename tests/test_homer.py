import json
import os
from base64 import b32encode
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from cliffy.cli import cli as cliffy_cli
from cliffy.commander import CLI
from cliffy.helper import CLIFFY_METADATA_DIR
from cliffy.homer import (
    get_clis,
    get_metadata,
    get_metadata_bypath,
    get_metadata_path,
    remove_metadata,
    save_metadata,
)
from cliffy.manifest import CLIMetadata


@pytest.mark.parametrize(
    "manifest_path, cli_name, cli_version, requires",
    [
        (
            "test_manifest.yaml",
            "test_cli",
            "0.1.0",
            ["test_req"],
        ),
        (
            "another_test_manifest.yaml",
            "another_test_cli",
            "1.0.0",
            [],
        ),
    ],
    ids=["simple_cli", "another_simple_cli"],
)
def test_save_metadata_happy_path(
    mocker: MockerFixture,
    tmp_path: Path,
    manifest_path: str,
    cli_name: str,
    cli_version: str,
    requires: list,
):
    # Arrange
    manifest_content = "test: content"
    manifest_file = tmp_path / manifest_path
    manifest_file.write_text(manifest_content)

    cli = CLI(name=cli_name, version=cli_version, requires=requires, code="")

    # Act
    save_metadata(str(manifest_file), cli)

    encoded_runnerpath = b32encode(cli.name.encode("ascii")).decode("utf-8")
    expected_metadata_path = f"{CLIFFY_METADATA_DIR}/{encoded_runnerpath}/{cli.name}.json"

    # Assert
    assert get_metadata_path(cli_name) == expected_metadata_path
    assert os.path.exists(expected_metadata_path)
    with open(expected_metadata_path) as f:
        metadata = json.load(f)
        assert metadata["cli_name"] == cli_name
        assert metadata["runner_path"] == str(manifest_file.resolve())
        assert metadata["version"] == cli_version
        assert metadata["manifest"] == manifest_content
        assert metadata["requires"] == requires
        loaded_datetime = datetime.fromisoformat(metadata["loaded"].replace("Z", "+00:00"))
        assert loaded_datetime > datetime.now() - timedelta(seconds=1)

    remove_metadata(cli_name)

    # metadata file removed
    assert not os.path.exists(expected_metadata_path)

    # manifest file not removed
    assert os.path.exists(manifest_file)


def test_save_metadata_manifest_not_found(tmp_path: Path):
    # Arrange
    manifest_path = tmp_path / "non_existent_manifest.json"
    cli = CLI(name="test_cli", version="0.1.0", requires=[], code="")

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        save_metadata(str(manifest_path), cli)


@pytest.mark.parametrize(
    "metadata_content, expected_metadata",
    [
        (
            '{"cli_name": "test_cli", "runner_path": "/path/to/manifest.json", "version": "0.1.0", "loaded": "2024-07-24T12:00:00Z", "manifest": "{}", "requires": []}',  # noqa: E501
            CLIMetadata(
                cli_name="test_cli",
                runner_path="/path/to/manifest.json",
                version="0.1.0",
                loaded=datetime.fromisoformat("2024-07-24T12:00:00+00:00"),
                manifest="{}",
                requires=[],
            ),
        ),
        (
            '{"cli_name": "another_test_cli", "runner_path": "/another/path/to/manifest.json", "version": "1.0.0", "loaded": "2024-07-25T12:00:00Z", "manifest": "[]", "requires": ["test"]}',  # noqa: E501
            CLIMetadata(
                cli_name="another_test_cli",
                runner_path="/another/path/to/manifest.json",
                version="1.0.0",
                loaded=datetime.fromisoformat("2024-07-25T12:00:00+00:00"),
                manifest="[]",
                requires=["test"],
            ),
        ),
    ],
    ids=["simple_metadata", "another_simple_metadata"],
)
def test_get_metadata_bypath_happy_path(
    mocker: MockerFixture, tmp_path: Path, metadata_content: str, expected_metadata: CLIMetadata
):
    # Arrange
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(metadata_content)

    # Act
    metadata = get_metadata_bypath(metadata_file)

    # Assert
    assert metadata == expected_metadata


def test_get_metadata_bypath_invalid_json(mocker: MockerFixture, tmp_path: Path):
    # Arrange
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text("invalid json")

    # Act
    metadata = get_metadata_bypath(metadata_file)

    # Assert
    # the name of the CLI is the file name without `.json`: that is the name `cli rm` looks up
    assert metadata.cli_name == "metadata"
    assert metadata.runner_path == str(metadata_file)
    assert metadata.version == "error"
    assert "could not load" in metadata.manifest


@pytest.mark.parametrize(
    "cli_name, expected_metadata",
    [
        ("test_cli", None),
        ("another_test_cli", None),
    ],
    ids=["non_existent_cli", "another_non_existent_cli"],
)
def test_get_metadata_non_existent(mocker: MockerFixture, tmp_path: Path, cli_name: str, expected_metadata):
    # Act
    metadata = get_metadata(cli_name)

    # Assert
    assert metadata == expected_metadata


def test_get_clis(mocker: MockerFixture, tmp_path: Path):
    # Arrange
    metadata_files = [
        f"{CLIFFY_METADATA_DIR}/M53====/test_cli_1.json",
        f"{CLIFFY_METADATA_DIR}/ONXW2ZJAMNXIW===/test_cli_2.json",
    ]
    metadata = [
        '{"cli_name": "test_cli_1", "runner_path": "/path/to/manifest.json", "version": "0.1.0", "loaded": "2024-07-24T12:00:00Z", "manifest": "{}", "requires": []}',  # noqa: E501
        '{"cli_name": "test_cli_2", "runner_path": "/another/path/to/manifest.json", "version": "1.0.0", "loaded": "2024-07-25T12:00:00Z", "manifest": "[]", "requires": ["test"]}',  # noqa: E501
    ]

    for i, file_path in enumerate(metadata_files):
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(metadata[i])

    # Act
    clis = list(get_clis())

    # Assert
    for cli in metadata:
        expected_metadata = CLIMetadata.model_validate_json(cli)
        assert expected_metadata in clis


@pytest.fixture
def metadata_dir(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch("cliffy.homer.CLIFFY_METADATA_DIR", tmp_path)
    return tmp_path


def save_cli(tmp_path: Path, name: str) -> None:
    manifest_path = tmp_path / f"{name}-manifest.yaml"
    manifest_path.write_text("name: x")
    save_metadata(str(manifest_path), CLI(name=name, version="1", code=""))


def test_remove_metadata_matches_name_literally(metadata_dir: Path):
    save_cli(metadata_dir, "first")
    save_cli(metadata_dir, "second")

    # `cli rm '*'` used to delete the metadata of every CLI and leave their scripts behind
    assert get_metadata_path("*") is None
    remove_metadata("*")
    remove_metadata("f?rst")

    assert {cli.cli_name for cli in get_clis()} == {"first", "second"}


def test_remove_metadata_keeps_directory_with_other_files(metadata_dir: Path):
    save_cli(metadata_dir, "first")
    metadata_path = get_metadata_path("first")
    assert metadata_path
    stray_file = Path(metadata_path).parent / ".DS_Store"
    stray_file.write_text("")

    remove_metadata("first")

    assert not Path(metadata_path).exists()
    assert stray_file.exists()


def test_get_metadata_bypath_closes_file(metadata_dir: Path):
    import warnings

    save_cli(metadata_dir, "first")
    metadata_path = get_metadata_path("first")
    assert metadata_path

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert get_metadata_bypath(Path(metadata_path)).cli_name == "first"

    assert not [w for w in caught if issubclass(w.category, ResourceWarning)]


@pytest.mark.parametrize("command", ["rm", "rm-all"])
def test_corrupt_metadata_can_be_removed(metadata_dir: Path, command: str):
    # it was listed as `first.json`, a name that `cli rm` and `cli rm-all` could not find
    save_cli(metadata_dir, "first")
    metadata_path = get_metadata_path("first")
    assert metadata_path
    Path(metadata_path).write_text("{ not json")

    listed = [cli.cli_name for cli in get_clis()]
    assert listed == ["first"]

    result = CliRunner().invoke(cliffy_cli, [command] if command == "rm-all" else [command, *listed])

    assert result.exit_code == 0, result.output
    assert not Path(metadata_path).exists()
    assert list(get_clis()) == []
