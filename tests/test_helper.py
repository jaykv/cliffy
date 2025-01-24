import pytest
import os
import platform
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from cliffy.helper import (
    RequirementSpec,
    write_to_file,
    import_module_from_path,
    make_executable,
    delete_temp_files,
    indent_block,
    wrap_as_comment,
    wrap_as_var,
    get_installed_package_versions,
    parse_requirement,
    compare_versions,
    out,
    out_err,
    exit_err,
    age_datetime,
    CLIFFY_CLI_DIR,
    CLIFFY_METADATA_DIR,
    PYTHON_BIN,
    PYTHON_EXECUTABLE,
    OPERATOR_MAP,
    TEMP_FILES,
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
def test_write_to_file(path, text, executable):
    # Act
    write_to_file(path, text, executable)

    # Assert
    file_path = Path(path)
    assert file_path.exists()
    assert file_path.read_text() == text
    if executable:
        assert os.access(path, os.X_OK)

    # Cleanup
    file_path.unlink()
    if executable:
        try:
            file_path.parent.rmdir()
            file_path.parent.parent.rmdir()
        except OSError:
            pass  # Directory not empty


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


# Test for delete_temp_files
def test_delete_temp_files():
    # Arrange
    temp_file = NamedTemporaryFile(delete=False)
    TEMP_FILES.append(temp_file)

    # Act
    delete_temp_files()

    # Assert
    assert not Path(temp_file.name).exists()
    assert TEMP_FILES == []


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


# Test for get_installed_package_versions (mocking subprocess)
@patch("subprocess.check_output")
def test_get_installed_package_versions(mock_check_output):
    # Arrange
    mock_check_output.return_value = b"package1==1.0.0\npackage2==2.0.0"

    # Act
    installed_packages = get_installed_package_versions()

    # Assert
    assert installed_packages == {"package1": "1.0.0", "package2": "2.0.0"}


# Parametrized tests for parse_requirement
@pytest.mark.parametrize(
    "requirement, expected_output",
    [
        ("package1>=1.0.0", RequirementSpec(name="package1", operator=">=", version="1.0.0")),  # id: with_operator
        ("package2", RequirementSpec(name="package2", operator=None, version=None)),  # id: without_operator
        (" package3 <= 2.0.0 ", RequirementSpec(name="package3", operator="<=", version="2.0.0")),  # id: with_spaces
    ],
)
def test_parse_requirement(requirement, expected_output):
    # Act
    parsed_req = parse_requirement(requirement)

    # Assert
    assert parsed_req == expected_output


# Parametrized tests for compare_versions
@pytest.mark.parametrize(
    "version1, version2, op, expected_output",
    [
        ("1.0.0", "1.0.0", "==", True),  # id: equal
        ("1.0.0", "2.0.0", ">=", False),  # id: greater_than_or_equal
        ("1.0.0", "2.0.0", "<", True),  # id: less_than
        ("1.0.0", "1.0.0", None, True),  # id: no_operator_equal
        ("1.0.0", "2.0.0", None, False),  # id: no_operator_not_equal
    ],
)
def test_compare_versions(version1, version2, op, expected_output):
    # Act
    comparison_result = compare_versions(version1, version2, op)

    # Assert
    assert comparison_result == expected_output


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
    assert isinstance(OPERATOR_MAP, dict)
    assert isinstance(TEMP_FILES, list)

    if platform.system() == "Windows":
        assert "Scripts" in PYTHON_BIN
    else:
        assert "bin" in PYTHON_BIN
