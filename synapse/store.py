"""Thread-safe, dependency-free SQLite persistence for the local workspace."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .materials import normalize_bundle, normalize_knowledge, retrieve, timestamp, tokenize


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS courses (
                    id TEXT PRIMARY KEY, data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lectures (
                    id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses(id),
                    data TEXT NOT NULL, imported_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS lectures_course ON lectures(course_id);
                CREATE TABLE IF NOT EXISTS slides (
                    id TEXT PRIMARY KEY, lecture_id TEXT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL, data TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS slides_lecture ON slides(lecture_id, position);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lecture_id TEXT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
                    scope TEXT NOT NULL, slide_id TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL, content TEXT NOT NULL, sources TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS messages_session ON messages(lecture_id, scope, slide_id, id);
                PRAGMA user_version = 1;
            """)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    @contextmanager
    def _db(self, write=False):
        db = sqlite3.connect(str(self.path), timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _get_lecture(self, db, lecture_id):
        row = db.execute("SELECT data, imported_at FROM lectures WHERE id=?", (str(lecture_id),)).fetchone()
        if row is None:
            raise KeyError("课堂不存在")
        lecture = json.loads(row["data"])
        lecture["imported_at"] = row["imported_at"]
        lecture["slides"] = [json.loads(row["data"]) for row in db.execute(
            "SELECT data FROM slides WHERE lecture_id=? ORDER BY position", (str(lecture_id),))]
        course = db.execute("SELECT data FROM courses WHERE id=?", (lecture["course_id"],)).fetchone()
        lecture["course"] = json.loads(course["data"]) if course else {"id": lecture["course_id"], "title": lecture["course_title"]}
        lecture["course_title"] = lecture["course"]["title"]
        lecture["slide_count"] = len(lecture["slides"])
        lecture["reviewed_count"] = sum(bool(s.get("reviewed")) for s in lecture["slides"])
        lecture["bookmarked_count"] = sum(bool(s.get("bookmarked")) for s in lecture["slides"])
        return lecture

    def get_lecture(self, lecture_id):
        with self._db() as db:
            return self._get_lecture(db, lecture_id)

    def import_bundle(self, bundle):
        lecture = normalize_bundle(bundle)
        course = lecture.pop("course")
        slides = lecture.pop("slides")
        with self._db(write=True) as db:
            old = db.execute("SELECT course_id, data FROM lectures WHERE id=?", (lecture["id"],)).fetchone()
            if old and old["course_id"] != lecture["course_id"]:
                raise ValueError("课堂 ID 已属于另一课程，请使用不同 ID")
            previous = {row["id"]: json.loads(row["data"]) for row in db.execute(
                "SELECT id,data FROM slides WHERE lecture_id=?", (lecture["id"],))}
            if old:
                old_data = json.loads(old["data"])
                if old_data.get("material_hash") == lecture["material_hash"] and not lecture.get("summary"):
                    lecture["summary"] = old_data.get("summary", "")
            for slide in slides:
                prior = previous.get(slide["id"])
                if prior:
                    for field in ("notes", "bookmarked", "reviewed"):
                        slide[field] = prior.get(field, slide[field])
                    unchanged = all(prior.get(field) == slide.get(field) for field in ("title", "ocr", "image_url", "transcript"))
                    if not slide["knowledge"] and unchanged:
                        slide["knowledge"] = prior.get("knowledge", [])
                        slide["analysis_updated_at"] = prior.get("analysis_updated_at")
                        if not slide.get("summary"):
                            slide["summary"] = prior.get("summary", "")
            db.execute("INSERT INTO courses(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                       (course["id"], _json(course)))
            db.execute("INSERT INTO lectures(id,course_id,data,imported_at) VALUES(?,?,?,?) "
                       "ON CONFLICT(id) DO UPDATE SET data=excluded.data,imported_at=excluded.imported_at",
                       (lecture["id"], course["id"], _json(lecture), _now()))
            db.execute("DELETE FROM slides WHERE lecture_id=?", (lecture["id"],))
            db.executemany("INSERT INTO slides(id,lecture_id,position,data) VALUES(?,?,?,?)",
                           [(s["id"], lecture["id"], s["index"], _json(s)) for s in slides])
            return self._get_lecture(db, lecture["id"])

    def update_slide(self, slide_id, changes):
        allowed = {"notes", "bookmarked", "reviewed"}
        if not isinstance(changes, dict) or set(changes) - allowed:
            raise ValueError("只能修改笔记、收藏和已复习状态")
        if "notes" in changes and (not isinstance(changes["notes"], str) or len(changes["notes"]) > 2_000_000):
            raise ValueError("笔记须为不超过 200 万字符的文字")
        for key in ("bookmarked", "reviewed"):
            if key in changes and not isinstance(changes[key], bool):
                raise ValueError("%s 必须是布尔值" % key)
        with self._db(write=True) as db:
            row = db.execute("SELECT data FROM slides WHERE id=?", (str(slide_id),)).fetchone()
            if row is None:
                raise KeyError("幻灯片不存在")
            slide = json.loads(row["data"])
            slide.update(changes)
            db.execute("UPDATE slides SET data=? WHERE id=?", (_json(slide), str(slide_id)))
            return slide

    def _analysis_lecture(self, db, lecture_id, expected_material_hash):
        row = db.execute("SELECT data FROM lectures WHERE id=?", (str(lecture_id),)).fetchone()
        if row is None:
            raise KeyError("课堂不存在")
        lecture = json.loads(row["data"])
        if expected_material_hash is not None and lecture.get("material_hash") != expected_material_hash:
            raise ValueError("课程材料已更新，请重新整理")
        return lecture

    def update_analysis(self, lecture_id, slide_id, knowledge, summary=None, expected_material_hash=None):
        knowledge = normalize_knowledge(knowledge)
        with self._db(write=True) as db:
            self._analysis_lecture(db, lecture_id, expected_material_hash)
            row = db.execute("SELECT data FROM slides WHERE id=? AND lecture_id=?", (str(slide_id), str(lecture_id))).fetchone()
            if row is None:
                raise KeyError("幻灯片不存在或不属于此课堂")
            slide = json.loads(row["data"])
            slide.update(knowledge=knowledge, analysis_updated_at=_now())
            if summary is not None:
                if not isinstance(summary, str) or len(summary) > 2_000_000:
                    raise ValueError("幻灯片总结格式无效")
                slide["summary"] = summary
            db.execute("UPDATE slides SET data=? WHERE id=?", (_json(slide), str(slide_id)))
            return slide

    def set_summary(self, lecture_id, summary, expected_material_hash=None):
        if not isinstance(summary, str) or len(summary) > 2_000_000:
            raise ValueError("课堂概要格式无效或过长")
        with self._db(write=True) as db:
            lecture = self._analysis_lecture(db, lecture_id, expected_material_hash)
            lecture["summary"] = summary
            lecture["analysis_updated_at"] = _now()
            lecture["analysis_material_hash"] = lecture.get("material_hash")
            db.execute("UPDATE lectures SET data=? WHERE id=?", (_json(lecture), str(lecture_id)))
        return summary

    def delete_lecture(self, lecture_id):
        with self._db(write=True) as db:
            row = db.execute("SELECT course_id FROM lectures WHERE id=?", (str(lecture_id),)).fetchone()
            if row is None:
                raise KeyError("课堂不存在")
            db.execute("DELETE FROM lectures WHERE id=?", (str(lecture_id),))
            db.execute("DELETE FROM courses WHERE id=? AND NOT EXISTS(SELECT 1 FROM lectures WHERE course_id=?)",
                       (row["course_id"], row["course_id"]))
        return {"deleted": str(lecture_id)}

    def state(self):
        with self._db() as db:
            courses = [json.loads(row["data"]) for row in db.execute("SELECT data FROM courses ORDER BY id")]
            lectures = []
            for row in db.execute("SELECT id FROM lectures ORDER BY imported_at DESC"):
                lecture = self._get_lecture(db, row["id"])
                slides = lecture.pop("slides")
                lecture.pop("transcript", None)
                lecture.pop("material_hash", None)
                lecture["knowledge_count"] = sum(len(s.get("knowledge", [])) for s in slides)
                lecture["thumbnail"] = next((s["image_url"] for s in slides if s.get("image_url")), "")
                lectures.append(lecture)
            for course in courses:
                course["lecture_count"] = sum(l["course_id"] == course["id"] for l in lectures)
            return {"courses": courses, "lectures": lectures, "stats": self._stats(db)}

    def _stats(self, db):
        lectures = [json.loads(row["data"]) for row in db.execute("SELECT data FROM lectures")]
        slides = [json.loads(row["data"]) for row in db.execute("SELECT data FROM slides")]
        storage_bytes = sum(p.stat().st_size for p in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")) if p.exists())
        return {"courses": db.execute("SELECT count(*) FROM courses").fetchone()[0],
                "lectures": len(lectures), "slides": len(slides),
                "reviewed": sum(bool(s.get("reviewed")) for s in slides),
                "bookmarks": sum(bool(s.get("bookmarked")) for s in slides),
                "knowledge_points": sum(len(s.get("knowledge", [])) for s in slides),
                "transcript_segments": sum(len(l.get("transcript", [])) for l in lectures),
                "duration": sum(l.get("duration", 0) for l in lectures),
                "storage_bytes": storage_bytes, "video_bytes": 0}

    def stats(self):
        with self._db() as db:
            return self._stats(db)

    def search(self, query, course_id=None):
        query = str(query or "").strip()
        if not query:
            return []
        if len(query) > 2000:
            raise ValueError("检索词过长")
        terms = tokenize(query)
        hits = []
        with self._db() as db:
            for row in db.execute("SELECT id,course_id FROM lectures"):
                if course_id is not None and row["course_id"] != str(course_id):
                    continue
                lecture = self._get_lecture(db, row["id"])
                for slide in lecture["slides"]:
                    text = "\n".join([slide["title"], slide.get("ocr", ""), slide.get("notes", "")] +
                                     [s["text"] for s in slide.get("transcript", [])] +
                                     [k["title"] + " " + k["detail"] for k in slide.get("knowledge", [])])
                    tokens = tokenize(text)
                    overlap = sum(min(tokens[t], 3) * (1.5 if len(t) > 1 else 0.2) for t in terms)
                    direct = text.lower().find(query.lower())
                    strong = [t for t in terms if len(t) > 1]
                    # One common Chinese character (e.g. 的/有) must not make
                    # every page a search result for a multi-character query.
                    if direct < 0 and (overlap <= 0 or (strong and not any(tokens[t] for t in strong))):
                        continue
                    score = overlap + (10 if direct >= 0 else 0)
                    start = max(0, direct - 40) if direct >= 0 else 0
                    hits.append({"lecture_id": lecture["id"], "course_id": lecture["course_id"],
                                 "slide_id": slide["id"], "title": slide["title"],
                                 "lecture_title": lecture["title"], "index": slide["index"],
                                 "start": slide["start"], "end": slide["end"],
                                 "snippet": text[start:start + 240], "score": round(score, 3)})
        return sorted(hits, key=lambda h: (-h["score"], h["lecture_id"], h["index"]))[:100]

    def retrieve(self, question, lecture_id, scope="lecture", slide_id=None, limit=8, budget=24000):
        if scope not in ("slide", "lecture", "course"):
            raise ValueError("问答范围无效")
        with self._db() as db:
            current = self._get_lecture(db, lecture_id)
            if scope == "slide":
                if slide_id is None or not any(s["id"] == str(slide_id) for s in current["slides"]):
                    raise ValueError("请选择当前课堂的一页 slide")
                lectures = [current]
            elif scope == "course":
                lectures = [self._get_lecture(db, row["id"]) for row in db.execute(
                    "SELECT id FROM lectures WHERE course_id=? ORDER BY imported_at", (current["course_id"],))]
            else:
                lectures = [current]
        return retrieve(lectures, question, str(slide_id) if scope == "slide" else None, limit, budget)

    def _session(self, db, lecture_id, scope, slide_id):
        if scope not in ("slide", "lecture", "course"):
            raise ValueError("问答范围无效")
        lecture = self._get_lecture(db, lecture_id)
        if scope == "slide":
            if slide_id is None or not any(s["id"] == str(slide_id) for s in lecture["slides"]):
                raise ValueError("所选 slide 不属于当前课堂")
            return str(slide_id)
        return ""

    def save_message(self, lecture_id, scope, slide_id, role, content, sources=None):
        if role not in ("user", "assistant"):
            raise ValueError("消息角色无效")
        if not isinstance(content, str) or len(content) > 2_000_000:
            raise ValueError("消息格式无效或过长")
        if sources is None:
            sources = []
        if not isinstance(sources, list):
            raise ValueError("消息来源必须是列表")
        with self._db(write=True) as db:
            slide_key = self._session(db, lecture_id, scope, slide_id)
            created_at = _now()
            cursor = db.execute("INSERT INTO messages(lecture_id,scope,slide_id,role,content,sources,created_at) VALUES(?,?,?,?,?,?,?)",
                                (str(lecture_id), scope, slide_key, role, content, _json(sources), created_at))
            return {"id": cursor.lastrowid, "role": role, "content": content, "sources": sources, "created_at": created_at}

    def messages(self, lecture_id, scope="lecture", slide_id=None):
        with self._db() as db:
            slide_key = self._session(db, lecture_id, scope, slide_id)
            rows = db.execute("SELECT * FROM messages WHERE lecture_id=? AND scope=? AND slide_id=? ORDER BY id",
                              (str(lecture_id), scope, slide_key))
            return [{"id": row["id"], "role": row["role"], "content": row["content"],
                     "sources": json.loads(row["sources"]), "created_at": row["created_at"]} for row in rows]

    def clear_messages(self, lecture_id, scope="lecture", slide_id=None):
        with self._db(write=True) as db:
            slide_key = self._session(db, lecture_id, scope, slide_id)
            count = db.execute("DELETE FROM messages WHERE lecture_id=? AND scope=? AND slide_id=?",
                               (str(lecture_id), scope, slide_key)).rowcount
        return {"deleted": count}

    def export_markdown(self, lecture_id):
        lecture = self.get_lecture(lecture_id)
        lines = ["# " + lecture["title"], "", "课程：" + lecture["course_title"], "日期：" + lecture["date"],
                 "时长：" + timestamp(lecture["duration"])]
        if lecture.get("is_demo"):
            lines += ["", "> 示例内容：为演示功能编写，不是实际课堂录音或课件。"]
        if lecture.get("source_url"):
            lines += ["来源：" + lecture["source_url"]]
        for warning in lecture.get("warnings", []):
            lines += ["", "> 材料提示：" + warning]
        if lecture.get("summary"):
            lines += ["", "## 课堂概要", "", lecture["summary"]]
        for slide in lecture["slides"]:
            lines += ["", "## 第 %d 页 · %s" % (slide["index"], slide["title"]),
                      "", "时间：%s–%s" % (timestamp(slide["start"]), timestamp(slide["end"]))]
            if slide.get("image_url"):
                lines += ["", "课件图片：" + slide["image_url"]]
            if slide.get("ocr"):
                lines += ["", "### 课件原文", "", slide["ocr"]]
            if slide.get("knowledge"):
                lines += ["", "### 知识点", ""]
                for item in slide["knowledge"]:
                    lines += ["- **%s**：%s" % (item["title"], item["detail"])]
            if slide.get("summary"):
                lines += ["", "### 本页总结", "", slide["summary"]]
            if slide.get("notes"):
                lines += ["", "### 我的笔记", "", slide["notes"]]
        # Export the original transcript once, not the repeated per-slide view.
        lines += ["", "## 完整课堂讲稿", ""]
        for segment in lecture["transcript"]:
            lines.append("[%s–%s] %s" % (timestamp(segment["start"]), timestamp(segment["end"]), segment["text"]))
        return "\n".join(lines) + "\n"

    def export_bundle(self, lecture_id):
        lecture = self.get_lecture(lecture_id)
        return {"schema_version": 1, "course": lecture["course"],
                "lecture": {k: v for k, v in lecture.items() if k not in ("course", "slides", "transcript")},
                "slides": lecture["slides"], "transcript": lecture["transcript"]}
