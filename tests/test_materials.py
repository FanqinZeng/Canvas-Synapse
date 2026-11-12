import unittest
from unittest.mock import patch

from synapse.materials import normalize_bundle, retrieve, sources_for, timestamp


def bundle(**overrides):
    value = {
        "course": {"id": "course-a", "title": "算法"},
        "lecture": {"id": "lecture-a", "title": "图划分", "duration": 30},
        "slides": [{"id": "a", "start": 5, "end": 10, "ocr": "连接与边权"},
                   {"id": "b", "start": 10, "end": 20, "ocr": "面积平衡"}],
        "transcript": [{"start": 0, "end": 4, "text": "开场"},
                       {"start": 5, "end": 10, "text": "第一页的完整话语"},
                       {"start": 10, "end": 12, "text": "恰好从第二页开始"},
                       {"start": 19, "end": 25, "text": "跨越结尾的话语"},
                       {"start": 28, "end": 30, "text": "结尾"}],
    }
    value.update(overrides)
    return value


class MaterialTests(unittest.TestCase):
    def test_half_open_alignment_preserves_intro_and_outro(self):
        result = normalize_bundle(bundle())
        first, second = result["slides"]
        self.assertEqual([s["text"] for s in first["transcript"]], ["开场", "第一页的完整话语"])
        self.assertEqual([s["text"] for s in second["transcript"]],
                         ["恰好从第二页开始", "跨越结尾的话语", "结尾"])
        attached = {s["id"] for slide in result["slides"] for s in slide["transcript"]}
        self.assertEqual(attached, {s["id"] for s in result["transcript"]})

    def test_sentence_spanning_pages_is_visible_on_both(self):
        value = bundle(transcript=[{"start": 8, "end": 12, "text": "这是跨页句子"}])
        result = normalize_bundle(value)
        self.assertEqual(result["slides"][0]["transcript"], result["slides"][1]["transcript"])
        self.assertEqual(len(result["transcript"]), 1)

    def test_zero_length_boundary_belongs_to_next_page(self):
        result = normalize_bundle(bundle(transcript=[{"start": 10, "end": 10, "text": "边界"}]))
        self.assertEqual(result["slides"][0]["transcript"], [])
        self.assertEqual(result["slides"][1]["transcript"][0]["text"], "边界")

    def test_explicit_gap_is_not_lost(self):
        value = bundle(slides=[{"start": 0, "end": 5}, {"start": 10, "end": 15}],
                       transcript=[{"start": 7, "end": 9, "text": "换页期间的讲话"}])
        result = normalize_bundle(value)
        self.assertEqual(result["slides"][0]["transcript"][0]["text"], "换页期间的讲话")

    def test_no_slides_creates_transcript_only_page(self):
        result = normalize_bundle(bundle(slides=[]))
        self.assertEqual(len(result["slides"]), 1)
        self.assertEqual(len(result["slides"][0]["transcript"]), 5)
        self.assertEqual(result["slides"][0]["title"], "课堂讲稿")

    def test_no_transcript_still_retains_slide_and_warning(self):
        value = bundle(transcript=[], warnings=["平台尚无讲稿"])
        result = normalize_bundle(value)
        self.assertEqual(result["warnings"], ["平台尚无讲稿"])
        self.assertEqual(result["slides"][0]["ocr"], "连接与边权")

    def test_unordered_transcript_roundtrip_is_stable(self):
        value = bundle()
        value["transcript"].reverse()
        initial = normalize_bundle(value)
        again = normalize_bundle(initial)
        self.assertEqual(initial["transcript"], again["transcript"])
        self.assertEqual(initial["material_hash"], again["material_hash"])
        self.assertEqual(initial["slides"], again["slides"])

    def test_invalid_times_fail_instead_of_silently_changing_material(self):
        for segment in [{"start": 10, "end": 5}, {"start": -1, "end": 5}, {"start": float("nan"), "end": 5},
                        {"start": True, "end": 5}]:
            with self.subTest(segment=segment), self.assertRaises(ValueError):
                normalize_bundle(bundle(transcript=[dict(segment, text="讲稿")]))

    def test_duplicate_slide_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "重复"):
            normalize_bundle(bundle(slides=[{"id": "same"}, {"id": "same"}]))

    def test_long_transcript_and_slide_text_are_not_cut(self):
        text = "完整的讲稿不能被截断。" * 4000
        result = normalize_bundle(bundle(transcript=[{"start": 0, "end": 30, "text": text}],
                                         slides=[{"start": 0, "ocr": text}]))
        self.assertEqual(result["transcript"][0]["text"], text)
        self.assertEqual(result["slides"][0]["ocr"], text)
        evidence = [s["text"] for s in sources_for(result) if s["kind"] == "slide"]
        self.assertEqual("".join(evidence), text)

    def test_retrieval_finds_chinese_term_and_obeys_budget(self):
        result = normalize_bundle(bundle())
        hits = retrieve(result, "面积平衡", limit=2, budget=2000)
        self.assertEqual(hits[0]["slide_id"], result["slides"][1]["id"])
        self.assertGreater(hits[0]["score"], 0)
        self.assertIn("面积平衡", hits[0]["text"])
        self.assertLessEqual(sum(len(s["text"]) + len(s["title"]) + 120 for s in hits), 2000)

    def test_slide_scope_does_not_retrieve_other_pages(self):
        result = normalize_bundle(bundle())
        slide_id = result["slides"][0]["id"]
        hits = retrieve(result, "面积平衡", slide_id=slide_id)
        self.assertTrue(all(s["slide_id"] == slide_id for s in hits))

    def test_nonmonotone_explicit_end_times_keep_all_actual_overlaps(self):
        value = bundle(slides=[{"start": 0, "end": 30}, {"start": 5, "end": 10}, {"start": 10, "end": 15}],
                       transcript=[{"start": 12, "end": 13, "text": "覆盖第一页和第三页"}])
        result = normalize_bundle(value)
        self.assertEqual([len(s["transcript"]) for s in result["slides"]], [1, 0, 1])

    def test_pathological_overlap_fails_explicitly_without_truncating_import(self):
        value = bundle(slides=[{"start": i, "end": 100} for i in range(4)],
                       transcript=[{"start": 10, "end": 20, "text": "相同讲稿"} for _ in range(3)])
        with patch("synapse.materials.MAX_ALIGNMENT_LINKS", 10), self.assertRaisesRegex(ValueError, "重复对齐过多"):
            normalize_bundle(value)

    def test_timestamps(self):
        self.assertEqual(timestamp(61.5), "01:01")
        self.assertEqual(timestamp(3661), "1:01:01")


if __name__ == "__main__":
    unittest.main()
