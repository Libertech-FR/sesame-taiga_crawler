import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.data_weaver3.main import config, weave_entries, weave_entry


class TestDataWeaverMain(unittest.TestCase):
    def setUp(self):
        config.clear()
        self.sample_config = {
            "mapping": {
                "inetOrgPerson.cn": ["prenom", "nom"],
                "$setOnInsert.inetOrgPerson.employeeNumber": ["id_coord"],
                "additionalFields.attributes.supannPerson.supannRefId": ["id_coord"],
            },
            "additionalFields": {
                "inetOrgPerson.employeeType": "TAIGA",
            },
            "transforms": {
                "inetOrgPerson.cn": "join(delimiter=' ')",
                "$setOnInsert.inetOrgPerson.employeeNumber": "parse_type(typename='str')",
                "additionalFields.attributes.supannPerson.supannRefId": [
                    "parse_type(typename='str')",
                    "prefix(string='{TAIGA}')",
                ],
            },
        }

    def test_weave_entry_maps_and_transforms_fields(self):
        source = {
            "prenom": "Alice",
            "nom": "Doe",
            "id_coord": 12345,
        }

        result = asyncio.run(weave_entry(source, self.sample_config))

        self.assertEqual(result["inetOrgPerson"]["cn"], "Alice Doe")
        self.assertEqual(result["inetOrgPerson"]["employeeType"], "TAIGA")
        self.assertEqual(result["$setOnInsert"]["inetOrgPerson"]["employeeNumber"], ["12345"])
        self.assertEqual(
            result["additionalFields"]["attributes"]["supannPerson"]["supannRefId"],
            ["{TAIGA}12345"],
        )

    def test_weave_entries_processes_multiple_rows(self):
        source = [
            {"prenom": "Alice", "nom": "Doe", "id_coord": 1},
            {"prenom": "Bob", "nom": "Smith", "id_coord": 2},
        ]

        results = asyncio.run(weave_entries(source, self.sample_config))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["inetOrgPerson"]["cn"], "Alice Doe")
        self.assertEqual(results[1]["inetOrgPerson"]["cn"], "Bob Smith")


if __name__ == "__main__":
    unittest.main()
