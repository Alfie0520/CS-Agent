import os
import unittest


class MenuStartupConfigTests(unittest.TestCase):
    def setUp(self):
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"

        from app.config import get_settings

        get_settings.cache_clear()

    def tearDown(self):
        from app.config import get_settings

        get_settings.cache_clear()

    def test_auto_create_wechat_menu_is_disabled_by_default(self):
        from app.config import get_settings

        settings = get_settings()

        self.assertFalse(settings.wechat_menu_auto_create_on_startup)
        self.assertFalse(settings.should_auto_create_wechat_menu_on_startup)

    def test_auto_create_wechat_menu_requires_explicit_enablement(self):
        os.environ["WECHAT_MENU_AUTO_CREATE_ON_STARTUP"] = "true"

        from app.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        self.assertTrue(settings.should_auto_create_wechat_menu_on_startup)
