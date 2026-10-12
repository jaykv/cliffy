import os
import platform
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cliffy.helper import (
    CLIFFY_CLI_DIR,
    CLIFFY_METADATA_DIR,
    PYTHON_BIN,
    PYTHON_EXECUTABLE,
    age_datetime,
    check_requirement,
    cli_name_problem,
    exit_err,
    get_installed_package_versions,
    import_generated_code,
    import_module_from_path,
    indent_block,
    make_executable,
    out,
    out_err,
    wrap_as_comment,
    wrap_as_var,
    write_atomically,
    write_to_file,
)


# Parametrized tests for write_to_file
@pytest.mark.parametrize(
    "path, text, executable",
    [
        ("test_file.txt", "test content", False),  # id: simple_text_file
        ("test_script.sh", "#!/bin/bash\necho 'Hello'", True),  # id: executable_script
        ("nested/directory/test.txt", "more content", False),  # id: nested_directory
    ],
)
def test_write_to_file(isolated_fs, path, text, executable):
    # Act: in a temporary working directory. The test used to leave `nested/directory` in the repository
    write_to_file(path, text, executable)

    # Assert
    file_path = Path(path)
    assert file_path.exists()
    assert file_path.read_text() == text
    if executable:
        assert os.access(path, os.X_OK)


# Parametrized tests for import_module_from_path
@pytest.mark.parametrize(
    "filepath, expected_module_name",
    [
        ("test_module.py", "test_module"),  # id: simple_module
    ],
)
def test_import_module_from_path(filepath, expected_module_name, tmpdir):
    # Arrange
    module_content = """
def test_function():
    return "test"
"""
    temp_file = tmpdir.join(filepath)
    temp_file.write(module_content)

    # Act
    module = import_module_from_path(str(temp_file))

    # Assert
    assert module.__name__ == expected_module_name
    assert module.test_function() == "test"


def test_import_module_from_path_error(tmpdir):
    # Arrange
    nonexistent_file = tmpdir.join("nonexistent.py")

    # Act & Assert
    with pytest.raises(ImportError):
        import_module_from_path(str(nonexistent_file))


# Test for make_executable
def test_make_executable(tmpdir):
    # Arrange
    temp_file = tmpdir.join("test_script.sh")
    temp_file.write("#!/bin/bash")

    # Act
    make_executable(str(temp_file))

    # Assert
    assert os.access(str(temp_file), os.X_OK)


def test_import_generated_code_removes_its_file(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))

    module, module_path = import_generated_code("answer = 42", "generated_cli")

    assert module.answer == 42
    assert module.__name__ == "generated_cli" and os.path.basename(module_path) == "generated_cli.py"
    assert not os.path.exists(module_path)
    assert list(tmp_path.iterdir()) == []


def test_import_generated_code_removes_its_file_when_the_import_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))

    with pytest.raises(ImportError):
        import_generated_code("import no_such_module_for_cliffy", "generated_cli")

    assert list(tmp_path.iterdir()) == []


# Parametrized tests for indent_block
@pytest.mark.parametrize(
    "block, spaces, expected_output",
    [
        ("line1\nline2", 4, "    line1\n    line2"),  # id: simple_indent
        ("line1\nline2", 2, "  line1\n  line2"),  # id: different_spaces
        ("", 4, ""),  # id: empty_block
    ],
)
def test_indent_block(block, spaces, expected_output):
    # Act
    indented_block = indent_block(block, spaces)

    # Assert
    assert indented_block == expected_output


# Parametrized tests for wrap_as_comment
@pytest.mark.parametrize(
    "text, split_on, expected_output",
    [
        ("test comment", None, "# test comment"),  # id: simple_comment
        ("test comment. second line", ". ", "# test comment\n# second line"),  # id: multiline_comment
        ("", None, "# "),  # id: empty_comment
    ],
)
def test_wrap_as_comment(text, split_on, expected_output):
    # Act
    wrapped_comment = wrap_as_comment(text, split_on)

    # Assert
    assert wrapped_comment == expected_output


# Parametrized tests for wrap_as_var
@pytest.mark.parametrize(
    "text, expected_output",
    [
        ("variable", "{{variable}}"),  # id: simple_variable
        ("", "{{}}"),  # id: empty_variable
    ],
)
def test_wrap_as_var(text, expected_output):
    # Act
    wrapped_var = wrap_as_var(text)

    # Assert
    assert wrapped_var == expected_output


def fake_distribution(name, version):
    dist = MagicMock(version=version)
    dist.metadata = {"Name": name}
    return dist


# Test for get_installed_package_versions (mocking the installed distributions)
@patch("cliffy.helper.distributions")
def test_get_installed_package_versions(mock_distributions):
    # Arrange
    mock_distributions.return_value = [fake_distribution("package1", "1.0.0"), fake_distribution("package2", "2.0.0")]

    # Act
    installed_packages = get_installed_package_versions()

    # Assert
    assert installed_packages == {"package1": "1.0.0", "package2": "2.0.0"}


@patch("cliffy.helper.distributions")
def test_get_installed_package_versions_normalizes_names(mock_distributions):
    # pip freeze prints `PyYAML` and `rich_click` in whatever spelling the project chose
    mock_distributions.return_value = [
        fake_distribution("PyYAML", "6.0.3"),
        fake_distribution("rich_click", "1.9.9"),
        fake_distribution("pyyaml", "5.0"),  # shadowed copy later on sys.path
    ]

    assert get_installed_package_versions() == {"pyyaml": "6.0.3", "rich-click": "1.9.9"}


def test_get_installed_package_versions_sees_real_environment():
    # the old implementation shelled out to `pip freeze`, which skips editable and pip-less installs
    assert "pyyaml" in get_installed_package_versions()


# Parametrized tests for check_requirement
@pytest.mark.parametrize(
    "requirement, installed, expected_output",
    [
        ("package1>=1.0.0", {"package1": "1.0.0"}, None),  # id: with_operator
        ("package2", {"package2": "0.1"}, None),  # id: without_operator
        (" package3 <= 2.0.0 ", {"package3": "2.0.0"}, None),  # id: with_spaces
        ("package==1.0.0", {"package": "1.0.0"}, None),  # id: equal
        ("package>=2.0.0", {"package": "1.0.0"}, "found version `1.0.0`"),  # id: greater_than_or_equal
        ("package<2.0.0", {"package": "1.0.0"}, None),  # id: less_than
        ("package==2.0.0", {"package": "1.0.0"}, "found version `1.0.0`"),  # id: not_equal
        ("package", {}, "not installed"),  # id: missing
        ("PyYAML>=6", {"pyyaml": "6.0.3"}, None),  # id: mixed_case_name
        ("rich_click", {"rich-click": "1.9.9"}, None),  # id: underscore_name
        ("requests>=2,<3", {"requests": "2.32.0"}, None),  # id: multiple_specifiers
        ("requests>=2,<3", {"requests": "3.0.0"}, "found version `3.0.0`"),  # id: multiple_specifiers_unmet
        ("click~=8.0", {"click": "8.5.0"}, None),  # id: compatible_release
        ("click~=8.0", {"click": "9.0.0"}, "found version `9.0.0`"),  # id: compatible_release_unmet
        ("typer[all]>=0.9", {"typer": "0.27.3"}, None),  # id: extras
        ("six<1.0.0", {"six": "1.17.0"}, "found version `1.17.0`"),  # id: less_than_unmet
        ("pywin32; sys_platform == 'no-such-platform'", {}, None),  # id: marker_does_not_apply
        ("package>=1.0.0rc1", {"package": "1.0.0rc2"}, None),  # id: prerelease_installed
    ],
)
def test_check_requirement(requirement, installed, expected_output):
    assert check_requirement(requirement, installed) == expected_output


def test_check_requirement_invalid():
    problem = check_requirement("not a requirement !!", {})
    assert problem is not None and problem.startswith("invalid requirement")


# Tests for out, out_err, and exit_err (using capsys)
def test_out(capsys):
    # Act
    out("test message")

    # Assert
    captured = capsys.readouterr()
    assert "test message" in captured.out


def test_out_err(capsys):
    # Act
    out_err("error message")

    # Assert
    captured = capsys.readouterr()
    assert "error message 💔" in captured.err


def test_exit_err(capsys):
    # Act & Assert
    with pytest.raises(SystemExit):
        exit_err("exit message")
    captured = capsys.readouterr()
    assert "exit message 💔" in captured.err


# Parametrized tests for age_datetime
@pytest.mark.parametrize(
    "date, expected_output",
    [
        (datetime(2023, 1, 1, 12, 0, 0) - timedelta(days=2.0), "2d"),  # id: days_ago
        (datetime(2023, 1, 1, 12, 0, 0) - timedelta(hours=5.0), "5h"),  # id: hours_ago
        (datetime(2023, 1, 1, 12, 0, 0) - timedelta(minutes=30.0), "30m"),  # id: minutes_ago
        (datetime(2023, 1, 1, 12, 0, 0) - timedelta(seconds=10.0), "10s"),  # id: seconds_ago
    ],
)
@patch("cliffy.helper.datetime")
def test_age_datetime(mock_datetime, date, expected_output):
    # Arrange
    mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

    # Act
    aged_datetime = age_datetime(date)

    # Assert
    assert aged_datetime == expected_output


# Tests for constants
def test_constants():
    assert isinstance(CLIFFY_CLI_DIR, Path)
    assert isinstance(CLIFFY_METADATA_DIR, Path)
    assert isinstance(PYTHON_BIN, str)
    assert isinstance(PYTHON_EXECUTABLE, str)

    if platform.system() == "Windows":
        assert "Scripts" in PYTHON_BIN
    else:
        assert "bin" in PYTHON_BIN


def test_write_atomically_replaces_a_link_instead_of_writing_through_it(tmp_path):
    target = tmp_path / "target"
    target.write_text("untouched")
    link = tmp_path / "link"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"symbolic links cannot be created here: {e}")

    write_atomically(str(link), "new")

    assert target.read_text() == "untouched"
    assert not link.is_symlink() and link.read_text() == "new"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["link", "target"]


def test_write_atomically_without_replace_keeps_an_existing_file(tmp_path):
    existing = tmp_path / "existing"
    existing.write_text("kept")

    with pytest.raises(FileExistsError):
        write_atomically(str(existing), "new", replace=False)

    assert existing.read_text() == "kept"
    assert [path.name for path in tmp_path.iterdir()] == ["existing"]

    write_atomically(str(tmp_path / "sub" / "created"), "new", executable=True, replace=False)
    assert (tmp_path / "sub" / "created").read_text() == "new"
    assert os.access(tmp_path / "sub" / "created", os.X_OK)


@pytest.mark.parametrize("name", ["hello", "my-cli", "_x1"])
def test_cli_name_problem_accepts_names(name):
    assert cli_name_problem(name) is None


@pytest.mark.parametrize("name", ["", ".", "..", "../x", "a/b", "a\\b", "-x", "a b", "a.b", "*", "x\n", None])
def test_cli_name_problem_rejects_paths_and_patterns(name):
    assert "not a valid CLI name" in (cli_name_problem(name) or "")
