import unittest

from cliffy.helper import RequirementSpec, age_datetime, parse_requirement
from datetime import datetime, timedelta

class TestHelper(unittest.TestCase):
    def test_parse_requirement(self):
        """
        Test that parse_requirement correctly parses different types of requirements.
        """
        test_cases = [
            ("package==1.0.0", RequirementSpec(name="package", operator="==", version="1.0.0")),
            ("package>=2.1", RequirementSpec(name="package", operator=">=", version="2.1")),
            ("package<3", RequirementSpec(name="package", operator="<", version="3")),
            ("package", RequirementSpec(name="package", operator=None, version=None)),
            ("package != 1.5", RequirementSpec(name="package", operator="!=", version="1.5")),
        ]

        for input_str, expected_output in test_cases:
            with self.subTest(input=input_str):
                result = parse_requirement(input_str)
                self.assertEqual(result.name, expected_output.name)
                self.assertEqual(result.operator, expected_output.operator)
                self.assertEqual(result.version, expected_output.version)

    def test_age_datetime(self):
        """
        Test that age_datetime correctly calculates the age of a datetime object.
        """
        now = datetime.now()
        test_cases = [
            (now - timedelta(days=5), "5d"),
            (now - timedelta(hours=3), "3h"),
            (now - timedelta(minutes=45), "45m"),
            (now - timedelta(seconds=30), "30s"),
        ]

        for input_date, expected_output in test_cases:
            with self.subTest(input=input_date):
                result = age_datetime(input_date)
                self.assertEqual(result, expected_output)