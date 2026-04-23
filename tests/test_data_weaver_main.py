import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.data_weaver3.main import weave_entries, weave_entry


class TestDataWeaverMain(unittest.TestCase):
    def setUp(self):
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

        result = weave_entry(source, self.sample_config)

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

        results = weave_entries(source, self.sample_config)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["inetOrgPerson"]["cn"], "Alice Doe")
        self.assertEqual(results[1]["inetOrgPerson"]["cn"], "Bob Smith")

    def test_sequential_weave_entry_isolates_configs(self):
        config_a = {
            "mapping": {"name": "prenom"},
            "additionalFields": {"source": "A"},
        }
        config_b = {
            "mapping": {"name": "prenom"},
            "additionalFields": {"source": "B"},
        }
        source = {"prenom": "Alice"}

        result_a1 = weave_entry(source, config_a)
        result_b = weave_entry(source, config_b)
        result_a2 = weave_entry(source, config_a)

        self.assertEqual(result_a1["source"], "A")
        self.assertEqual(result_b["source"], "B")
        self.assertEqual(result_a2["source"], "A")

    def test_weave_entry_rejects_config_without_mapping(self):
        with self.assertRaises(ValueError):
            weave_entry({}, {"additionalFields": {}})

    def test_weave_entry_saves_json_file(self):
        source = {"prenom": "Alice", "nom": "Doe", "id_coord": 1}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            result = weave_entry(source, self.sample_config, file_path=str(out))
            self.assertTrue(out.exists())
            with out.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            self.assertEqual(loaded, result)

    def test_weave_entries_saves_csv_file(self):
        source = [
            {"prenom": "Alice", "nom": "Doe", "id_coord": 1},
            {"prenom": "Bob", "nom": "Smith", "id_coord": 2},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.csv"
            weave_entries(source, self.sample_config, file_path=str(out))
            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(content), 3)
            header = content[0].split(",")
            self.assertIn("inetOrgPerson.cn", header)
            joined = "\n".join(content)
            self.assertIn("Alice Doe", joined)
            self.assertIn("Bob Smith", joined)


if __name__ == "__main__":
    unittest.main()
