import io
import json
import unittest
from unittest.mock import patch

from synapse.llm import KNOWLEDGE_SYSTEM, generate_knowledge, parse_knowledge, request_parts, stream_text
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

    def test_analysis_json_mode_does_not_change_chat_or_custom_provider_requests(self):
        config = dict(CONFIG, api_base="https://open.bigmodel.cn/api/paas/v4", model="glm-5.3-flash")
        _, structured, _ = request_parts(config, [], KNOWLEDGE_SYSTEM, json_mode=True)
        self.assertEqual(structured["response_format"], {"type": "json_object"})
        self.assertEqual(structured["messages"][0]["content"], KNOWLEDGE_SYSTEM)
        self.assertNotIn("response_format", request_parts(config, [])[1])
        self.assertNotIn("response_format", request_parts(CONFIG, [], json_mode=True)[1])

    def test_wrapped_json_and_latex_preserve_formula(self):
        expected = {"summary": "公式", "knowledge": [{"title": "面积", "detail": r"$\\frac{a}{b}$ 和 \alpha"}]}
        encoded = json.dumps(expected, ensure_ascii=False)
        for text in (encoded, "\ufeff" + encoded, "以下为整理结果：\n```json\n" + encoded + "\n```\n结束。",
                     "<think>这里只是思考，{不能当作结果}</think>\n" + encoded,
                     "以下为结果\n" + encoded + "\n以上内容根据材料整理。"):
            with self.subTest(text=text[:40]):
                self.assertEqual(parse_knowledge(text), expected)

    def test_invalid_or_ambiguous_json_is_not_repaired_or_partially_accepted(self):
        valid = '{"summary":"摘要","knowledge":[]}'
        invalid = [r'{"summary":"\alpha","knowledge":[]}', '{"summary":"部分","knowledge":[',
                   '{"summary":"错误","knowledge":"[]"}', '<think>未闭合' + valid,
                   valid + "\n另一个结果\n" + valid, "```json\n" + valid + "\n```\n```json\n" + valid + "\n```"]
        for text in invalid:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_knowledge(text)

    def test_generation_retries_once_using_original_material_and_its_own_system(self):
        answer = '{"summary":"摘要","knowledge":[{"title":"概念","detail":"原文解释"}]}'
        with patch("synapse.llm.complete", side_effect=['{"summary":"truncated', answer]) as complete:
            parsed = generate_knowledge(CONFIG, "原始课件与讲稿")
        self.assertEqual(parsed["knowledge"][0]["title"], "概念")
        self.assertEqual(complete.call_count, 2)
        for call in complete.call_args_list:
            self.assertEqual(call.args[1], [{"role": "user", "content": "原始课件与讲稿"}])
            self.assertTrue(call.kwargs["json_mode"])
            self.assertTrue(call.kwargs["system"].startswith(KNOWLEDGE_SYSTEM))

    def test_generation_stops_after_two_bad_formats_and_does_not_retry_network_error(self):
        with patch("synapse.llm.complete", return_value="Markdown 回答") as complete:
            with self.assertRaisesRegex(ValueError, "连续两次"):
                generate_knowledge(CONFIG, "课件")
            self.assertEqual(complete.call_count, 2)
        with patch("synapse.llm.complete", side_effect=ValueError("远端服务 HTTP 400")) as complete:
            with self.assertRaisesRegex(ValueError, "HTTP 400"):
                generate_knowledge(CONFIG, "课件")
            self.assertEqual(complete.call_count, 1)


if __name__ == "__main__":
    unittest.main()
