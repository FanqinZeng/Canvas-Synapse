import io
import json
import unittest
from unittest.mock import patch

from synapse.llm import request_parts, stream_text
from synapse.server import split_material


CONFIG = {"api_base": "https://example.com/v1", "model": "test-model", "api_key": "test-secret", "protocol": "chat"}


class LLMTests(unittest.TestCase):
    def test_chat_ignores_reasoning_and_usage_chunks(self):
        events = [
            {"choices": [{"delta": {"reasoning_content": "private reasoning"}}]},
            {"choices": [{"delta": {"content": "课程"}}]},
            {"choices": [], "usage": {"total_tokens": 8}},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ]
        payload = b"".join(("data: " + json.dumps(e) + "\n\n").encode() for e in events) + b"data: [DONE]\n\n"
        with patch("synapse.llm.open_request", return_value=io.BytesIO(payload)):
            self.assertEqual("".join(stream_text(CONFIG, [{"role": "user", "content": "hello"}])), "课程")

    def test_truncated_answer_is_not_success(self):
        data = b'data: {"choices":[{"delta":{"content":"half"},"finish_reason":"length"}]}\n\n'
        with patch("synapse.llm.open_request", return_value=io.BytesIO(data)):
            with self.assertRaisesRegex(ValueError, "未完整"):
                list(stream_text(CONFIG, []))

    def test_responses_multimodal_format_and_no_remote_storage(self):
        config = dict(CONFIG, protocol="responses")
        url, payload, headers = request_parts(config, [{"role": "user", "content": [
            {"type": "text", "text": "explain"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,QQ=="}}
        ]}])
        self.assertTrue(url.endswith("/v1/responses"))
        self.assertFalse(payload["store"])
        self.assertEqual(payload["input"][0]["content"][1]["type"], "input_image")
        self.assertEqual(headers["Authorization"], "Bearer test-secret")

    def test_responses_stream(self):
        events = [{"type": "response.output_text.delta", "delta": "文本"}, {"type": "response.completed"}]
        data = b"".join(("data: " + json.dumps(e) + "\n\n").encode() for e in events)
        with patch("synapse.llm.open_request", return_value=io.BytesIO(data)):
            self.assertEqual("".join(stream_text(dict(CONFIG, protocol="responses"), [])), "文本")

    def test_disconnect_without_done_is_failure(self):
        with patch("synapse.llm.open_request", return_value=io.BytesIO(b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n')):
            with self.assertRaisesRegex(ValueError, "完整"):
                list(stream_text(CONFIG, []))

    def test_chunking_covers_long_lines_and_late_content(self):
        text = "介绍\n" + "长" * 30000 + "\n课堂最后一道例题"
        parts = split_material(text, 1000)
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(len(p) <= 1000 for p in parts))
        self.assertIn("最后一道", parts[-1])


if __name__ == "__main__":
    unittest.main()
