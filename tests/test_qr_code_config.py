import os
import unittest


class QrCodeConfigTest(unittest.TestCase):
    def setUp(self):
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"
        os.environ["WECHAT_QR_CODE_ASSET_ID"] = "visit_image:__system:老板微信二维码"
        from app.config import get_settings

        get_settings.cache_clear()

    def tearDown(self):
        from app.config import get_settings

        get_settings.cache_clear()
        for key in (
            "WECHAT_APP_ID",
            "WECHAT_APP_SECRET",
            "WECHAT_TOKEN",
            "WECHAT_QR_CODE_ASSET_ID",
        ):
            os.environ.pop(key, None)

    def test_wechat_qr_code_asset_id_can_be_configured(self):
        from app.config import get_settings

        settings = get_settings()

        self.assertEqual("visit_image:__system:老板微信二维码", settings.wechat_qr_code_asset_id)


if __name__ == "__main__":
    unittest.main()
