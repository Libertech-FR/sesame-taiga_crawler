import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.import_ind import _load_cache_datas


class TestLoadCacheDatas(unittest.TestCase):
    """Regression tests for _load_cache_datas.

    Locks the behaviour introduced after a production crash where an empty
    ./cache/oasys_etd.json caused json.load() to raise JSONDecodeError and
    abort the whole import run. The helper must skip broken files and let
    the remaining ones proceed.
    """

    def test_skips_empty_and_malformed_files(self):
        configs = {
            "taiga_adm.json": {"mapping": {}},
            "oasys_etd.json": {"mapping": {}},
            "taiga_esn.json": {"mapping": {}},
            "other.json": {"mapping": {}},
        }
        with TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            (cache_dir / "taiga_adm.json").write_text(
                json.dumps({"data": [{"id": 1}, {"id": 2}]}), encoding="utf-8"
            )
            (cache_dir / "oasys_etd.json").write_text("", encoding="utf-8")
            (cache_dir / "taiga_esn.json").write_text("not json at all", encoding="utf-8")
            (cache_dir / "other.json").write_text(
                json.dumps({"no_data_key": []}), encoding="utf-8"
            )
            (cache_dir / "not_in_config.json").write_text(
                json.dumps({"data": [{"id": 3}]}), encoding="utf-8"
            )

            with self.assertLogs("src.import_ind", level="WARNING") as cm:
                result = _load_cache_datas(str(cache_dir), configs)

        self.assertEqual(set(result.keys()), {"taiga_adm.json"})
        self.assertEqual(result["taiga_adm.json"], [{"id": 1}, {"id": 2}])
        joined = "\n".join(cm.output)
        self.assertIn("oasys_etd.json", joined)
        self.assertIn("taiga_esn.json", joined)
        self.assertIn("other.json", joined)
        self.assertNotIn("not_in_config.json", joined)

    def test_returns_empty_dict_when_cache_dir_missing(self):
        with self.assertLogs("src.import_ind", level="WARNING"):
            result = _load_cache_datas("/does/not/exist", {"taiga_adm.json": {}})
        self.assertEqual(result, {})

    def test_returns_empty_dict_when_no_cache_file_matches_config(self):
        with TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            (cache_dir / "unrelated.json").write_text(
                json.dumps({"data": [{"id": 1}]}), encoding="utf-8"
            )
            result = _load_cache_datas(str(cache_dir), {"taiga_adm.json": {}})
        self.assertEqual(result, {})

    def test_loads_all_valid_files(self):
        configs = {"taiga_adm.json": {"mapping": {}}, "taiga_esn.json": {"mapping": {}}}
        with TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            (cache_dir / "taiga_adm.json").write_text(
                json.dumps({"data": [{"id": 1}]}), encoding="utf-8"
            )
            (cache_dir / "taiga_esn.json").write_text(
                json.dumps({"data": [{"id": 2}]}), encoding="utf-8"
            )
            result = _load_cache_datas(str(cache_dir), configs)
        self.assertEqual(set(result.keys()), {"taiga_adm.json", "taiga_esn.json"})
        self.assertEqual(result["taiga_adm.json"], [{"id": 1}])
        self.assertEqual(result["taiga_esn.json"], [{"id": 2}])


if __name__ == "__main__":
    unittest.main()
