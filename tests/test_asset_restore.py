import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


def _jpeg_bytes(color=(20, 80, 160), size=(120, 80), quality=90):
    image = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


class AssetRestoreTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_restores_legacy_media_index_images_and_generates_asset_index(self):
        from app.assets.restore import restore_assets_from_media_index

        media_index = self.root / "media_index.json"
        asset_root = self.root / "assets"
        asset_index = asset_root / "asset_index.json"
        media_index.write_text(
            json.dumps(
                [
                    {
                        "media_id": "mid-1",
                        "image_name": "华为.png",
                        "category": "广东-深圳",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        async def fake_download(media_id):
            self.assertEqual("mid-1", media_id)
            return {"content": _jpeg_bytes(), "content_type": "image/jpeg"}

        result = restore_assets_from_media_index(
            media_index_path=media_index,
            asset_root=asset_root,
            asset_index_path=asset_index,
            download_material=fake_download,
        )

        self.assertEqual(1, result["restored"])
        self.assertEqual(0, result["already_exists"])
        self.assertTrue((asset_root / "images" / "广东-深圳" / "华为.png").exists())
        assets = json.loads(asset_index.read_text(encoding="utf-8"))
        self.assertEqual("visit_image:广东-深圳:华为", assets[0]["asset_id"])

    def test_large_images_are_compressed_close_to_target_size(self):
        from app.assets.image_processing import compress_image_if_needed

        source = self.root / "large.png"
        target = self.root / "compressed.jpg"
        image = Image.effect_noise((1800, 1800), 90).convert("RGB")
        image.save(source, format="PNG")
        self.assertGreater(source.stat().st_size, 1024 * 1024)

        output = compress_image_if_needed(
            source,
            target,
            threshold_bytes=1024 * 1024,
            target_bytes=200 * 1024,
        )

        self.assertEqual(target, output)
        self.assertLessEqual(target.stat().st_size, 260 * 1024)


if __name__ == "__main__":
    unittest.main()
