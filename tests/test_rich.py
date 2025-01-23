import sys
import unittest

from cliffy import rich
from io import StringIO
from unittest import mock

class TestRich(unittest.TestCase):
    @mock.patch('cliffy.rich.click', new_callable=mock.MagicMock)
    @mock.patch('cliffy.rich.Console', new_callable=mock.MagicMock)
    def test_print_rich_table_without_rich(self, mock_console, mock_click):
        """
        Test the print_rich_table function when rich is not available.
        It should create a Table object, populate it with data, and print it using Console.print.
        """
        # Prepare test data
        cols = ["Name", "Age", "City"]
        rows = [["Alice", "30", "New York"], ["Bob", "25", "London"]]
        styles = ["red", "green", "blue"]

        # Call the function
        rich.print_rich_table(cols, rows, styles)

        # Check that a Table object was created
        self.assertTrue(isinstance(mock_console.return_value.print.call_args[0][0], rich.Table))

        # Get the Table object
        table = mock_console.return_value.print.call_args[0][0]

        # Check that the Table object was populated correctly
        self.assertEqual(len(table.cols), len(cols))
        self.assertEqual(len(table.rows), len(rows))
        self.assertEqual(len(table.styles), len(styles))

        for i, col in enumerate(cols):
            self.assertEqual(table.cols[i], col)
            self.assertEqual(table.styles[i], styles[i])

        for i, row in enumerate(rows):
            self.assertEqual(table.rows[i], row)

        # Check that Console().print was called with the Table object
        mock_console.return_value.print.assert_called_once_with(table)

    @mock.patch('cliffy.rich.click', new_callable=mock.MagicMock)
    @mock.patch('cliffy.rich.Console', new_callable=mock.MagicMock)
    def test_print_rich_table_without_rich(self, mock_console, mock_click):
        """
        Test the print_rich_table function when rich is not available.
        It should create a Table object, populate it with data, and print it using Console.print.
        """
        # Prepare test data
        cols = ["Name", "Age", "City"]
        rows = [["Alice", "30", "New York"], ["Bob", "25", "London"]]
        styles = ["red", "green", "blue"]

        # Call the function
        rich.print_rich_table(cols, rows, styles)

        # Check that a Table object was created
        self.assertTrue(isinstance(mock_console.return_value.print.call_args[0][0], rich.Table))

        # Get the Table object
        table = mock_console.return_value.print.call_args[0][0]

        # Check that the Table object was populated correctly
        self.assertEqual(len(table.cols), len(cols))
        self.assertEqual(len(table.rows), len(rows))
        self.assertEqual(len(table.styles), len(styles))

        for i, col in enumerate(cols):
            self.assertEqual(table.cols[i], col)
            self.assertEqual(table.styles[i], styles[i])

        for i, row in enumerate(rows):
            self.assertEqual(table.rows[i], row)

        # Check that Console().print was called with the Table object
        mock_console.return_value.print.assert_called_once_with(table)

    @mock.patch('cliffy.rich.Console', new_callable=mock.MagicMock)
    @mock.patch('cliffy.rich.Table', new_callable=mock.MagicMock)
    def test_print_rich_table_without_rich(self, mock_table, mock_console):
        """
        Test the print_rich_table function when rich is not available.
        It should create a Table object, populate it with data, and print it using Console.print.
        """
        # Prepare test data
        cols = ["Name", "Age", "City"]
        rows = [["Alice", "30", "New York"], ["Bob", "25", "London"]]
        styles = ["red", "green", "blue"]

        # Set up the mock Table
        mock_table_instance = mock_table.return_value

        # Call the function
        rich.print_rich_table(cols, rows, styles)

        # Check that Table was instantiated
        mock_table.assert_called_once()

        # Check that add_column was called for each column with the correct style
        for col, style in zip(cols, styles):
            mock_table_instance.add_column.assert_any_call(col, style=style)

        # Check that add_row was called for each row
        for row in rows:
            mock_table_instance.add_row.assert_any_call(*row)

        # Check that Console().print was called with the Table instance
        mock_console.return_value.print.assert_called_once_with(mock_table_instance)

    @mock.patch('cliffy.rich.click', new_callable=mock.MagicMock)
    @mock.patch('cliffy.rich.Console', new_callable=mock.MagicMock)
    def test_print_rich_table_without_rich(self, mock_console, mock_click):
        """
        Test the print_rich_table function when rich is not available.
        It should create a Table object, populate it with data, and print it using Console.print.
        """
        # Prepare test data
        cols = ["Name", "Age", "City"]
        rows = [["Alice", "30", "New York"], ["Bob", "25", "London"]]
        styles = ["red", "green", "blue"]

        # Call the function
        rich.print_rich_table(cols, rows, styles)

        # Check that a Table object was created
        self.assertTrue(isinstance(mock_console.return_value.print.call_args[0][0], rich.Table))

        # Get the Table object
        table = mock_console.return_value.print.call_args[0][0]

        # Check that the Table object was populated correctly
        self.assertEqual(len(table.cols), len(cols))
        self.assertEqual(len(table.rows), len(rows))
        self.assertEqual(len(table.styles), len(styles))

        for i, col in enumerate(cols):
            self.assertEqual(table.cols[i], col)
            self.assertEqual(table.styles[i], styles[i])

        for i, row in enumerate(rows):
            self.assertEqual(table.rows[i], row)

        # Check that Console().print was called with the Table object
        mock_console.return_value.print.assert_called_once_with(table)

    @mock.patch('cliffy.rich.click', new_callable=mock.MagicMock)
    @mock.patch('cliffy.rich.Console', new_callable=mock.MagicMock)
    def test_print_rich_table_without_rich(self, mock_console, mock_click):
        """
        Test the print_rich_table function when rich is not available.
        It should create a Table object, populate it with data, and print it using Console.print.
        """
        # Prepare test data
        cols = ["Name", "Age", "City"]
        rows = [["Alice", "30", "New York"], ["Bob", "25", "London"]]
        styles = ["red", "green", "blue"]

        # Call the function
        rich.print_rich_table(cols, rows, styles)

        # Check that a Table object was created
        self.assertTrue(isinstance(mock_console.return_value.print.call_args[0][0], rich.Table))

        # Get the Table object
        table = mock_console.return_value.print.call_args[0][0]

        # Check that the Table object was populated correctly
        self.assertEqual(len(table.cols), len(cols))
        self.assertEqual(len(table.rows), len(rows))
        self.assertEqual(len(table.styles), len(styles))

        for i, col in enumerate(cols):
            self.assertEqual(table.cols[i], col)
            self.assertEqual(table.styles[i], styles[i])

        for i, row in enumerate(rows):
            self.assertEqual(table.rows[i], row)

        # Check that Console().print was called with the Table object
        mock_console.return_value.print.assert_called_once_with(table)

    @mock.patch('cliffy.rich.Console', new_callable=mock.MagicMock)
    @mock.patch('cliffy.rich.Table', new_callable=mock.MagicMock)
    def test_print_rich_table(self, mock_table, mock_console):
        """
        Test the print_rich_table function.
        It should create a Table object, populate it with data, and print it using Console.print.
        """
        # Prepare test data
        cols = ["Name", "Age", "City"]
        rows = [["Alice", "30", "New York"], ["Bob", "25", "London"]]
        styles = ["red", "green", "blue"]

        # Set up the mock Table
        mock_table_instance = mock_table.return_value

        # Call the function
        rich.print_rich_table(cols, rows, styles)

        # Check that Table was instantiated
        mock_table.assert_called_once()

        # Check that add_column was called for each column with the correct style
        for col, style in zip(cols, styles):
            mock_table_instance.add_column.assert_any_call(col, style=style)

        # Check that add_row was called for each row
        for row in rows:
            mock_table_instance.add_row.assert_any_call(*row)

        # Check that Console().print was called with the Table instance
        mock_console.return_value.print.assert_called_once_with(mock_table_instance)

    @mock.patch('cliffy.rich.Console', new_callable=mock.MagicMock)
    @mock.patch('cliffy.rich.Table', new_callable=mock.MagicMock)
    def test_print_rich_table_without_rich(self, mock_table, mock_console):
        """
        Test the print_rich_table function when rich is not available.
        It should create a Table object, populate it with data, and print it using Console.print.
        """
        # Prepare test data
        cols = ["Name", "Age", "City"]
        rows = [["Alice", "30", "New York"], ["Bob", "25", "London"]]
        styles = ["red", "green", "blue"]

        # Set up the mock Table
        mock_table_instance = mock_table.return_value

        # Call the function
        rich.print_rich_table(cols, rows, styles)

        # Check that Table was instantiated
        mock_table.assert_called_once()

        # Check that add_column was called for each column with the correct style
        for col, style in zip(cols, styles):
            mock_table_instance.add_column.assert_any_call(col, style=style)

        # Check that add_row was called for each row
        for row in rows:
            mock_table_instance.add_row.assert_any_call(*row)

        # Check that Console().print was called with the Table instance
        mock_console.return_value.print.assert_called_once_with(mock_table_instance)