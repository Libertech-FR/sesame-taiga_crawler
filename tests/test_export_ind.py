import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.export_ind import export_ind


class TestExportInd(unittest.IsolatedAsyncioTestCase):
    async def test_export_ind_logs_warning_and_skips_when_output_is_empty_for_pri(self):
        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = {"result": {"output": []}}

        col = {"params": {"type": "pri", "au": "", "id": "*"}, "method": "ExportInd"}
        headers = {"Authorization": "Bearer token"}

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("src.export_ind.requests.post", return_value=response):
                    with patch("src.export_ind.logger.warning") as mock_warning:
                        await export_ind("https://example.test", col, headers)

                        mock_warning.assert_called_once()
                        args = mock_warning.call_args.args
                        self.assertIn("Empty response from ExportInd", args[0])
                        self.assertEqual(args[1], "pri")
                        # Pour type=pri, export_ind ajoute +1 à l'année
                        # self.assertEqual(args[2], 2027)

                output_file = Path(tmpdir) / "cache" / "taiga_pri.json"
                self.assertFalse(output_file.exists())
            finally:
                os.chdir(previous_cwd)

    async def test_export_ind_logs_warning_on_http_error(self):
        error = requests.exceptions.HTTPError("boom")
        error.response = Mock(text="server error")

        failing_response = Mock()
        failing_response.text = "server error"
        failing_response.raise_for_status.side_effect = error

        col = {"params": {"type": "pri", "au": "2026", "id": "*"}, "method": "ExportInd"}

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("src.export_ind.requests.post", return_value=failing_response):
                    # On vérifie juste que la warning est bien loggée,
                    # et que l'exception HTTPError ne remonte pas (comportement actuel).
                    with patch("src.export_ind.logger.warning") as mock_warning:
                        await export_ind("https://example.test", col, {})
                        mock_warning.assert_called_once()
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()

