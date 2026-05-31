import os
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


class AssetRouterTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-app-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"
        os.environ["VISIT_IMAGE_API_KEY"] = "secret"
        os.environ["ASSET_ROOT_PATH"] = str(self.root / "assets")
        os.environ["ASSET_INDEX_PATH"] = str(self.root / "assets" / "asset_index.json")

        from app.config import get_settings

        get_settings.cache_clear()
        from app.assets.router import router

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
            "ASSET_ROOT_PATH",
            "ASSET_INDEX_PATH",
        ]:
            os.environ.pop(key, None)
        self.tmpdir.cleanup()

    def test_upload_rejects_non_image_suffix(self):
        response = self.client.post(
            "/api/assets/image",
            data={"api_key": "secret", "category": "16陕西", "image_name": "bad.txt"},
            files={"image_file": ("bad.txt", b"not image", "text/plain")},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(False, response.json()["success"])
        self.assertIn("Unsupported image suffix", response.json()["error"])

    def test_detail_and_stats_after_upload(self):
        upload = self.client.post(
            "/api/assets/image",
            data={"api_key": "secret", "category": "16陕西", "image_name": "西安比亚迪.png"},
            files={"image_file": ("西安比亚迪.png", b"image", "image/png")},
        )
        asset_id = upload.json()["asset"]["asset_id"]

        detail = self.client.get(f"/api/assets/{asset_id}", params={"api_key": "secret"})
        stats = self.client.get("/api/assets/stats", params={"api_key": "secret"})

        self.assertEqual(True, detail.json()["success"])
        self.assertEqual("西安比亚迪", detail.json()["asset"]["name"])
        self.assertEqual(1, stats.json()["count"])
        self.assertEqual({"16陕西": 1}, stats.json()["categories"])


if __name__ == "__main__":
    unittest.main()
