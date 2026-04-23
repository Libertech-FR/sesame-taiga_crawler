import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "tests_integration" / "cache"
DATA_DIR = ROOT / "tests_integration" / "data"
FIXTURE_FILES = ("taiga_adm.json", "taiga_esn.json", "taiga_etd.json", "taiga_pri.json")


class TestIntegrationFixtures(unittest.TestCase):
    def test_hardcoded_fixtures_are_present_and_identical(self):
        self.assertTrue(CACHE_DIR.exists(), f"Dossier cache introuvable: {CACHE_DIR}")
        self.assertTrue(DATA_DIR.exists(), f"Dossier data introuvable: {DATA_DIR}")

        for filename in FIXTURE_FILES:
            cache_file = CACHE_DIR / filename
            data_file = DATA_DIR / filename

            self.assertTrue(cache_file.exists(), f"Fichier manquant dans cache: {cache_file}")
            self.assertTrue(data_file.exists(), f"Fichier manquant dans data: {data_file}")

            cache_payload = json.loads(cache_file.read_text(encoding="utf-8"))
            data_payload = json.loads(data_file.read_text(encoding="utf-8"))
            self.assertEqual(cache_payload, data_payload, f"Différence entre cache et data pour {filename}")

            self.assertIsInstance(cache_payload, dict, f"Le fixture {filename} doit être un objet JSON")
            self.assertIn("data", cache_payload, f"Le fixture {filename} doit contenir une clé 'data'")
            self.assertIsInstance(cache_payload["data"], list, f"Le champ data doit être une liste dans {filename}")
            self.assertGreater(len(cache_payload["data"]), 0, f"Le fixture {filename} ne doit pas être vide")


if __name__ == "__main__":
    unittest.main()
