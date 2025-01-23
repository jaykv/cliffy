import sys
import unittest

from cliffy.builder import TEMP_FILES, build_cli_from_manifest, run_cli
from io import StringIO, TextIOWrapper
from unittest.mock import Mock, call, patch

class TestBuilder(unittest.TestCase):
    @patch('cliffy.builder.Transformer')
    @patch('cliffy.builder.build_cli')
    def test_build_cli_from_manifest(self, mock_build_cli, mock_transformer):
        """
        Test that build_cli_from_manifest correctly processes the manifest and calls build_cli
        with the expected arguments.
        """
        # Mock the manifest file
        mock_manifest = Mock(spec=TextIOWrapper)

        # Set up the mock Transformer
        mock_transformer_instance = Mock()
        mock_transformer_instance.cli.name = 'test_cli'
        mock_transformer_instance.cli.code = 'print("Hello, World!")'
        mock_transformer_instance.cli.requires = ['requests']
        mock_transformer.return_value = mock_transformer_instance

        # Set up the mock build_cli result
        mock_build_cli.return_value = Mock()

        # Call the function under test
        cli, result = build_cli_from_manifest(mock_manifest, output_dir='/tmp', interpreter='/usr/bin/python3')

        # Assert that Transformer was called with the correct arguments
        mock_transformer.assert_called_once_with(mock_manifest, validate_requires=False)

        # Assert that build_cli was called with the correct arguments
        mock_build_cli.assert_called_once()
        args, kwargs = mock_build_cli.call_args
        self.assertEqual(args[0], 'test_cli')
        self.assertIn('test_cli_', kwargs['script_path'])
        self.assertEqual(kwargs['deps'], ['requests'])
        self.assertEqual(kwargs['output_dir'], '/tmp')
        self.assertEqual(kwargs['interpreter'], '/usr/bin/python3')

        # Assert that the function returns the expected values
        self.assertEqual(cli, mock_transformer_instance.cli)
        self.assertEqual(result, mock_build_cli.return_value)

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.sys')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_sys, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Run the CLI
        run_cli(cli_name, script_code, args)

        # Assert that the script was written to the temporary file
        mock_file.write.assert_called_once_with(script_code)
        mock_file.flush.assert_called_once()

        # Assert that sys.argv was modified correctly
        self.assertEqual(mock_sys.argv, [mock_file.name] + list(args))

        # Assert that the CLI function was called
        mock_module.cli.assert_called_once()

        # Assert that the temporary file was added to TEMP_FILES
        self.assertIn(mock_file, TEMP_FILES)

        # Assert that delete_temp_files was called
        mock_delete_temp_files.assert_called_once()

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.sys')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_sys, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Run the CLI
        run_cli(cli_name, script_code, args)

        # Assert that the script was written to the temporary file
        mock_file.write.assert_called_once_with(script_code)
        mock_file.flush.assert_called_once()

        # Assert that sys.argv was modified correctly
        self.assertEqual(mock_sys.argv, [mock_file.name] + list(args))

        # Assert that the CLI function was called
        mock_module.cli.assert_called_once()

        # Assert that the temporary file was added to TEMP_FILES
        self.assertIn(mock_file, TEMP_FILES)

        # Assert that delete_temp_files was called
        mock_delete_temp_files.assert_called_once()

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.sys')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_sys, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Run the CLI
        run_cli(cli_name, script_code, args)

        # Assert that the script was written to the temporary file
        mock_file.write.assert_called_once_with(script_code)
        mock_file.flush.assert_called_once()

        # Assert that sys.argv was modified correctly
        self.assertEqual(mock_sys.argv, [mock_file.name] + list(args))

        # Assert that the CLI function was called
        mock_module.cli.assert_called_once()

        # Assert that the temporary file was added to TEMP_FILES
        self.assertIn(mock_file, TEMP_FILES)

        # Assert that delete_temp_files was called
        mock_delete_temp_files.assert_called_once()

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.sys')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_sys, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Run the CLI
        run_cli(cli_name, script_code, args)

        # Assert that the script was written to the temporary file
        mock_file.write.assert_called_once_with(script_code)
        mock_file.flush.assert_called_once()

        # Assert that sys.argv was modified correctly
        self.assertEqual(mock_sys.argv, [mock_file.name] + list(args))

        # Assert that the CLI function was called
        mock_module.cli.assert_called_once()

        # Assert that the temporary file was added to TEMP_FILES
        self.assertIn(mock_file, TEMP_FILES)

        # Assert that delete_temp_files was called
        mock_delete_temp_files.assert_called_once()

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.sys')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_sys, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Run the CLI
        run_cli(cli_name, script_code, args)

        # Assert that the script was written to the temporary file
        mock_file.write.assert_called_once_with(script_code)
        mock_file.flush.assert_called_once()

        # Assert that sys.argv was modified correctly
        self.assertEqual(mock_sys.argv, [mock_file.name] + list(args))

        # Assert that the CLI function was called
        mock_module.cli.assert_called_once()

        # Assert that the temporary file was added to TEMP_FILES
        self.assertIn(mock_file, TEMP_FILES)

        # Assert that delete_temp_files was called
        mock_delete_temp_files.assert_called_once()

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.sys')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_sys, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Run the CLI
        run_cli(cli_name, script_code, args)

        # Assert that the script was written to the temporary file
        mock_file.write.assert_called_once_with(script_code)
        mock_file.flush.assert_called_once()

        # Assert that sys.argv was modified correctly
        self.assertEqual(mock_sys.argv, [mock_file.name] + list(args))

        # Assert that the CLI function was called
        mock_module.cli.assert_called_once()

        # Assert that the temporary file was added to TEMP_FILES
        self.assertIn(mock_file, TEMP_FILES)

        # Assert that delete_temp_files was called
        mock_delete_temp_files.assert_called_once()

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.sys')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_sys, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Run the CLI
        run_cli(cli_name, script_code, args)

        # Assert that the script was written to the temporary file
        mock_file.write.assert_called_once_with(script_code)
        mock_file.flush.assert_called_once()

        # Assert that sys.argv was modified correctly
        self.assertEqual(mock_sys.argv, [mock_file.name] + list(args))

        # Assert that the CLI function was called
        mock_module.cli.assert_called_once()

        # Assert that the temporary file was added to TEMP_FILES
        self.assertIn(mock_file, TEMP_FILES)

        # Assert that delete_temp_files was called
        mock_delete_temp_files.assert_called_once()

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Store the original sys.argv
        original_argv = sys.argv.copy()

        try:
            # Run the CLI
            run_cli(cli_name, script_code, args)

            # Assert that the script was written to the temporary file
            mock_file.write.assert_called_once_with(script_code)
            mock_file.flush.assert_called_once()

            # Assert that sys.argv was modified correctly
            self.assertEqual(sys.argv, [mock_file.name] + list(args))

            # Assert that the CLI function was called
            mock_module.cli.assert_called_once()

            # Assert that the temporary file was added to TEMP_FILES
            self.assertIn(mock_file, TEMP_FILES)

            # Assert that delete_temp_files was called
            mock_delete_temp_files.assert_called_once()

        finally:
            # Restore the original sys.argv
            sys.argv = original_argv

    @patch('cliffy.builder.import_module_from_path')
    @patch('cliffy.builder.NamedTemporaryFile')
    @patch('cliffy.builder.delete_temp_files')
    def test_run_cli(self, mock_delete_temp_files, mock_temp_file, mock_import_module):
        """
        Test that run_cli correctly executes the CLI script with given arguments.
        This test verifies:
        1. The script is written to a temporary file
        2. sys.argv is modified correctly and restored after execution
        3. The imported module's CLI function is called
        4. Temporary files are properly managed
        5. delete_temp_files is called
        """
        # Mock the temporary file
        mock_file = Mock()
        mock_file.name = 'test_cli.py'
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock the imported module
        mock_module = Mock()
        mock_import_module.return_value = mock_module

        # Set up test CLI code and arguments
        cli_name = 'test_cli'
        script_code = 'print("Hello from CLI")'
        args = ('arg1', 'arg2')

        # Store the original sys.argv and TEMP_FILES
        original_argv = sys.argv.copy()
        original_temp_files = TEMP_FILES.copy()

        try:
            # Run the CLI
            run_cli(cli_name, script_code, args)

            # Assert that the script was written to the temporary file
            mock_file.write.assert_called_once_with(script_code)
            mock_file.flush.assert_called_once()

            # Assert that sys.argv was modified correctly
            self.assertEqual(sys.argv, [mock_file.name] + list(args))

            # Assert that the CLI function was called
            mock_module.cli.assert_called_once()

            # Assert that the temporary file was added to TEMP_FILES
            self.assertIn(mock_file, TEMP_FILES)

            # Assert that delete_temp_files was called
            mock_delete_temp_files.assert_called_once()

        finally:
            # Restore the original sys.argv and TEMP_FILES
            sys.argv = original_argv
            TEMP_FILES[:] = original_temp_files

        # Assert that sys.argv was restored
        self.assertEqual(sys.argv, original_argv)

        # Assert that TEMP_FILES was restored
        self.assertEqual(TEMP_FILES, original_temp_files)