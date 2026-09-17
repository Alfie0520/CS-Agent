import base64
import os
import tempfile
import unittest
from pathlib import Path


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("response is not json")
        return self._payload


class _FakeAsyncClient:
    """替身 httpx.AsyncClient：记录请求并返回预设响应。"""

    response = _FakeResponse()
    calls: list[dict] = []

    def __init__(self, **kwargs) -> None:
        self._kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeAsyncClient.calls.append({"url": url, "headers": headers, "json": json})
        return _FakeAsyncClient.response


class AsrClientTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["WECHAT_APP_ID"] = "test-app-id"
        os.environ["WECHAT_APP_SECRET"] = "test-app-secret"
        os.environ["WECHAT_TOKEN"] = "test-token"
        os.environ["ASR_API_KEY"] = "test-asr-key"

        from app.config import get_settings

        get_settings.cache_clear()

        self.mp3 = Path(self._tmp.name) / "voice.mp3"
        self.mp3.write_bytes(b"fake-mp3-bytes")

    def tearDown(self):
        from app.config import get_settings

        get_settings.cache_clear()
        for key in (
            "WECHAT_APP_ID",
            "WECHAT_APP_SECRET",
            "WECHAT_TOKEN",
            "ASR_API_KEY",
            "ASR_LANGUAGE",
        ):
            os.environ.pop(key, None)
        self._tmp.cleanup()

    def _patch_http(self, response: _FakeResponse) -> None:
        from app.asr import client as asr

        _FakeAsyncClient.response = response
        _FakeAsyncClient.calls = []
        original = asr.httpx.AsyncClient
        asr.httpx.AsyncClient = _FakeAsyncClient
        self.addCleanup(setattr, asr.httpx, "AsyncClient", original)

    def test_data_uri_uses_mpeg_prefix(self):
        from app.asr.client import _data_uri

        uri = _data_uri(self.mp3)

        self.assertTrue(uri.startswith("data:audio/mpeg;base64,"))
        self.assertEqual(
            base64.b64encode(b"fake-mp3-bytes").decode(), uri.split(",", 1)[1]
        )

    async def test_transcribe_parses_choices_content(self):
        from app.asr import client as asr

        self._patch_http(
            _FakeResponse(200, {"choices": [{"message": {"content": " 你好世界 "}}]})
        )

        text = await asr.transcribe(self.mp3)

        self.assertEqual("你好世界", text)
        call = _FakeAsyncClient.calls[0]
        self.assertTrue(call["url"].endswith("/compatible-mode/v1/chat/completions"))
        self.assertEqual("Bearer test-asr-key", call["headers"]["Authorization"])
        self.assertEqual("qwen3-asr-flash", call["json"]["model"])
        self.assertFalse(call["json"]["stream"])
        audio = call["json"]["messages"][0]["content"][0]
        self.assertEqual("input_audio", audio["type"])
        self.assertTrue(
            audio["input_audio"]["data"].startswith("data:audio/mpeg;base64,")
        )
        # 默认不传语言，交给模型自动判断
        self.assertNotIn("asr_options", call["json"])

    async def test_language_is_sent_when_configured(self):
        from app.asr import client as asr
        from app.config import get_settings

        os.environ["ASR_LANGUAGE"] = "zh"
        get_settings.cache_clear()
        self._patch_http(
            _FakeResponse(200, {"choices": [{"message": {"content": "好"}}]})
        )

        await asr.transcribe(self.mp3)

        self.assertEqual({"language": "zh"}, _FakeAsyncClient.calls[0]["json"]["asr_options"])

    async def test_http_error_returns_none(self):
        from app.asr import client as asr

        self._patch_http(_FakeResponse(429, text='{"error":"rate limited"}'))

        self.assertIsNone(await asr.transcribe(self.mp3))

    async def test_unexpected_body_returns_none(self):
        from app.asr import client as asr

        self._patch_http(_FakeResponse(200, {"output": {"text": "旧协议"}}))

        self.assertIsNone(await asr.transcribe(self.mp3))

    async def test_missing_api_key_skips_request(self):
        from app.asr import client as asr
        from app.config import get_settings

        os.environ["ASR_API_KEY"] = ""
        get_settings.cache_clear()
        self._patch_http(_FakeResponse(200, {"choices": [{"message": {"content": "x"}}]}))

        self.assertIsNone(await asr.transcribe(self.mp3))
        self.assertEqual([], _FakeAsyncClient.calls)

    async def test_missing_file_returns_none(self):
        from app.asr import client as asr

        self._patch_http(_FakeResponse(200, {"choices": [{"message": {"content": "x"}}]}))

        self.assertIsNone(await asr.transcribe(Path(self._tmp.name) / "nope.mp3"))
        self.assertEqual([], _FakeAsyncClient.calls)


if __name__ == "__main__":
    unittest.main()
