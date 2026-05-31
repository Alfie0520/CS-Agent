import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class WeWorkNotificationTest(unittest.IsolatedAsyncioTestCase):
    def test_build_colleague_notification_is_customer_facing_brief(self):
        from app.notification.wework_bot import build_colleague_notification

        content = build_colleague_notification(
            channel="kf",
            user_id="external-user",
            reason="客户明确询问西安比亚迪参访报价，已出现预算沟通意向。",
            summary="用户说：想看西安比亚迪，两周后大概 20 人，问能不能给预算。",
            customer_profile="疑似企业培训负责人，需求阶段接近方案和报价确认。",
            recommended_action="尽快加微信确认出行时间、人数和预算口径。",
            urgency="high",
            occurred_at=datetime(2026, 6, 1, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        )

        self.assertIn("CS-Agent 高意向客户提醒", content)
        self.assertIn("发生时间：2026-06-01 10:30", content)
        self.assertIn("跟进优先级：高", content)
        self.assertIn("客户来源：微信客服", content)
        self.assertIn("案发现场：", content)
        self.assertIn("简要用户画像：", content)
        self.assertIn("建议下一步：", content)
        self.assertNotIn("用户渠道", content)

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
