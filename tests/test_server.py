import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from unittest.mock import patch

from synapse.server import create_server


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server = create_server(cls.tmp.name, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server.application.pool.shutdown(wait=True)
        cls.tmp.cleanup()

    def req(self, method, path, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        data = json.dumps(body).encode() if body is not None else None
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        connection.request(method, path, data, h)
        response = connection.getresponse()
        status, raw = response.status, response.read()
        connection.close()
        return status, raw

    def demo(self):
        status, raw = self.req("POST", "/api/demo", {})
        self.assertEqual(status, 200, raw)
        identity = json.loads(raw)["lecture_id"]
        return json.loads(self.req("GET", "/api/lectures/" + identity)[1])

    def test_empty_state_and_static(self):
        self.assertEqual(self.req("GET", "/api/health")[0], 200)
        self.assertIn(b"Canvas", self.req("GET", "/")[1])
        self.assertEqual(self.req("GET", "/../settings.json")[0], 404)

    def test_demo_edit_search_and_export_roundtrip(self):
        lecture = self.demo()
        slide = lecture["slides"][0]
        status, raw = self.req("PATCH", "/api/slides/" + slide["id"], {"notes": "独立测试笔记", "bookmarked": True})
        self.assertEqual(status, 200, raw)
        search = json.loads(self.req("GET", "/api/search?q=" + "%E7%8B%AC%E7%AB%8B%E6%B5%8B%E8%AF%95")[1])
        self.assertTrue(search["results"])
        status, export = self.req("GET", "/api/export/" + lecture["id"] + "?format=json")
        self.assertEqual(status, 200)
        self.assertEqual(self.req("POST", "/api/import", json.loads(export))[0], 200)
        self.assertIn("独立测试笔记", self.req("GET", "/api/export/" + lecture["id"])[1].decode())

    def test_cross_origin_and_dns_rebinding_blocked(self):
        self.assertEqual(self.req("POST", "/api/demo", {}, {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.req("GET", "/api/state", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.req("POST", "/api/demo", {}, {"Content-Type": "text/plain"})[0], 400)

    def test_settings_and_missing_credentials(self):
        self.req("PUT", "/api/settings", {"api_key": "fake-test-secret", "model": "fake-test-model"})
        public = self.req("GET", "/api/settings")[1]
        self.assertNotIn(b"fake-test-secret", public)
        self.assertIn(b"api_key_set", public)
        self.req("PUT", "/api/settings", {"clear_api_key": True})
        lecture = self.demo()
        self.assertEqual(self.req("POST", "/api/analyze", {"lecture_id": lecture["id"]})[0], 400)

    def test_chat_stream_uses_sources_and_only_saves_complete_response(self):
        lecture = self.demo()
        self.req("PUT", "/api/settings", {"api_key": "fake-test-secret", "model": "fake-test-model"})
        body = {"lecture_id": lecture["id"], "slide_id": lecture["slides"][0]["id"], "scope": "slide", "message": "本页的重点是什么？"}
        def fake(config, messages):
            self.assertIn("原始证据", messages[0]["content"])
            yield "重点 "
            yield "[S1]"
        with patch("synapse.llm.stream_text", side_effect=fake):
            status, raw = self.req("POST", "/api/chat", body)
        events = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual(status, 200)
        self.assertEqual(events[0]["type"], "sources")
        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(events[0]["sources"])
        before = self.server.application.store.messages(lecture["id"], "slide", body["slide_id"])
        with patch("synapse.llm.stream_text", side_effect=ValueError("测试中断")):
            _, raw = self.req("POST", "/api/chat", body)
        self.assertIn('"type": "error"', raw.decode())
        self.assertEqual(len(self.server.application.store.messages(lecture["id"], "slide", body["slide_id"])), len(before))

    def test_analysis_updates_every_slide(self):
        lecture = self.demo()
        self.req("PUT", "/api/settings", {"api_key": "fake-test-secret", "model": "fake-test-model"})
        with patch("synapse.llm.complete", return_value='{"summary":"整理摘要","knowledge":[{"title":"测试概念","detail":"依据原文"}]}'):
            status, raw = self.req("POST", "/api/analyze", {"lecture_id": lecture["id"]})
            self.assertEqual(status, 200)
            job_id = json.loads(raw)["job_id"]
            for _ in range(200):
                job = json.loads(self.req("GET", "/api/jobs/" + job_id)[1])
                if job["status"] != "running":
                    break
                time.sleep(0.01)
        self.assertEqual(job["status"], "complete", job)
        current = self.server.application.store.get_lecture(lecture["id"])
        self.assertTrue(all(s["knowledge"][0]["title"] == "测试概念" for s in current["slides"]))

    def test_analysis_rejects_images_for_text_only_glm_before_starting_job(self):
        bundle = {
            "course": {"id": "vision-check", "title": "测试课程"},
            "lecture": {"id": "vision-check", "title": "测试课", "duration": 60},
            "slides": [{"start": 0, "image_url": "https://example.com/slide.jpg", "ocr": "测试课件"}],
        }
        status, raw = self.req("POST", "/api/import", bundle)
        self.assertEqual(status, 200, raw)
        self.req("PUT", "/api/settings", {"model": "glm-5.3", "api_key": "fake-test-secret", "send_images": True})
        with patch("synapse.server.Application.start_job") as start_job:
            status, raw = self.req("POST", "/api/analyze", {"lecture_id": "vision-check"})
            self.assertEqual(status, 400, raw)
            self.assertIn("glm-5.3 只支持文本", raw.decode())
            start_job.assert_not_called()
        self.req("PUT", "/api/settings", {"send_images": False})


if __name__ == "__main__":
    unittest.main()
