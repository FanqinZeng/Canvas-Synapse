import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from synapse.demo import demo_bundle, demo_slide_svg
from synapse.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "data.sqlite3"
        self.store = Store(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_reimport_preserves_personal_work_and_analysis(self):
        lecture = self.store.import_bundle(demo_bundle())
        identity = lecture["slides"][0]["id"]
        self.store.update_slide(identity, {"notes": "我自己的问题", "reviewed": True, "bookmarked": True})
        self.store.update_analysis(lecture["id"], identity, [{"title": "新知识点", "detail": "有证据的解释"}], "本页生成总结")
        self.store.set_summary(lecture["id"], "重新整理的课堂概要")
        value = demo_bundle()
        value["lecture"]["summary"] = ""
        value["slides"][0]["knowledge"] = []
        result = self.store.import_bundle(value)
        first = result["slides"][0]
        self.assertEqual(first["id"], identity)
        self.assertEqual(first["notes"], "我自己的问题")
        self.assertTrue(first["reviewed"])
        self.assertTrue(first["bookmarked"])
        self.assertEqual(first["knowledge"][0]["title"], "新知识点")
        self.assertEqual(first["summary"], "本页生成总结")
        self.assertEqual(result["summary"], "重新整理的课堂概要")

    def test_full_and_canonical_json_exports_roundtrip(self):
        lecture = self.store.import_bundle(demo_bundle())
        self.store.update_slide(lecture["slides"][0]["id"], {"notes": "保留我的笔记", "reviewed": True})
        exported = self.store.get_lecture(lecture["id"])
        another = Store(Path(self.temp.name) / "other.sqlite3")
        imported = another.import_bundle(exported)
        self.assertEqual(imported["slides"], exported["slides"])
        self.assertEqual(imported["material_hash"], exported["material_hash"])
        self.assertTrue(imported["is_demo"])
        self.assertEqual(imported["provenance"]["kind"], "demo")
        third = Store(Path(self.temp.name) / "third.sqlite3")
        canonical = third.import_bundle(self.store.export_bundle(lecture["id"]))
        self.assertEqual(canonical["slides"], exported["slides"])

    def test_changed_source_does_not_reuse_old_generated_points(self):
        lecture = self.store.import_bundle(demo_bundle())
        value = demo_bundle()
        value["slides"][0]["ocr"] = "完全不同的新课件"
        value["slides"][0]["knowledge"] = []
        value["lecture"]["summary"] = ""
        result = self.store.import_bundle(value)
        self.assertEqual(result["slides"][0]["knowledge"], [])
        self.assertEqual(result["summary"], "")
        self.assertNotEqual(result["material_hash"], lecture["material_hash"])

    def test_changed_image_does_not_reuse_old_visual_analysis(self):
        lecture = self.store.import_bundle(demo_bundle())
        value = demo_bundle()
        value["slides"][0]["image_url"] = "https://example.com/revised-graph.png"
        value["slides"][0]["knowledge"] = []
        result = self.store.import_bundle(value)
        self.assertEqual(result["slides"][0]["knowledge"], [])
        self.assertNotEqual(result["material_hash"], lecture["material_hash"])

    def test_stale_analysis_cannot_overwrite_reimported_material(self):
        initial = self.store.import_bundle(demo_bundle())
        identity = initial["slides"][0]["id"]
        expected = initial["material_hash"]
        self.store.update_analysis(initial["id"], identity,
                                   [{"title": "已完成的分析", "detail": "旧材料"}], expected_material_hash=expected)
        changed = demo_bundle()
        changed["slides"][0]["ocr"] = "重新导入的图与公式"
        changed["slides"][0]["knowledge"] = [{"title": "新材料知识点", "detail": "须保留"}]
        changed["lecture"]["summary"] = "新材料概要"
        self.store.import_bundle(changed)
        with self.assertRaisesRegex(ValueError, "课程材料已更新，请重新整理"):
            self.store.update_analysis(initial["id"], identity,
                                       [{"title": "延迟完成的旧分析", "detail": "不得写入"}],
                                       "旧页总结", expected_material_hash=expected)
        with self.assertRaisesRegex(ValueError, "课程材料已更新，请重新整理"):
            self.store.set_summary(initial["id"], "延迟完成的旧总结", expected_material_hash=expected)
        final = self.store.get_lecture(initial["id"])
        self.assertEqual(final["slides"][0]["knowledge"][0]["title"], "新材料知识点")
        self.assertEqual(final["summary"], "新材料概要")
        self.assertNotEqual(final["material_hash"], expected)

    def test_current_analysis_hash_allows_atomic_updates(self):
        lecture = self.store.import_bundle(demo_bundle())
        expected = lecture["material_hash"]
        self.store.update_analysis(lecture["id"], lecture["slides"][0]["id"],
                                   [{"title": "完整资料", "detail": "当前版本"}],
                                   "本页总结", expected_material_hash=expected)
        self.store.set_summary(lecture["id"], "当前总结", expected_material_hash=expected)
        final = self.store.get_lecture(lecture["id"])
        self.assertEqual(final["summary"], "当前总结")
        self.assertEqual(final["analysis_material_hash"], expected)

    def test_course_isolation_and_scoped_retrieval(self):
        original = self.store.import_bundle(demo_bundle())
        value = demo_bundle()
        value["course"].update(id="other-course", title="另一课程")
        value["lecture"].update(id="other-lecture", course_id="other-course")
        value["slides"][0].update(ocr="绝密外课程材料独有标识")
        self.store.import_bundle(value)
        hits = self.store.retrieve("面积平衡", original["id"], scope="course")
        self.assertTrue(hits)
        self.assertTrue(all(h["lecture_id"] == original["id"] for h in hits))
        self.assertEqual(self.store.search("独有标识", original["course_id"]), [])
        with self.assertRaises(ValueError):
            self.store.retrieve("问题", original["id"], scope="slide", slide_id="unrelated")

    def test_collision_does_not_overwrite_another_course(self):
        lecture = self.store.import_bundle(demo_bundle())
        value = demo_bundle()
        value["course"]["id"] = "other-course"
        value["lecture"]["course_id"] = "other-course"
        with self.assertRaises(ValueError):
            self.store.import_bundle(value)
        self.assertEqual(self.store.get_lecture(lecture["id"])["course_id"], "demo-vlsi")

    def test_chat_is_durable_and_clear_is_scoped(self):
        lecture = self.store.import_bundle(demo_bundle())
        slide_id = lecture["slides"][0]["id"]
        self.store.save_message(lecture["id"], "lecture", None, "user", "解释一下")
        self.store.save_message(lecture["id"], "slide", slide_id, "assistant", "根据课件", [{"id": "source-1"}])
        reopened = Store(self.path)
        self.assertEqual(reopened.messages(lecture["id"])[0]["content"], "解释一下")
        self.assertEqual(reopened.messages(lecture["id"], "slide", slide_id)[0]["sources"], [{"id": "source-1"}])
        self.assertEqual(reopened.clear_messages(lecture["id"], "slide", slide_id)["deleted"], 1)
        self.assertEqual(len(reopened.messages(lecture["id"])), 1)
        self.assertEqual(reopened.messages(lecture["id"], "slide", slide_id), [])

    def test_markdown_export_contains_full_original_once(self):
        value = demo_bundle()
        value["transcript"] = [{"start": 245, "end": 255, "text": "跨页讲稿唯一标记"}]
        value["warnings"] = ["缺失某段课件"]
        lecture = self.store.import_bundle(value)
        markdown = self.store.export_markdown(lecture["id"])
        self.assertEqual(markdown.count("跨页讲稿唯一标记"), 1)
        self.assertIn("缺失某段课件", markdown)
        self.assertIn("示例内容", markdown)
        self.assertIn("04:05–04:15", markdown)

    def test_state_stats_and_delete_cascade(self):
        lecture = self.store.import_bundle(demo_bundle())
        self.store.save_message(lecture["id"], "lecture", None, "user", "课程问题")
        self.store.update_slide(lecture["slides"][0]["id"], {"reviewed": True})
        state = self.store.state()
        self.assertEqual(state["stats"]["slides"], 6)
        self.assertEqual(state["stats"]["reviewed"], 1)
        self.assertEqual(state["stats"]["video_bytes"], 0)
        self.assertEqual(state["courses"][0]["lecture_count"], 1)
        self.assertNotIn("transcript", state["lectures"][0])
        self.store.delete_lecture(lecture["id"])
        self.assertEqual(self.store.state()["courses"], [])
        self.assertEqual(self.store.stats()["slides"], 0)
        with self.assertRaises(KeyError):
            self.store.get_lecture(lecture["id"])

    def test_parallel_updates_do_not_lose_fields(self):
        lecture = self.store.import_bundle(demo_bundle())
        slide_id = lecture["slides"][0]["id"]
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.store.update_slide, slide_id, change) for change in
                       [{"notes": "并发笔记"}, {"reviewed": True}, {"bookmarked": True}]]
            for future in futures:
                future.result()
        slide = self.store.get_lecture(lecture["id"])["slides"][0]
        self.assertEqual(slide["notes"], "并发笔记")
        self.assertTrue(slide["reviewed"])
        self.assertTrue(slide["bookmarked"])

    def test_demo_svg_is_small_and_explicitly_synthetic(self):
        svg = demo_slide_svg(1)
        self.assertIn("SYNTHETIC DEMO", svg)
        self.assertIn("示例课件", svg)
        self.assertLess(len(svg.encode()), 10000)
        with self.assertRaises(KeyError):
            demo_slide_svg(7)


if __name__ == "__main__":
    unittest.main()
