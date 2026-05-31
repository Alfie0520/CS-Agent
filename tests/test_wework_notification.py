import os
import tempfile
import unittest
from pathlib import Path


class WeWorkNotificationTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_text_includes_keyword_and_posts_payload(self):
        from app.notification.wework_bot import send_wework_bot_text

        calls = []

        async def post_json(url, payload):
            calls.append((url, payload))
            return {"errcode": 0, "errmsg": "ok"}

        result = await send_wework_bot_text(
            "新线索：客户要报价",
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
            keyword="CS-Agent",
            post_json=post_json,
        )

        self.assertEqual(True, result["success"])
        self.assertEqual("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test", calls[0][0])
        self.assertEqual("text", calls[0][1]["msgtype"])
        self.assertIn("CS-Agent", calls[0][1]["text"]["content"])
        self.assertIn("客户要报价", calls[0][1]["text"]["content"])

    async def test_send_text_uses_feishu_payload_for_feishu_webhook(self):
        from app.notification.wework_bot import send_wework_bot_text

        calls = []

        async def post_json(url, payload):
            calls.append((url, payload))
            return {"code": 0, "msg": "success"}

        result = await send_wework_bot_text(
            "新线索：客户要报价",
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test",
            keyword="CS-Agent",
            post_json=post_json,
        )

        self.assertEqual(True, result["success"])
        self.assertEqual("text", calls[0][1]["msg_type"])
        self.assertIn("CS-Agent", calls[0][1]["content"]["text"])
        self.assertIn("客户要报价", calls[0][1]["content"]["text"])

    async def test_notify_slash_command_sends_test_message_without_llm(self):
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-app-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"
        os.environ["MINIMAX_API_KEY"] = "test-minimax-key"
        os.environ["WEWORK_BOT_WEBHOOK_URL"] = "https://example.test/webhook"
        tmpdir = tempfile.TemporaryDirectory()
        os.environ["SESSION_DB_PATH"] = str(Path(tmpdir.name) / "sessions.db")

        from app.config import get_settings

        get_settings.cache_clear()
        from app.agent import llm_agent
        from app.agent.llm_agent import LLMAgent
        from app.models.message import IncomingMessage, MsgType

        sent = []

        async def fake_send(content, **kwargs):
            sent.append(content)
            return {"success": True, "errcode": 0, "errmsg": "ok"}

        original = llm_agent.send_wework_bot_text
        llm_agent.send_wework_bot_text = fake_send

        class FakeChannel:
            channel_name = "kf"

        try:
            agent = LLMAgent(channel=FakeChannel())
            response = await agent.handle(
                IncomingMessage(
                    to_user="service",
                    from_user="external-user",
                    create_time=0,
                    msg_type=MsgType.TEXT,
                    content="/notify hello",
                    msg_id="msg-1",
                    channel="kf",
                )
            )
        finally:
            llm_agent.send_wework_bot_text = original
            get_settings.cache_clear()
            for key in [
                "WECHAT_APP_ID",
                "WECHAT_APP_SECRET",
                "WECHAT_TOKEN",
                "MINIMAX_API_KEY",
                "WEWORK_BOT_WEBHOOK_URL",
                "SESSION_DB_PATH",
            ]:
                os.environ.pop(key, None)
            tmpdir.cleanup()

        self.assertEqual(1, len(sent))
        self.assertIn("/notify 测试消息", sent[0])
        self.assertIn("hello", sent[0])
        self.assertEqual("通知测试已发送。", response.replies[0].text)


if __name__ == "__main__":
    unittest.main()
