"""Local-only HTTP application, SQLite storage and bounded background jobs."""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import __version__
from .settings import Settings
from .store import Store
from . import llm
from .net import open_request, read_limited

STATIC = Path(__file__).parent / "static"
CACHE_LIMIT = 128 * 1024 * 1024
MAX_BODY = 16 * 1024 * 1024


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def split_material(text, limit=6500):
    """Cover all input, even an exceptionally long single paragraph."""
    result, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            result.append(current)
            current = ""
        while len(line) > limit:
            result.append(line[:limit])
            line = line[limit:]
        current += line
    if current:
        result.append(current)
    return result or [""]


class Application:
    def __init__(self, data_dir):
        self.directory = Path(data_dir).resolve()
        self.settings = Settings(self.directory)
        self.store = Store(self.directory / "synapse.sqlite3")
        self.cache = self.directory / "cache"
        self.cache.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.jobs = {}
        self.clients = {}
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="synapse")

    def canvas(self):
        from .canvas import CanvasClient
        config = self.settings.get()
        if not config.get("canvas_token"):
            raise ValueError("请先在设置中保存 Canvas Access Token")
        key = hashlib.sha256(config["canvas_token"].encode()).hexdigest()
        # Keep an authenticated connector private to its job/request. Tokens never enter a URL.
        return CanvasClient(config["canvas_token"], config["canvas_base"])

    def start_job(self, label, fn, key):
        with self.lock:
            for existing in self.jobs.values():
                if existing["key"] == key and existing["status"] == "running":
                    return existing["id"]
            if sum(j["status"] == "running" for j in self.jobs.values()) >= 8:
                raise ValueError("任务较多，请等待当前任务完成")
            identity = uuid.uuid4().hex
            self.jobs[identity] = {"id": identity, "key": key, "label": label, "status": "running",
                                   "progress": 0, "message": "等待处理", "result": {}, "created_at": time.time()}
        def update(progress, message):
            with self.lock:
                self.jobs[identity].update(progress=progress, message=message)
        def run():
            try:
                result = fn(update)
                with self.lock:
                    self.jobs[identity].update(status="complete", progress=100, message="处理完成", result=result or {})
            except Exception as e:
                with self.lock:
                    self.jobs[identity].update(status="failed", error=self.safe_error(e), message="处理失败，可重试")
        self.pool.submit(run)
        return identity

    def safe_error(self, error):
        message = str(error) if isinstance(error, (ValueError, KeyError)) else "处理未完成，请检查材料或连接后重试"
        config = self.settings.get()
        for key in ("api_key", "canvas_token"):
            if config.get(key):
                message = message.replace(config[key], "[已隐藏]")
        return message[:500]

    def cache_bytes(self):
        with self.lock:
            return sum(p.stat().st_size for p in self.cache.glob("*") if p.is_file())

    def clear_cache(self):
        with self.lock:
            amount = self.cache_bytes()
            for p in self.cache.glob("*"):
                if p.is_file():
                    p.unlink(missing_ok=True)
            return amount

    def asset(self, url):
        name = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / name
        allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        with self.lock:
            if path.exists():
                data = path.read_bytes()
                os.utime(str(path), None)
                mime, body = data.split(b"\n", 1)
                return mime.decode(), body
        # Never attach Canvas or model credentials to user-supplied/CDN URLs.
        headers = {"Accept": "image/png,image/jpeg,image/webp,image/gif", "Referer": "https://v.sjtu.edu.cn/"}
        with open_request(url, headers=headers, timeout=30) as response:
            mime = response.headers.get_content_type()
            if mime not in allowed:
                raise ValueError("远端没有返回支持的图片；可尝试重新同步课程更新图片地址")
            body = read_limited(response, 8 * 1024 * 1024)
        with self.lock:
            # LRU eviction; no growing video/audio cache or background prefetch.
            used = self.cache_bytes()
            for old in sorted(self.cache.glob("*"), key=lambda p: p.stat().st_mtime):
                if used + len(body) < CACHE_LIMIT:
                    break
                used -= old.stat().st_size
                old.unlink(missing_ok=True)
            tmp = self.cache / (name + ".tmp")
            tmp.write_bytes(mime.encode() + b"\n" + body)
            tmp.replace(path)
        return mime, body

    def analyze(self, lecture_id):
        config = self.settings.get()
        llm.check_config(config)
        lecture = self.store.get_lecture(lecture_id)
        if not lecture:
            raise ValueError("未找到课程回放")
        if config.get("send_images") and any(
            slide.get("image_url") and not slide["image_url"].startswith("/demo-slides/")
            for slide in lecture["slides"]
        ):
            llm.check_image_input(config)

        def run(update):
            summaries = []
            slides = lecture["slides"]
            for i, slide in enumerate(slides):
                update(round(i / max(len(slides), 1) * 100), "整理第 %s / %s 页" % (i + 1, len(slides)))
                # Preserve source speech verbatim. AI knowledge is stored separately.
                raw = "课件文字：\n" + slide.get("ocr", "") + "\n老师讲稿：\n" + "\n".join(
                    "[%s–%s] %s" % (s["start"], s["end"], s["text"]) for s in slide.get("transcript", []))
                if not slide.get("ocr", "").strip() and not any(s.get("text", "").strip() for s in slide.get("transcript", [])) and not (config.get("send_images") and slide.get("image_url")):
                    summary = "本页缺少可用的课件文字与讲稿，未推测知识点；可重新同步，或开启支持视觉的图片分析。"
                    self.store.update_analysis(lecture_id, slide["id"], [], summary,
                                               expected_material_hash=lecture["material_hash"])
                    summaries.append("### %s\n%s" % (slide["title"], summary))
                    continue
                pieces = split_material(raw, min(6500, max(2000, config["context_chars"] - 2000)))
                knowledge = []
                page_summaries = []
                for part, text in enumerate(pieces):
                    prompt = ("整理这页课堂材料的第 %s/%s 段。仅输出 JSON："
                              '{"summary":"本段摘要","knowledge":[{"title":"知识点","detail":"解释、条件、推导或例子"}]}。'
                              "保留公式和术语，资料缺失处注明缺失。不要伪造讲稿或页码。\n课程：%s\n页标题：%s\n%s"
                              % (part + 1, len(pieces), lecture.get("course_title", ""), slide["title"], text))
                    content = prompt
                    if config.get("send_images") and part == 0 and slide.get("image_url"):
                        image_url = slide["image_url"]
                        if image_url.startswith("/demo-slides/"):
                            # SVG demo is adequately represented by its complete OCR.
                            image_url = None
                        if image_url:
                            mime, image = self.asset(image_url)
                            if len(image) > 3 * 1024 * 1024:
                                raise ValueError("第 %s 页图片超过视觉分析上限 3MB，可关闭图片分析后重试" % (i + 1))
                            data_url = "data:%s;base64,%s" % (mime, base64.b64encode(image).decode())
                            content = [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}]
                    try:
                        parsed = llm.generate_knowledge(config, content)
                    except ValueError as error:
                        raise ValueError("第 %s 页、第 %s 段整理失败：%s" % (i + 1, part + 1, error)) from None
                    knowledge.extend(parsed["knowledge"])
                    page_summaries.append(parsed["summary"])
                self.store.update_analysis(lecture_id, slide["id"], knowledge, "\n\n".join(page_summaries),
                                           expected_material_hash=lecture["material_hash"])
                summaries.append("### %s\n%s" % (slide["title"], "\n\n".join(page_summaries)))
            self.store.set_summary(lecture_id, "\n\n".join(summaries), expected_material_hash=lecture["material_hash"])
            return {"lecture_id": lecture_id}
        return self.start_job("整理课堂", run, "analysis:" + str(lecture_id))


class Handler(BaseHTTPRequestHandler):
    server_version = "CanvasSynapse/" + __version__
    protocol_version = "HTTP/1.1"

    @property
    def app(self):
        return self.server.application

    def log_message(self, fmt, *args):
        # No paths, queries, request bodies, source URLs or secret values in access logs.
        pass

    def headers_common(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")

    def respond(self, value, status=200, mime="application/json; charset=utf-8", filename=None):
        body = value if isinstance(value, bytes) else json_bytes(value)
        self.send_response(status)
        self.headers_common()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % filename)
        self.end_headers()
        self.wfile.write(body)

    def check_local(self, mutate=False):
        host = self.headers.get("Host", "")
        p = urlsplit("http://" + host)
        if p.hostname not in ("127.0.0.1", "localhost", "::1") or (p.port or 80) != self.server.server_port:
            raise PermissionError("仅允许本机访问")
        origin = self.headers.get("Origin")
        if origin and origin not in ("http://" + host,):
            raise PermissionError("拒绝跨站请求")
        if mutate and self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise ValueError("请求须使用 application/json")

    def body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("无效的请求长度")
        if not 0 < length <= MAX_BODY:
            raise ValueError("请提供 JSON 请求，大小不超过 16MB")
        try:
            value = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            raise ValueError("JSON 格式无效")
        if not isinstance(value, dict):
            raise ValueError("JSON 顶层须为对象")
        return value

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_PATCH(self):
        self.dispatch("PATCH")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def dispatch(self, method):
        try:
            self.check_local(method != "GET")
            path = unquote(urlsplit(self.path).path)
            query = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
            body = self.body() if method != "GET" else {}
            self.route(method, path, query, body)
        except (BrokenPipeError, ConnectionResetError):
            return
        except PermissionError as e:
            self.respond({"error": str(e)}, 403)
        except KeyError as e:
            self.respond({"error": self.app.safe_error(e)}, 404)
        except (ValueError, TypeError) as e:
            self.respond({"error": self.app.safe_error(e)}, 400)
        except Exception:
            self.respond({"error": "请求未完成，请检查材料后重试"}, 500)

    def route(self, method, path, query, body):
        store = self.app.store
        if method == "GET":
            if path == "/api/health":
                return self.respond({"ok": True, "version": __version__, "video_storage": False})
            if path == "/api/state":
                state = store.state()
                state["settings"] = self.app.settings.public()
                state.setdefault("stats", {}).update(cache_bytes=self.app.cache_bytes(), cache_limit_bytes=CACHE_LIMIT)
                return self.respond(state)
            if path == "/api/settings":
                return self.respond(self.app.settings.public())
            if path == "/api/search":
                return self.respond({"results": store.search(query.get("q", ""), query.get("course_id"))})
            if path == "/api/chat":
                scope = query.get("scope", "lecture")
                if scope not in ("slide", "lecture", "course"):
                    raise ValueError("提问范围无效")
                return self.respond({"messages": store.messages(query.get("lecture_id", ""), scope, query.get("slide_id"))})
            if path.startswith("/api/jobs/"):
                with self.app.lock:
                    job = self.app.jobs.get(path.rsplit("/", 1)[-1])
                    return self.respond(dict(job) if job else {"error": "任务不存在，应用可能已经重启，请检查课程列表"}, 200 if job else 404)
            if path.startswith("/api/lectures/"):
                lecture = store.get_lecture(path.rsplit("/", 1)[-1])
                return self.respond(lecture if lecture else {"error": "未找到这节回放"}, 200 if lecture else 404)
            if path.startswith("/api/export/"):
                identity = path.rsplit("/", 1)[-1]
                lecture = store.get_lecture(identity)
                if not lecture:
                    raise ValueError("未找到回放")
                if query.get("format") == "json":
                    return self.respond(store.export_bundle(identity), filename="canvas-synapse-lecture.json")
                return self.respond(store.export_markdown(identity).encode(), mime="text/markdown; charset=utf-8", filename="canvas-synapse-notes.md")
            if path == "/api/import-example":
                from .demo import demo_bundle
                return self.respond(demo_bundle(), filename="canvas-synapse-example.json")
            if path == "/api/assets":
                mime, data = self.app.asset(query.get("url", ""))
                return self.respond(data, mime=mime)
            if path.startswith("/api/"):
                return self.respond({"error": "接口不存在"}, 404)
            return self.static(path)
        if method == "PUT" and path == "/api/settings":
            return self.respond(self.app.settings.update(body))
        if method == "PATCH" and path.startswith("/api/slides/"):
            return self.respond(store.update_slide(path.rsplit("/", 1)[-1], body))
        if method == "DELETE" and path.startswith("/api/lectures/"):
            store.delete_lecture(path.rsplit("/", 1)[-1])
            return self.respond({"ok": True})
        if method == "DELETE" and path == "/api/chat":
            store.clear_messages(query.get("lecture_id", ""), query.get("scope", "lecture"), query.get("slide_id"))
            return self.respond({"ok": True})
        if method == "POST":
            if path == "/api/demo":
                from .demo import demo_bundle
                lecture = store.import_bundle(demo_bundle())
                return self.respond({"lecture_id": lecture["id"]})
            if path == "/api/import":
                lecture = store.import_bundle(body.get("bundle", body))
                return self.respond({"lecture_id": lecture["id"]})
            if path == "/api/cache/clear":
                return self.respond({"ok": True, "freed_bytes": self.app.clear_cache()})
            if path == "/api/analyze":
                return self.respond({"job_id": self.app.analyze(str(body.get("lecture_id", "")))})
            if path == "/api/settings/test":
                result = llm.complete(self.app.settings.get(), [{"role": "user", "content": "请仅回复：连接成功"}])
                return self.respond({"ok": True, "message": result[:200]})
            if path == "/api/canvas/courses":
                return self.respond({"courses": self.app.canvas().courses()})
            if path == "/api/canvas/lectures":
                return self.respond({"lectures": self.app.canvas().lectures(str(body.get("course_id", "")))})
            if path == "/api/canvas/import":
                course_id, lecture_id = str(body.get("course_id", "")), str(body.get("lecture_id", ""))
                if not course_id or not lecture_id:
                    raise ValueError("请选择课程与节次")
                client = self.app.canvas()
                def run(update):
                    update(10, "读取平台字幕与课件索引")
                    bundle = client.bundle(course_id, lecture_id)
                    update(80, "对齐每页课件与老师讲稿")
                    lecture = store.import_bundle(bundle)
                    return {"lecture_id": lecture["id"]}
                return self.respond({"job_id": self.app.start_job("导入回放", run, "import:" + course_id + ":" + lecture_id)})
            if path == "/api/chat":
                return self.chat(body)
        return self.respond({"error": "接口不存在"}, 404)

    def static(self, path):
        match = re.fullmatch(r"/demo-slides/([1-6])\.svg", path)
        if match:
            from .demo import demo_slide_svg
            return self.respond(demo_slide_svg(int(match.group(1))).encode("utf-8"), mime="image/svg+xml")
        if path == "/browser-export":
            path = "/browser-export.html"
        requested = (STATIC / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
        if STATIC.resolve() not in requested.parents or not requested.is_file():
            return self.respond({"error": "页面不存在"}, 404)
        mime = mimetypes.guess_type(str(requested))[0] or "application/octet-stream"
        if mime.startswith("text/") or requested.suffix == ".js":
            mime += "; charset=utf-8"
        return self.respond(requested.read_bytes(), mime=mime)

    def chat(self, body):
        lecture_id, slide_id = str(body.get("lecture_id", "")), body.get("slide_id")
        scope = body.get("scope", "slide")
        question = body.get("message", "")
        if not isinstance(question, str) or not question.strip() or len(question) > 6000:
            raise ValueError("请输入 1–6000 字的问题")
        if scope not in ("slide", "lecture", "course"):
            raise ValueError("提问范围无效")
        config = self.app.settings.get()
        llm.check_config(config)
        store = self.app.store
        if not store.get_lecture(lecture_id):
            raise ValueError("回放不存在")
        sources = store.retrieve(question, lecture_id, scope, slide_id, budget=config["context_chars"])
        for i, source in enumerate(sources):
            source["id"] = "S" + str(i + 1)
        def source_text(s):
            kind = {"note": "个人笔记（不代表老师原话）", "transcript": "讲稿转写（可能存在识别错误）", "slide": "课件 OCR"}.get(s.get("kind"), "导入资料")
            demo = "；合成示例，非真实课堂" if s.get("is_demo") else ""
            return "[%s] %s｜类型：%s%s（%s–%s 秒）\n%s" % (s["id"], s["title"], kind, demo, s.get("start", 0), s.get("end", 0), s["text"])
        evidence = "\n\n".join(source_text(s) for s in sources)
        # Budget history as well as source evidence; the current question is never truncated.
        budget = config["context_chars"]
        if len(evidence) > budget:
            # Cut on source boundaries, never silently shorten a single source.
            kept, length = [], 0
            for source in sources:
                if length + len(source["text"]) + 200 > budget:
                    break
                kept.append(source)
                length += len(source["text"]) + 200
            sources = kept
            evidence = "\n\n".join(source_text(s) for s in sources)
        history = []
        size = len(question) + len(evidence)
        for msg in reversed(store.messages(lecture_id, scope, slide_id)[-16:]):
            if size + len(msg["content"]) > budget + 6000:
                break
            history.insert(0, {"role": msg["role"], "content": msg["content"]})
            size += len(msg["content"])
        messages = [{"role": "user", "content": "以下为检索到的部分课程原始证据：\n" + (evidence or "未检索到相关材料，请明确说明资料不足。")}] + history + [{"role": "user", "content": question}]
        self.send_response(200)
        self.headers_common()
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        def event(value):
            self.wfile.write(json_bytes(value) + b"\n")
            self.wfile.flush()
        output = []
        try:
            event({"type": "sources", "sources": sources})
            for delta in llm.stream_text(config, messages):
                output.append(delta)
                event({"type": "delta", "text": delta})
            # Only persist complete exchanges; interrupted output never becomes evidence/history.
            store.save_message(lecture_id, scope, slide_id, "user", question, [])
            store.save_message(lecture_id, scope, slide_id, "assistant", "".join(output), sources)
            event({"type": "done"})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:
            event({"type": "error", "message": self.app.safe_error(e)})


def create_server(data_dir, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.application = Application(data_dir)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description="Canvas Synapse 本地课程工作台")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default=os.getenv("SYNAPSE_DATA_DIR", str(Path.home() / ".canvas-synapse")))
    args = parser.parse_args()
    server = create_server(args.data_dir, args.port)
    print("Canvas Synapse → http://127.0.0.1:%s" % server.server_port, flush=True)
    print("仅在本机运行；按 Ctrl+C 停止。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.application.pool.shutdown(wait=False)


if __name__ == "__main__":
    main()
