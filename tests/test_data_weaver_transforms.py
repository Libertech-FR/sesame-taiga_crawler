import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.data_weaver3.transforms import parse_args, parse_function_call, parse_transform


class TestDataWeaverTransforms(unittest.TestCase):
    def test_parse_args_supports_quotes_and_numbers(self):
        args = "delimiter='.' start=1 end=3"
        parsed = parse_args(args)
        self.assertEqual(parsed["delimiter"], ".")
        self.assertEqual(parsed["start"], 1)
        self.assertEqual(parsed["end"], 3)

    def test_parse_function_call_extracts_name_and_kwargs(self):
        name, kwargs = parse_function_call("suffix(string='@lyon.archi.fr')")
        self.assertEqual(name, "suffix")
        self.assertEqual(kwargs["string"], "@lyon.archi.fr")

    def test_parse_transform_chainable_examples(self):
        value = ["Jean", "Dupont"]
        joined = parse_transform("join(delimiter='.')", value)
        lowered = parse_transform("lower", joined)
        suffixed = parse_transform("suffix(string='@lyon.archi.fr')", lowered)
        self.assertEqual(suffixed, "jean.dupont@lyon.archi.fr")

    def test_parse_transform_parse_type_str(self):
        value = 12345
        parsed = parse_transform("parse_type(typename='str')", value)
        self.assertEqual(parsed, "12345")


if __name__ == "__main__":
    unittest.main()
