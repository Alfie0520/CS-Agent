import os
import tempfile
import unittest
from pathlib import Path


class _FakeResult:
    def __init__(self, output: str) -> None:
        self.output = output

    def all_messages(self):
        return []


class _FakePydanticAgent:
    """替身 pydantic-ai Agent，只记录被喂进来的 prompt。"""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def run(self, prompt, message_history=None, deps=None):
        self.prompts.append(prompt)
        return _FakeResult("好的，收到")


class _FakeChannel:
    channel_name = "kf"

    def __init__(self, download_ok: bool = True) -> None:
        self.sent: list[str] = []
        self.downloaded: list[str] = []
        self._download_ok = download_ok

    async def send_text(self, user_id: str, content: str):
        self.sent.append(content)
        return {"errcode": 0}

    async def download_media(self, media_id: str, dest_path):
        self.downloaded.append(media_id)
        if not self._download_ok:
            return {"errcode": 40007, "errmsg": "invalid media_id"}
        Path(dest_path).write_bytes(b"fake-amr")
        return {"errcode": 0, "path": str(dest_path)}


class VoiceMessageTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-app-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"
        os.environ["SESSION_DB_PATH"] = str(Path(self._tmp.name) / "sessions.db")

        from app.config import get_settings

        get_settings.cache_clear()

    def tearDown(self):
        from app.config import get_settings

        get_settings.cache_clear()
        for key in (
            "WECHAT_APP_ID",
            "WECHAT_APP_SECRET",
            "WECHAT_TOKEN",
            "SESSION_DB_PATH",
        ):
            os.environ.pop(key, None)
        self._tmp.cleanup()

    def _build_agent(self, channel):
        from app.agent.llm_agent import LLMAgent

        agent = LLMAgent(channel=channel)
        fake = _FakePydanticAgent()
        agent._agent = fake
        return agent, fake

    # ---------- 解析层 ----------

    def test_official_account_voice_xml_parses_recognition(self):
        from app.core.xml_parser import parse_xml
        from app.models.message import MsgType

        xml = (
            "<xml>"
            "<ToUserName><![CDATA[toUser]]></ToUserName>"
            "<FromUserName><![CDATA[fromUser]]></FromUserName>"
            "<CreateTime>1357290913</CreateTime>"
            "<MsgType><![CDATA[voice]]></MsgType>"
            "<MediaId><![CDATA[media_id]]></MediaId>"
            "<Format><![CDATA[amr]]></Format>"
            "<Recognition><![CDATA[我想去深圳看华为]]></Recognition>"
            "<MsgId>1234567890123456</MsgId>"
            "</xml>"
        ).encode()

        msg = parse_xml(xml)

        self.assertEqual(MsgType.VOICE, msg.msg_type)
        self.assertEqual("media_id", msg.media_id)
        self.assertEqual("amr", msg.format)
        self.assertEqual("我想去深圳看华为", msg.recognition)

    def test_kf_voice_message_parses_media_id(self):
        from app.handler.kf_router import _parse_kf_message
        from app.models.message import MsgType

        msg = _parse_kf_message(
            {
                "origin": 3,
                "msgtype": "voice",
                "external_userid": "wm-user",
                "open_kfid": "wk-kfid",
                "send_time": 1700000000,
                "msgid": "msg-1",
                "voice": {"media_id": "kf-media-id"},
            }
        )

        self.assertIsNotNone(msg)
        self.assertEqual(MsgType.VOICE, msg.msg_type)
        self.assertEqual("kf-media-id", msg.media_id)
        self.assertEqual("amr", msg.format)

    def test_kf_voice_message_without_media_id_is_ignored(self):
        from app.handler.kf_router import _parse_kf_message

        msg = _parse_kf_message(
            {
                "origin": 3,
                "msgtype": "voice",
                "external_userid": "wm-user",
                "voice": {},
            }
        )

        self.assertIsNone(msg)

    # ---------- Agent 层 ----------

    async def test_recognition_is_used_without_download(self):
        from app.models.message import IncomingMessage, MsgType

        channel = _FakeChannel()
        agent, fake = self._build_agent(channel)

        response = await agent.handle(
            IncomingMessage(
                to_user="toUser",
                from_user="fromUser",
                create_time=0,
                msg_type=MsgType.VOICE,
                media_id="media_id",
                format="amr",
                recognition="我想去深圳看华为",
                channel="official_account",
            )
        )

        self.assertEqual(["我想去深圳看华为"], fake.prompts)
        self.assertEqual([], channel.downloaded)
        self.assertEqual([], channel.sent)
        self.assertEqual(1, len(response.replies))

    async def test_fallback_downloads_and_transcribes(self):
        from app.agent import llm_agent
        from app.models.message import IncomingMessage, MsgType

        channel = _FakeChannel()
        agent, fake = self._build_agent(channel)

        convert_calls: list[tuple[str, str]] = []
        asr_calls: list[str] = []

        async def fake_convert(src, dst):
            convert_calls.append((str(src), str(dst)))
            Path(dst).write_bytes(b"fake-mp3")
            return True

        async def fake_transcribe(path):
            asr_calls.append(str(path))
            return "帮我看下河南的胖东来"

        original_convert = llm_agent.to_mp3_16k_mono
        original_transcribe = llm_agent.asr_client.transcribe
        llm_agent.to_mp3_16k_mono = fake_convert
        llm_agent.asr_client.transcribe = fake_transcribe
        try:
            response = await agent.handle(
                IncomingMessage(
                    to_user="toUser",
                    from_user="fromUser",
                    create_time=0,
                    msg_type=MsgType.VOICE,
                    media_id="kf-media-id",
                    format="amr",
                    channel="kf",
                )
            )
        finally:
            llm_agent.to_mp3_16k_mono = original_convert
            llm_agent.asr_client.transcribe = original_transcribe

        self.assertEqual(["kf-media-id"], channel.downloaded)
        self.assertEqual(1, len(convert_calls))
        self.assertEqual(1, len(asr_calls))
        # 安抚消息必须在识别之前发出
        self.assertEqual([llm_agent._VOICE_ACK], channel.sent)
        self.assertEqual(["帮我看下河南的胖东来"], fake.prompts)
        self.assertEqual(1, len(response.replies))

    async def test_transcribe_failure_returns_hint(self):
        from app.agent import llm_agent
        from app.models.message import IncomingMessage, MsgType

        channel = _FakeChannel()
        agent, fake = self._build_agent(channel)

        async def fake_convert(src, dst):
            Path(dst).write_bytes(b"fake-mp3")
            return True

        async def fake_transcribe(path):
            return None

        original_convert = llm_agent.to_mp3_16k_mono
        original_transcribe = llm_agent.asr_client.transcribe
        llm_agent.to_mp3_16k_mono = fake_convert
        llm_agent.asr_client.transcribe = fake_transcribe
        try:
            response = await agent.handle(
                IncomingMessage(
                    to_user="toUser",
                    from_user="fromUser",
                    create_time=0,
                    msg_type=MsgType.VOICE,
                    media_id="kf-media-id",
                    format="amr",
                    channel="kf",
                )
            )
        finally:
            llm_agent.to_mp3_16k_mono = original_convert
            llm_agent.asr_client.transcribe = original_transcribe

        self.assertEqual([], fake.prompts)
        self.assertEqual(1, len(response.replies))
        self.assertEqual(llm_agent._VOICE_UNRECOGNIZED_REPLY, response.replies[0].text)

    async def test_download_failure_skips_asr(self):
        from app.agent import llm_agent
        from app.models.message import IncomingMessage, MsgType

        channel = _FakeChannel(download_ok=False)
        agent, fake = self._build_agent(channel)

        asr_calls: list[str] = []

        async def fake_transcribe(path):
            asr_calls.append(str(path))
            return "不该被调用"

        original_transcribe = llm_agent.asr_client.transcribe
        llm_agent.asr_client.transcribe = fake_transcribe
        try:
            response = await agent.handle(
                IncomingMessage(
                    to_user="toUser",
                    from_user="fromUser",
                    create_time=0,
                    msg_type=MsgType.VOICE,
                    media_id="bad-media-id",
                    format="amr",
                    channel="kf",
                )
            )
        finally:
            llm_agent.asr_client.transcribe = original_transcribe

        self.assertEqual([], asr_calls)
        self.assertEqual([], fake.prompts)
        self.assertEqual(llm_agent._VOICE_UNRECOGNIZED_REPLY, response.replies[0].text)


if __name__ == "__main__":
    unittest.main()
