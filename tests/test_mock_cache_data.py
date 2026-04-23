import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mock_cache_data import generate_mock_from_cache_payload, generate_mocks_from_cache_dir


class TestMockCacheData(unittest.TestCase):
    def test_generate_mock_keeps_structure_and_size(self):
        payload = {
            "type": "lyon / administratifs",
            "data": [
                {"id_adm": 174, "nom": "Agent", "photo_nom": "adm-174.jpg", "nss_date": "07/02/2003"},
                {"id_adm": 200, "nom": "Agent", "photo_nom": "adm-200.jpg", "nss_date": "17/09/2001"},
            ],
            "total": 2,
        }

        mock = generate_mock_from_cache_payload(payload, size=5, seed=123)

        self.assertEqual(mock["type"], payload["type"])
        self.assertEqual(mock["total"], 5)
        self.assertEqual(len(mock["data"]), 5)
        for row in mock["data"]:
            self.assertEqual(set(row.keys()), {"id_adm", "nom", "photo_nom", "nss_date"})
            self.assertIsInstance(row["id_adm"], int)
            self.assertRegex(row["photo_nom"], r"adm-\d+\.jpg")
            self.assertRegex(row["nss_date"], r"\d{2}/\d{2}/\d{4}")

    def test_generate_mocks_from_cache_dir_writes_files(self):
        base = Path(self.id().replace(".", "_"))
        tmp_path = Path(".tmp_tests") / base
        cache_dir = tmp_path / "cache"
        out_dir = tmp_path / "mocks"
        cache_dir.mkdir(parents=True, exist_ok=True)

        source_payload = {
            "type": "lyon / primo-inscrits",
            "data": [{"id_etd": 1, "email1": "test@example.com"}],
            "total": 1,
        }
        with (cache_dir / "taiga_pri.json").open("w", encoding="utf-8") as fh:
            json.dump(source_payload, fh)

        generated = generate_mocks_from_cache_dir(cache_dir, out_dir, size=3, seed=10)

        self.assertEqual(len(generated), 1)
        output_file = generated[0]
        self.assertTrue(output_file.exists())
        output_payload = json.loads(output_file.read_text(encoding="utf-8"))
        self.assertEqual(output_payload["total"], 3)
        self.assertEqual(len(output_payload["data"]), 3)

        # Nettoyage minimal du dossier temporaire.
        for generated_file in out_dir.glob("*.json"):
            generated_file.unlink()
        for source_file in cache_dir.glob("*.json"):
            source_file.unlink()
        out_dir.rmdir()
        cache_dir.rmdir()
        tmp_path.rmdir()


if __name__ == "__main__":
    unittest.main()
