import os
import unittest


class KfRouterTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-app-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"
        os.environ["KF_AUTO_TRANSITION_ENABLED"] = "false"
        from app.config import get_settings

        get_settings.cache_clear()

    def tearDown(self):
        from app.config import get_settings

        get_settings.cache_clear()
        os.environ.pop("WECHAT_APP_ID", None)
        os.environ.pop("WECHAT_APP_SECRET", None)
        os.environ.pop("WECHAT_TOKEN", None)
        os.environ.pop("KF_AUTO_TRANSITION_ENABLED", None)

    async def test_transition_to_ai_skips_when_disabled(self):
        from app.handler import kf_router

        calls = []

        async def fake_kf_post(path, payload):
            calls.append((path, payload))
            return {"errcode": 0, "service_state": 0}

        original = kf_router.kf_post
        kf_router.kf_post = fake_kf_post
        try:
            await kf_router._transition_to_ai("kf-id", "user-id")
        finally:
            kf_router.kf_post = original

        self.assertEqual([], calls)


if __name__ == "__main__":
    unittest.main()
