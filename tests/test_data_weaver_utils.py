import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.data_weaver3.utils import construct, crush


class TestDataWeaverUtils(unittest.TestCase):
    def test_crush_flatten_nested_dict_and_list(self):
        nested = {
            "user": {
                "name": "Alice",
                "roles": ["admin", "staff"],
            }
        }

        flat = crush(nested)

        self.assertEqual(flat["user.name"], "Alice")
        self.assertEqual(flat["user.roles.0"], "admin")
        self.assertEqual(flat["user.roles.1"], "staff")

    def test_construct_rebuilds_structure(self):
        flat = {
            "inetOrgPerson.cn": "Alice Doe",
            "additionalFields.attributes.supannPerson.supannRefId": "{TAIGA}123",
            "phones.0": "010203",
            "phones.1": "040506",
        }

        rebuilt = construct(flat)

        self.assertEqual(rebuilt["inetOrgPerson"]["cn"], "Alice Doe")
        self.assertEqual(
            rebuilt["additionalFields"]["attributes"]["supannPerson"]["supannRefId"],
            "{TAIGA}123",
        )
        self.assertEqual(rebuilt["phones"], ["010203", "040506"])


if __name__ == "__main__":
    unittest.main()
