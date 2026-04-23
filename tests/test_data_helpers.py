import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_utils import compare_fingerprints, filter_datas


class TestDataHelpers(unittest.TestCase):
    def test_compare_fingerprints_returns_only_new_entries(self):
        current = [
            {"ident": "etd-1", "size": 100, "date": 10},
            {"ident": "etd-2", "size": 200, "date": 20},
        ]
        new = [
            {"ident": "etd-1", "size": 100, "date": 10},
            {"ident": "etd-3", "size": 300, "date": 30},
        ]

        diff = compare_fingerprints(current, new)

        self.assertEqual(diff, {("etd-3", 300, 30)})

    def test_filter_datas_removes_existing_fingerprints(self):
        current = [
            {"ident": "adm-1", "size": 100, "date": 1},
            {"ident": "adm-2", "size": 200, "date": 2},
        ]
        old = [{"ident": "adm-1", "size": 100, "date": 1}]

        filtered = filter_datas(current, old)

        self.assertEqual(filtered, [{"ident": "adm-2", "size": 200, "date": 2}])


if __name__ == "__main__":
    unittest.main()
