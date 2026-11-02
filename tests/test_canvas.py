import json
import unittest
from urllib.parse import parse_qs, urlsplit

from synapse.canvas import (CanvasClient, CanvasError, _school_url, jwt_from_url,
                            parse_form, parse_slides, parse_transcript)


def response(data, status=200, headers=None):
    return status, headers or {}, json.dumps(data).encode("utf-8")


class SchoolTransport:
    def __init__(self, subtitles=True, slides=True):
        self.calls = []
        self.subtitles, self.slides = subtitles, slides

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        parsed, query = urlsplit(url), parse_qs(urlsplit(url).query)
        if parsed.path == "/api/v1/courses":
            return response([{"id": 42, "name": "VLSI", "term": {"name": "2026 秋"}}])
        if parsed.path == "/api/v1/courses/42":
            return response({"id": 42, "name": "VLSI"})
        if parsed.path.endswith("sessionless_launch"):
            return response({"url": "https://oc.sjtu.edu.cn/lti-launch"})
        if parsed.path == "/lti-launch":
            return 200, {}, b'<form action="https://v.sjtu.edu.cn/oidc" method="post"><input name="id_token" value="one-time"></form>'
        if parsed.path == "/oidc":
            assert method == "POST"
            assert body == b"id_token=one-time"
            return 302, {"Location": "https://v.sjtu.edu.cn/ui/#/play?jwt_token=ephemeral"}, b""
        if parsed.path.endswith("/lms/launch-context"):
            return response({"data": {"canvasRecord": {"teachingClassId": 64}}})
        if parsed.path.endswith("subject_vod_list_new"):
            return response({"data": {"records": [{"id": 123, "subjName": "VLSI", "tecName": "教师",
                                                      "courBeginTime": "2026-10-27 17:55:00",
                                                      "courEndTime": "2026-10-27 18:50:00",
                                                      "weekNumber": 7, "letiNumber": 11}]}})
        if "/translate/" in parsed.path:
            rows = [{"bg": 1000, "ed": 2000, "res": "完整讲稿"},
                    {"bg": 3299000, "ed": 3300000, "res": "最后一秒也保留"}] if self.subtitles else []
            return response({"data": {"beforeAssemblyList": rows}})
        if parsed.path.endswith("/ai/ppt"):
            rows = [{"imageSeekTime": 1, "imageUrl": "https://cdn.sjtu.edu.cn/slide.jpg",
                     "ocrText": "图划分\ncutsize", "textKeywordList": ["cutsize"]},
                    {"imageSeekTime": 21, "imageUrl": "https://cdn.sjtu.edu.cn/slide2.jpg", "ocrText": "平衡"}] if self.slides else []
            return response({"data": {"docList": rows}})
        raise AssertionError("Unexpected API request: %s" % parsed.path)


class CanvasTests(unittest.TestCase):
    def test_subtitle_ms_and_slide_seconds_are_distinct(self):
        transcript = parse_transcript({"beforeAssemblyList": [{"bg": 1500, "ed": 2500, "res": "定义"}]})
        self.assertEqual(transcript[0]["start"], 1.5)
        self.assertEqual(transcript[0]["end"], 2.5)
        slides = parse_slides({"docList": [{"imageSeekTime": 41, "ocrText": "PPT"},
                                           {"imageSeekTime": 4, "ocrText": "第一页"}]})
        self.assertEqual(slides[0]["start"], 4)
        self.assertEqual(slides[0]["end"], 41)

    def test_subtitles_fall_back_to_assembled_if_blank_original(self):
        rows = parse_transcript({"beforeAssemblyList": [{"res": "  "}],
                                 "afterAssemblyList": [{"bg": 30, "ed": 40, "res": "有效"}]})
        self.assertEqual(rows[0]["text"], "有效")

    def test_lti_form_uses_first_form_and_decodes_entities(self):
        form = parse_form('<form method="POST" action="/login"><input name="a" value="x&amp;y"></form><form action="/other"></form>')
        self.assertEqual(form, ("/login", "POST", {"a": "x&y"}))
        self.assertEqual(jwt_from_url("https://v.sjtu.edu.cn/#/x?jwt_token=a%2Bb"), "a+b")

    def test_end_to_end_bundle_never_requests_video_and_redacts_credentials(self):
        transport = SchoolTransport()
        client = CanvasClient("unit-test-token", transport=transport)
        self.assertEqual(client.courses()[0]["term"], "2026 秋")
        bundle = client.bundle(42, 123)
        self.assertEqual(bundle["lecture"]["id"], "sjtu:42:123")
        self.assertEqual(bundle["course"]["id"], "sjtu:42")
        self.assertEqual(bundle["slides"][-1]["end"], 3300)
        self.assertEqual(bundle["transcript"][-1]["text"], "最后一秒也保留")
        self.assertNotIn("unit-test-token", json.dumps(bundle))
        self.assertNotIn("ephemeral", json.dumps(bundle))
        for _, url, headers, _ in transport.calls:
            self.assertFalse(any(extension in url for extension in (".mp4", ".m3u8", ".flv")))
            if "Authorization" in headers:
                self.assertEqual(urlsplit(url).hostname, "oc.sjtu.edu.cn")
            if "jwt-token" in headers:
                self.assertEqual(urlsplit(url).hostname, "v.sjtu.edu.cn")
        self.assertNotIn("Authorization", client.image_headers("https://cdn.sjtu.edu.cn/a.jpg"))

    def test_recording_must_belong_to_selected_course(self):
        transport = SchoolTransport()
        with self.assertRaisesRegex(CanvasError, "不属于"):
            CanvasClient("token", transport=transport).bundle(42, 999)
        self.assertFalse(any("/translate/" in item[1] for item in transport.calls))

    def test_missing_transcript_is_explicit_and_does_not_drop_slides(self):
        bundle = CanvasClient("token", transport=SchoolTransport(subtitles=False)).bundle(42, 123)
        self.assertTrue(bundle["slides"])
        self.assertEqual(bundle["transcript"], [])
        self.assertIn("讲稿", bundle["warnings"][0])
        with self.assertRaisesRegex(CanvasError, "尚无"):
            CanvasClient("token", transport=SchoolTransport(subtitles=False, slides=False)).bundle(42, 123)

    def test_lti_and_canvas_pagination_never_leave_school(self):
        for url in ("https://sjtu.edu.cn.evil.test/", "https://oc.sjtu.edu.cn@evil.test/", "http://v.sjtu.edu.cn/",
                    "https://evil.test/", "https://v.sjtu.edu.cn:8443/"):
            with self.assertRaises(CanvasError):
                _school_url(url)
        calls = []
        def malicious(method, url, headers, body):
            calls.append(url)
            return response([], headers={"Link": '<https://evil.test/api/v1/courses>; rel="next"'})
        with self.assertRaises(CanvasError):
            CanvasClient("token", transport=malicious).courses()
        self.assertEqual(len(calls), 1)

    def test_bearer_cannot_be_sent_to_video_host(self):
        with self.assertRaises(CanvasError):
            CanvasClient("token", transport=SchoolTransport())._request("GET", "https://v.sjtu.edu.cn/api/v1/a", {"Authorization": "Bearer token"})

    def test_base_url_and_id_validation(self):
        with self.assertRaises(CanvasError):
            CanvasClient("token", base="https://other.test")
        with self.assertRaises(CanvasError):
            CanvasClient("token", transport=SchoolTransport()).lectures("../user")


if __name__ == "__main__":
    unittest.main()
