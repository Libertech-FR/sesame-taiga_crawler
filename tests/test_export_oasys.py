import json
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

from src.export_oasys import export_oasys


class TestExportOasys(unittest.IsolatedAsyncioTestCase):
    async def test_export_oasys_writes_cache_file_for_etd(self):
        payload = {
            "data": [{"id": "x1"}, {"id": "x2"}],
            "meta": {"pagination": {"count": 2}},
        }

        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = payload

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}
        headers = {"Authorization": "Bearer token"}

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("src.export_oasys.requests.get", return_value=response) as mock_get:
                    await export_oasys("https://example.test", col, headers)
            finally:
                os.chdir(previous_cwd)

            expected_url = "https://example.test/export?year=2026&offset=0&limit=10000"
            mock_get.assert_called_once_with(expected_url, headers=headers, verify=False, timeout=10000)

            output_file = Path(tmpdir) / "cache" / "oasys_etd.json"
            self.assertTrue(output_file.exists())
            written_data = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(written_data["type"], "etd")
            self.assertEqual(written_data["data"], payload["data"])
            self.assertEqual(written_data["total"], 2)

    async def test_export_oasys_raises_when_response_is_ko(self):
        response = Mock()
        response.text = "ko!"
        response.raise_for_status.return_value = None
        response.json.return_value = {"data": [{"id": "x1"}], "meta": {"pagination": {"count": 1}}}

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}

        with patch("src.export_oasys.requests.get", return_value=response):
            with self.assertRaises(Exception):
                await export_oasys("https://example.test", col, {})

    async def test_export_oasys_raises_when_data_is_empty(self):
        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = {"data": [], "meta": {"pagination": {"count": 0}}}

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}

        with patch("src.export_oasys.requests.get", return_value=response):
            with self.assertRaises(Exception):
                await export_oasys("https://example.test", col, {})

    async def test_export_oasys_logs_warning_on_http_error(self):
        response = Mock()
        response.text = "server error"
        error = requests.exceptions.HTTPError("boom")
        error.response = response

        failing_response = Mock()
        failing_response.raise_for_status.side_effect = error

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}

        with patch("src.export_oasys.requests.get", return_value=failing_response):
            with patch("src.export_oasys.logger.warning") as mock_warning:
                await export_oasys("https://example.test", col, {})
                mock_warning.assert_called_once()

    async def test_export_oasys_raises_when_payload_has_no_data_key(self):
        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = {"meta": {"pagination": {"count": 1}}}

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}

        with patch("src.export_oasys.requests.get", return_value=response):
            with self.assertRaises(KeyError):
                await export_oasys("https://example.test", col, {})

    async def test_export_oasys_raises_when_payload_has_no_count(self):
        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = {"data": [{"id": "x1"}], "meta": {"pagination": {}}}

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}

        with patch("src.export_oasys.requests.get", return_value=response):
            with self.assertRaises(KeyError):
                await export_oasys("https://example.test", col, {})

    async def test_export_oasys_raises_when_cache_write_fails(self):
        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = {"data": [{"id": "x1"}], "meta": {"pagination": {"count": 1}}}

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}

        with patch("src.export_oasys.requests.get", return_value=response):
            with patch("builtins.open", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    await export_oasys("https://example.test", col, {})

    async def test_export_oasys_overwrites_existing_cache_file(self):
        payload = {
            "data": [{"id": "new-1"}],
            "meta": {"pagination": {"count": 1}},
        }
        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = payload

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}
        headers = {"Authorization": "Bearer token"}

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                cache_dir = Path(tmpdir) / "cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                output_file = cache_dir / "oasys_etd.json"
                output_file.write_text('{"type": "etd", "data": [{"id": "old"}], "total": 99}', encoding="utf-8")

                with patch("src.export_oasys.requests.get", return_value=response):
                    await export_oasys("https://example.test", col, headers)
            finally:
                os.chdir(previous_cwd)

            written_data = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(written_data["data"], payload["data"])
            self.assertEqual(written_data["total"], 1)

    async def test_export_oasys_calls_empty_url_for_non_etd_type(self):
        payload = {
            "data": [{"id": "x1"}],
            "meta": {"pagination": {"count": 1}},
        }
        response = Mock()
        response.text = "ok"
        response.raise_for_status.return_value = None
        response.json.return_value = payload

        col = {"params": {"type": "adm", "method": "export", "au": "2026"}, "method": "export"}
        headers = {"Authorization": "Bearer token"}

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("src.export_oasys.requests.get", return_value=response) as mock_get:
                    await export_oasys("https://example.test", col, headers)
            finally:
                os.chdir(previous_cwd)

            mock_get.assert_called_once_with("", headers=headers, verify=False, timeout=10000)
            output_file = Path(tmpdir) / "cache" / "oasys_adm.json"
            self.assertTrue(output_file.exists())

    async def test_export_oasys_http_error_without_response_logs_warning(self):
        error = requests.exceptions.HTTPError("boom")
        error.response = None

        failing_response = Mock()
        failing_response.raise_for_status.side_effect = error

        col = {"params": {"type": "etd", "method": "export", "au": "2026"}, "method": "export"}

        with patch("src.export_oasys.requests.get", return_value=failing_response):
            with patch("src.export_oasys.logger.warning") as mock_warning:
                await export_oasys("https://example.test", col, {})
                mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
