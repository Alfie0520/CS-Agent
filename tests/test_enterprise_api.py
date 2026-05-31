import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


class EnterpriseApiTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_path = Path(self.tmpdir.name) / "enterprises.json"
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-app-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"
        os.environ["VISIT_IMAGE_API_KEY"] = "secret"
        os.environ["ENTERPRISE_DATA_PATH"] = str(self.data_path)

        from app.config import get_settings

        get_settings.cache_clear()
        from app.enterprise_api import router

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        from app.config import get_settings

        get_settings.cache_clear()
        for key in [
            "WECHAT_APP_ID",
            "WECHAT_APP_SECRET",
            "WECHAT_TOKEN",
            "VISIT_IMAGE_API_KEY",
            "ENTERPRISE_DATA_PATH",
        ]:
            os.environ.pop(key, None)
        self.tmpdir.cleanup()

    def _row(self):
        return {
            "id": 1,
            "city": "陕西",
            "name": "比亚迪",
            "themes": ["智能制造"],
            "visit_experience": "参观",
            "sharing_topics": "分享",
            "core_value": "价值",
            "knowledge_points": "知识点",
            "pain_points": "痛点",
        }

    def test_upload_rejects_missing_required_field(self):
        bad = self._row()
        bad.pop("name")

        response = self.client.post(
            "/api/enterprises/data",
            data={"api_key": "secret"},
            files={"json_file": ("enterprises.json", json.dumps([bad]).encode(), "application/json")},
        )

        self.assertEqual(False, response.json()["success"])
        self.assertIn("missing required field: name", response.json()["error"])
        self.assertFalse(self.data_path.exists())

    def test_dry_run_validates_without_writing_and_get_reports_source(self):
        response = self.client.post(
            "/api/enterprises/data",
            data={"api_key": "secret", "dry_run": "true"},
            files={"json_file": ("enterprises.json", json.dumps([self._row()]).encode(), "application/json")},
        )
        fetched = self.client.get("/api/enterprises/data", params={"api_key": "secret"})

        self.assertEqual(True, response.json()["success"])
        self.assertEqual(True, response.json()["dry_run"])
        self.assertFalse(self.data_path.exists())
        self.assertEqual(True, fetched.json()["success"])
        self.assertIn("source_path", fetched.json())

    def test_get_accepts_api_key_header(self):
        response = self.client.get("/api/enterprises/data", headers={"X-API-Key": "secret"})

        self.assertEqual(200, response.status_code)
        self.assertEqual(True, response.json()["success"])


if __name__ == "__main__":
    unittest.main()
