import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cache_to_data import run_conversion


class TestCacheToDataPipeline(unittest.TestCase):
    def test_mock_cache_conversion_and_weaver_output(self):
        mock_cache_dir = Path(os.getenv("TEST_MOCK_CACHE_DIR", "./tests_artifacts/cache_mocks"))
        data_output_dir = Path(os.getenv("TEST_DATA_OUTPUT_DIR", "./tests_artifacts/data"))
        config_path = Path(os.getenv("TEST_CONFIG_PATH", "./config.yml"))

        self.assertTrue(mock_cache_dir.exists(), f"Dossier mocks introuvable: {mock_cache_dir}")
        self.assertTrue(any(mock_cache_dir.glob("taiga_*.json")), "Aucun mock taiga_*.json généré")

        output_files = run_conversion(str(mock_cache_dir), str(data_output_dir), str(config_path))
        self.assertGreater(len(output_files), 0, "Aucun fichier converti")

        non_empty_output = []
        for output_file in output_files:
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, list, f"Le fichier converti doit être une liste: {output_file}")
            if payload:
                non_empty_output.append((output_file, payload))

        self.assertGreater(len(non_empty_output), 0, "Toutes les sorties converties sont vides")

        # Vérifie qu'au moins une conversion contient la structure attendue de data_weaver3.
        _, first_payload = non_empty_output[0]
        first_entry = first_payload[0]
        self.assertIn("inetOrgPerson", first_entry)
        self.assertIn("additionalFields", first_entry)
        self.assertIn("$setOnInsert", first_entry)


if __name__ == "__main__":
    unittest.main()
