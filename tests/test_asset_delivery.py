import json
import tempfile
import unittest
from pathlib import Path


class FakeChannel:
    channel_name = "kf"

    def __init__(self):
        self.sent = []

    async def send_image(self, user_id, media_id):
        self.sent.append((user_id, media_id))
        return {"errcode": 0, "errmsg": "ok"}


class AssetDeliveryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        images_dir = self.root / "images" / "广东-深圳"
        images_dir.mkdir(parents=True)
        (images_dir / "华为.png").write_bytes(b"image-v1")
        self.index_path = self.root / "asset_index.json"
        self.cache_path = self.root / "delivery_cache.json"

        from app.assets.index import build_image_asset_index, save_asset_index

        save_asset_index(build_image_asset_index(self.root / "images"), self.index_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    async def test_send_asset_uploads_once_and_reuses_valid_cache(self):
        from app.assets.delivery import AssetDeliveryService

        uploads = []

        async def upload(channel_name, file_path, media_type):
            uploads.append((channel_name, Path(file_path).name, media_type))
            return {"media_id": f"{channel_name}-media-{len(uploads)}", "expires_in": 7200}

        channel = FakeChannel()
        service = AssetDeliveryService(
            asset_root=self.root,
            index_path=self.index_path,
            cache_path=self.cache_path,
            upload_media=upload,
        )

        first = await service.send_asset(channel, "user-1", "visit_image:广东-深圳:华为")
        second = await service.send_asset(channel, "user-1", "visit_image:广东-深圳:华为")

        self.assertEqual({"errcode": 0, "errmsg": "ok"}, first)
        self.assertEqual({"errcode": 0, "errmsg": "ok"}, second)
        self.assertEqual([("kf", "华为.png", "image")], uploads)
        self.assertEqual([("user-1", "kf-media-1"), ("user-1", "kf-media-1")], channel.sent)

        cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual("kf-media-1", cache[0]["media_id"])


if __name__ == "__main__":
    unittest.main()
