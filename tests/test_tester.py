import unittest

from click.testing import Result
from cliffy.manifest import CLIManifest
from cliffy.tester import ShellScript, TestCase, Tester
from unittest.mock import MagicMock, patch

class TestTester(unittest.TestCase):
    @patch('cliffy.tester.open', new_callable=MagicMock)
    @patch('cliffy.tester.Transformer')
    @patch('cliffy.tester.import_module_from_path')
    @patch('cliffy.tester.CliRunner')
    @patch('cliffy.tester.Parser')
    @patch('cliffy.tester.NamedTemporaryFile')
    def setUp(self, mock_ntf, mock_parser, mock_cli_runner, mock_import, mock_transformer, mock_open):
        self.mock_manifest = MagicMock(spec=CLIManifest)
        self.mock_manifest.tests = [
            "> echo 'Test shell script'",
            {"test command": "assert result.exit_code == 0"}
        ]
        self.mock_transformer = mock_transformer.return_value
        self.mock_transformer.manifest = self.mock_manifest
        self.mock_transformer.cli.name = "test_cli"
        self.mock_transformer.cli.code = "mock_code"

        self.mock_module = MagicMock()
        mock_import.return_value = self.mock_module

        self.mock_runner = mock_cli_runner.return_value
        self.mock_parser = mock_parser.return_value

        self.tester = Tester('dummy_manifest.yaml')

    def test_init(self):
        """
        Test the initialization of the Tester class.
        This test checks if the Tester is correctly initialized with mocked dependencies
        and if the test pipeline is properly set up.
        """
        self.assertIsInstance(self.tester, Tester)
        self.assertEqual(self.tester.T, self.mock_transformer)
        self.assertEqual(self.tester.module, self.mock_module)
        self.assertEqual(self.tester.runner, self.mock_runner)
        self.assertEqual(self.tester.parser, self.mock_parser)
        self.assertEqual(len(self.tester.test_pipeline), 2)
        self.assertIsInstance(self.tester.test_pipeline[0], ShellScript)
        self.assertIsInstance(self.tester.test_pipeline[1], TestCase)
        self.assertEqual(self.tester.total_cases, 1)

    def test_is_valid_command(self):
        """
        Test the is_valid_command method of the Tester class.
        This test checks if the method correctly identifies valid and invalid commands.
        """
        self.tester.module_funcs = [
            ('command_func', MagicMock()),
            ('another_func', MagicMock())
        ]

        self.tester.parser.get_command_func_name = MagicMock(return_value='command_func')
        self.assertTrue(self.tester.is_valid_command('valid_command'))

        self.tester.parser.get_command_func_name = MagicMock(return_value='non_existent_func')
        self.assertFalse(self.tester.is_valid_command('invalid_command'))

    def test_invoke_test(self):
        """
        Test the invoke_test method of the Tester class.
        This test checks if the method correctly invokes a command and executes the assert script.
        """
        mock_result = MagicMock(spec=Result)
        mock_result.output = "Test output"
        mock_result.exit_code = 0
        self.tester.runner.invoke = MagicMock(return_value=mock_result)

        test_command = "test_command"
        test_script = "assert result.exit_code == 0\nassert 'Test output' in result_text"

        generator = self.tester.invoke_test(test_command, test_script)
        result = next(generator)

        self.assertEqual(result, mock_result)
        self.tester.runner.invoke.assert_called_once_with(self.tester.module.cli, test_command)

        # Test that no exception is raised when executing the assert script
        try:
            next(generator)
        except StopIteration:
            pass
        except Exception as e:
            self.fail(f"Executing assert script raised an unexpected exception: {e}")

    def test_invoke_shell(self):
        """
        Test the invoke_shell method of the Tester class.
        This test checks if the method correctly handles shell script execution.
        """
        with patch('cliffy.tester.transformer.transform') as mock_transform, \
             patch('builtins.exec') as mock_exec:
            mock_transform.return_value = "transformed_code"
            shell_script = ShellScript(command="> echo 'Test'")
            self.tester.invoke_shell(shell_script)
            mock_transform.assert_called_once_with("> echo 'Test'")
            mock_exec.assert_called_once_with("import subprocess\ntransformed_code")