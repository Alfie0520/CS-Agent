import json
import tempfile
import unittest
from pathlib import Path


class AssetIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.images_root = self.root / "images"
        self.index_path = self.root / "asset_index.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_scans_images_into_stable_asset_index(self):
        from app.assets.index import build_image_asset_index, save_asset_index

        image_path = self.images_root / "广东-深圳" / "华为.png"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"image-v1")

        assets = build_image_asset_index(self.images_root)
        save_asset_index(assets, self.index_path)

        self.assertEqual(1, len(assets))
        asset = assets[0]
        self.assertEqual("visit_image:广东-深圳:华为", asset["asset_id"])
        self.assertEqual("广东-深圳", asset["category"])
        self.assertEqual("华为", asset["name"])
        self.assertEqual("images/广东-深圳/华为.png", asset["path"])
        self.assertEqual("image", asset["kind"])
        self.assertTrue(asset["sha256"])

        saved = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.assertEqual(assets, saved)

    def test_replacing_file_changes_sha_without_changing_asset_id(self):
        from app.assets.index import build_image_asset_index

        image_path = self.images_root / "广东-深圳" / "华为.png"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"image-v1")
        first = build_image_asset_index(self.images_root)[0]

        image_path.write_bytes(b"image-v2")
        second = build_image_asset_index(self.images_root)[0]

        self.assertEqual(first["asset_id"], second["asset_id"])
        self.assertNotEqual(first["sha256"], second["sha256"])


if __name__ == "__main__":
    unittest.main()
