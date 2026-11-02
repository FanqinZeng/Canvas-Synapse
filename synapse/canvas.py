"""Read SJTU course slides and transcripts without fetching video.

The LTI/resource API protocol is based on the MIT-licensed CanvasKit project
(Copyright 2026 ZHS-XER). See THIRD_PARTY_NOTICES.md. Only the authenticated
user's Canvas course context is used. The platform's private API may change.
"""
from __future__ import annotations

import http.cookiejar
import json
import math
import re
import threading
import time
from datetime import datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener


CANVAS_BASE = "https://oc.sjtu.edu.cn"
RESOURCE_BASE = "https://v.sjtu.edu.cn/jy-application-resourcemanage"
RESOURCE_UI = "https://v.sjtu.edu.cn/jy-application-resourcemanage-ui/"
VIDEO_TOOL_ID = 8329
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
USER_AGENT = "Canvas-Synapse/0.1 (+https://github.com/FanqinZeng/Canvas-Synapse)"


class CanvasError(ValueError):
    """An actionable import failure, without credentials or response bodies."""


def _school_url(url, canvas_only=False):
    """Never send an LTI form or credentials outside SJTU over HTTPS."""
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        valid_host = host == "oc.sjtu.edu.cn" if canvas_only else (
            host == "sjtu.edu.cn" or host.endswith(".sjtu.edu.cn")
        )
        if (parsed.scheme != "https" or not valid_host or parsed.username
                or parsed.password or parsed.port not in (None, 443)):
            raise ValueError()
    except ValueError:
        raise CanvasError("学校接口返回了不受支持的地址，已停止请求以保护凭据。")
    return url


def _number(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else default
    except (ValueError, TypeError):
        return default


def _remote_id(value):
    value = str(value).split(":")[-1]
    if not value.isdecimal() or len(value) > 20 or int(value) <= 0:
        raise CanvasError("课程或节次编号无效，请重新获取列表。")
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _Form(HTMLParser):
    """Read the first LTI auto-submit form, including its hidden inputs."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.action = None
        self.method = "GET"
        self.fields = {}
        self.inside = False
        self.done = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and not self.done and not self.inside:
            self.inside = True
            self.action = attrs.get("action") or ""
            self.method = (attrs.get("method") or "GET").upper()
        elif tag == "input" and self.inside and attrs.get("name"):
            self.fields[attrs["name"]] = attrs.get("value") or ""

    def handle_endtag(self, tag):
        if tag == "form" and self.inside:
            self.inside = False
            self.done = True


def parse_form(html):
    form = _Form()
    form.feed(html)
    if form.action is None:
        return None
    if form.method not in ("GET", "POST"):
        raise CanvasError("学校登录表单使用了不受支持的方法。")
    return form.action, form.method, form.fields


def jwt_from_url(url):
    parsed = urlsplit(url)
    for query in (parsed.query, parsed.fragment.split("?", 1)[-1]):
        token = parse_qs(query).get("jwt_token", [])
        if token:
            return token[0]
    return None


def _next_link(header):
    for part in (header or "").split(","):
        match = re.match(r'\s*<([^>]+)>;\s*rel="next"', part)
        if match:
            return match.group(1)
    return None


def _api_data(payload):
    if not isinstance(payload, dict):
        raise CanvasError("课堂平台返回的数据格式不正确，请稍后重试。")
    if payload.get("ok") is False or payload.get("dataOk") is False:
        raise CanvasError("课堂平台拒绝了请求，请检查课程权限或重新连接。")
    if payload.get("code") in (401, 403, "401", "403"):
        raise CanvasError("课堂平台登录已失效，请重新连接 Canvas。")
    return payload.get("data")


def parse_transcript(data):
    """SJTU subtitle bg/ed are milliseconds; output seconds everywhere."""
    data = data or {}
    rows = data.get("beforeAssemblyList") or []
    if not any(str(row.get("res") or "").strip() for row in rows):
        rows = data.get("afterAssemblyList") or []
    output = []
    for row in rows:
        text = str(row.get("res") or "").strip()
        if not text:
            continue
        start = _number(row.get("bg")) / 1000.0
        end = max(start, _number(row.get("ed"), start * 1000) / 1000.0)
        output.append({"start": start, "end": end, "text": text})
    return sorted(output, key=lambda item: (item["start"], item["end"]))


def parse_slides(data):
    """imageSeekTime is already seconds (unlike subtitle timestamps)."""
    output = []
    for row in (data or {}).get("docList") or []:
        if row.get("showFlag") is False:
            continue
        start = _number(row.get("imageSeekTime"))
        ocr = str(row.get("ocrText") or "").strip()
        keywords = [str(word) for word in row.get("textKeywordList") or [] if word]
        image = str(row.get("imageUrl") or "")
        if image.startswith("//"):
            image = "https:" + image
        elif image.startswith("/"):
            image = urljoin(RESOURCE_UI, image)
        if image:
            try:
                parsed = urlsplit(image)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                    image = ""
            except ValueError:
                image = ""
        lines = [line.strip() for line in ocr.splitlines() if line.strip()]
        title = (lines[0] if lines else " · ".join(keywords[:4]))[:160]
        output.append({"start": start, "title": title, "image_url": image,
                       "ocr": ocr, "keywords": keywords})
    output.sort(key=lambda item: item["start"])
    for i, slide in enumerate(output):
        slide["index"] = i + 1
        slide["title"] = slide["title"] or "课堂画面 %s" % (i + 1)
        if i + 1 < len(output):
            slide["end"] = output[i + 1]["start"]
    return output


def _duration(begin, end):
    try:
        return max(0.0, (datetime.fromisoformat(end) - datetime.fromisoformat(begin)).total_seconds())
    except (ValueError, TypeError):
        return 0.0


def parse_lectures(records, course_id):
    output = []
    for row in sorted(records, key=lambda item: item.get("courBeginTime") or ""):
        if not row.get("id"):
            continue
        begin, end = row.get("courBeginTime") or "", row.get("courEndTime") or ""
        subject = row.get("subjName") or row.get("teclName") or "课程回放"
        week = row.get("weekNumber") or row.get("weekNo")
        period = row.get("letiNumber")
        title = "%s %s%s" % (subject, "第%s周 " % week if week else "",
                               "第%s节" % period if period else begin[11:16])
        teachers = row.get("teclTeacNames") or row.get("teacNames") or []
        teacher = row.get("tecName") or (", ".join(teachers) if isinstance(teachers, list) else teachers)
        output.append({"id": str(row["id"]), "course_id": str(course_id),
                       "title": title.strip(), "date": begin[:10], "begin": begin,
                       "duration": _duration(begin, end), "teacher": str(teacher),
                       "classroom": row.get("clroName") or "",
                       "available": row.get("vodClickEnable") is not False,
                       "source_url": "%s/courses/%s/external_tools/%s" % (CANVAS_BASE, course_id, VIDEO_TOOL_ID)})
    return output


class CanvasClient:
    """One ephemeral client per import job; credentials are never in a bundle.

    ``transport`` may be injected in tests. It receives
    (method, url, headers, bytes_or_none) and returns (status, headers, bytes).
    """
    def __init__(self, token, base=CANVAS_BASE, timeout=30, transport=None):
        if str(base).rstrip("/") != CANVAS_BASE:
            raise CanvasError("目前支持交大本部 Canvas：https://oc.sjtu.edu.cn。")
        if not isinstance(token, str) or not token.strip():
            raise CanvasError("请先在设置中保存 Canvas Access Token。")
        if any(character in token for character in "\r\n"):
            raise CanvasError("Canvas Token 格式不正确。")
        self.token, self.base, self.timeout = token.strip(), CANVAS_BASE, timeout
        self._transport = transport
        self._opener = build_opener(_NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self._tokens = {}
        self._class_ids = {}
        self._lock = threading.Lock()

    def _request(self, method, url, headers=None, body=None):
        _school_url(url)
        headers = dict(headers or {})
        headers.setdefault("User-Agent", USER_AGENT)
        host = urlsplit(url).hostname
        if "Authorization" in headers and (host != "oc.sjtu.edu.cn" or not urlsplit(url).path.startswith("/api/v1/")):
            raise CanvasError("拒绝向非 Canvas API 地址发送访问令牌。")
        if "jwt-token" in headers and host != "v.sjtu.edu.cn":
            raise CanvasError("拒绝向其他站点发送课堂平台凭据。")
        if self._transport:
            status, response_headers, content = self._transport(method, url, headers, body)
            if len(content) > MAX_RESPONSE_BYTES:
                raise CanvasError("学校接口返回的数据过大，请缩小导入范围。")
            return status, {key.lower(): value for key, value in response_headers.items()}, content
        request = Request(url, data=body, headers=headers, method=method)
        try:
            response = self._opener.open(request, timeout=self.timeout)
        except HTTPError as error:
            response = error
        except (URLError, TimeoutError, OSError):
            raise CanvasError("无法连接学校接口，请确认校园网络/VPN和网络连接。") from None
        with response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise CanvasError("学校接口返回的数据过大，请缩小导入范围。")
            return response.code, {key.lower(): value for key, value in response.headers.items()}, content

    @staticmethod
    def _raise_status(status):
        if status in (401, 403):
            raise CanvasError("访问被拒绝（HTTP %s），请检查 Canvas Token 和课程权限。" % status)
        if status == 404:
            raise CanvasError("学校接口或材料不存在（HTTP 404），平台可能已改版。")
        if status >= 400:
            raise CanvasError("学校接口暂时不可用（HTTP %s），请稍后重试。" % status)
        if status in (301, 302, 303, 307, 308):
            raise CanvasError("学校 API 跳转至登录页，请更新 Canvas Token。")

    @staticmethod
    def _json(content):
        try:
            return json.loads(content.decode("utf-8-sig"))
        except (ValueError, UnicodeError):
            raise CanvasError("学校接口没有返回 JSON，可能需要重新登录或平台已改版。") from None

    def _canvas(self, path, params=None):
        url = urljoin(self.base, path)
        _school_url(url, canvas_only=True)
        if params:
            url += ("&" if "?" in url else "?") + urlencode(params, doseq=True)
        for attempt in range(3):
            status, headers, content = self._request("GET", url, {"Authorization": "Bearer " + self.token,
                                                                   "Accept": "application/json"})
            if status != 429 or attempt == 2:
                break
            time.sleep(0.5 * 2 ** attempt)
        self._raise_status(status)
        return self._json(content), headers

    def _paginate(self, path, params=None):
        url = path
        params = {"per_page": 100, **(params or {})}
        rows = []
        seen = set()
        for _ in range(100):
            if url in seen:
                raise CanvasError("Canvas 分页返回了重复地址，已停止导入。")
            seen.add(url)
            data, headers = self._canvas(url, params)
            if not isinstance(data, list):
                raise CanvasError("Canvas 列表格式不正确。")
            rows.extend(data)
            url = _next_link(headers.get("link"))
            if not url:
                return rows
            _school_url(url, canvas_only=True)
            params = None
        raise CanvasError("Canvas 分页超过限制，请缩小查询范围。")

    def courses(self):
        rows = self._paginate("/api/v1/courses", {"enrollment_state": "active", "include[]": "term"})
        return [{"id": str(row["id"]), "title": row.get("name") or row.get("course_code") or "未命名课程",
                 "teacher": "", "term": (row.get("term") or {}).get("name") or ""}
                for row in rows if row.get("id") and row.get("name")]

    def _jwt(self, course_id):
        course_id = _remote_id(course_id)
        with self._lock:
            if course_id in self._tokens:
                return self._tokens[course_id]
            data, _ = self._canvas("/api/v1/courses/%s/external_tools/sessionless_launch" % course_id,
                                   {"id": VIDEO_TOOL_ID})
            if not isinstance(data, dict) or not data.get("url"):
                raise CanvasError("该课程没有可用的课堂视频入口。")
            url, method, fields = data["url"], "GET", None
            for _ in range(20):
                _school_url(url)
                token = jwt_from_url(url)
                if token:
                    if urlsplit(url).hostname != "v.sjtu.edu.cn":
                        raise CanvasError("课堂登录凭据的接收地址不正确。")
                    self._tokens[course_id] = token
                    return token
                headers = {"Referer": self.base + "/"}
                body = None
                if fields is not None:
                    encoded = urlencode(fields).encode("utf-8")
                    if method == "GET":
                        url += ("&" if "?" in url else "?") + encoded.decode("ascii")
                    else:
                        body = encoded
                        headers["Content-Type"] = "application/x-www-form-urlencoded"
                status, response_headers, content = self._request(method, url, headers, body)
                if status in (301, 302, 303, 307, 308):
                    location = response_headers.get("location")
                    if not location:
                        raise CanvasError("学校登录跳转缺少目标地址。")
                    url = urljoin(url, location)
                    if status in (301, 302, 303):
                        method, fields = "GET", None
                    continue
                self._raise_status(status)
                form = parse_form(content.decode("utf-8", errors="replace"))
                if form is None:
                    raise CanvasError("课堂登录未完成；请确认课程已开放新版课堂视频。")
                action, method, fields = form
                url = urljoin(url, action)
            raise CanvasError("学校登录跳转次数过多，请稍后重试。")

    def _resource(self, course_id, path, params=None, retry=True):
        query = "?" + urlencode(params or {}) if params else ""
        url = RESOURCE_BASE + path + query
        status, _, content = self._request("GET", url, {"jwt-token": self._jwt(course_id),
                                                         "Referer": RESOURCE_UI, "Accept": "application/json"})
        if status == 401 and retry:
            self._tokens.pop(_remote_id(course_id), None)
            return self._resource(course_id, path, params, retry=False)
        self._raise_status(status)
        return _api_data(self._json(content))

    def lectures(self, course_id):
        course_id = _remote_id(course_id)
        if course_id not in self._class_ids:
            launch = self._resource(course_id, "/lms/launch-context") or {}
            teaching_id = (launch.get("canvasRecord") or {}).get("teachingClassId")
            if not teaching_id:
                raise CanvasError("平台未返回课程上下文，请检查课程视频权限。")
            self._class_ids[course_id] = teaching_id
        records = []
        for page in range(1, 101):
            data = self._resource(course_id, "/v1/subject_vod_list_new", {
                "page.pageIndex": page, "page.pageSize": 1000, "teclIds": self._class_ids[course_id],
                "page.orders[0].asc": "false", "page.orders[0].field": "courBeginTime",
                "schoolOpenStatusFlag": "false"}) or {}
            rows = data.get("records") or []
            records.extend(rows)
            total = _number(data.get("total"))
            if len(rows) < 1000 or total and len(records) >= total:
                return parse_lectures(records, course_id)
        raise CanvasError("课堂列表过大，请联系项目维护者调整分页限制。")

    def bundle(self, course_id, lecture_id):
        course_id, lecture_id = _remote_id(course_id), _remote_id(lecture_id)
        # Membership is checked against this course's actual list. A JWT for one
        # course must never be reused to import an arbitrary recording ID.
        found = next((item for item in self.lectures(course_id) if item["id"] == lecture_id), None)
        if found is None:
            raise CanvasError("这节回放不属于所选课程，或当前账号无访问权限。")
        if not found["available"]:
            raise CanvasError("该节回放尚未开放点播。")
        course_data, _ = self._canvas("/api/v1/courses/%s" % course_id)
        transcript_data = self._resource(course_id, "/v1/course/ai/translate/%s" % lecture_id,
                                         {"useOriginal": "true"})
        transcript = parse_transcript(transcript_data)
        if not transcript:
            transcript = parse_transcript(self._resource(course_id, "/v1/course/ai/translate/%s" % lecture_id,
                                                          {"useOriginal": "false"}))
        slides = parse_slides(self._resource(course_id, "/v1/course/ai/ppt", {"courseId": lecture_id}))
        warnings = []
        if not transcript:
            warnings.append("平台尚无可用讲稿。已保留 slides；本应用不会自动下载视频或编造讲稿。")
        if not slides:
            warnings.append("平台尚无 PPT 截图。已保留讲稿，可稍后重新导入。")
        if not slides and not transcript:
            raise CanvasError("这一节尚无平台字幕或 PPT 截图，请稍后重试。未下载视频。")
        duration = max([found["duration"]] + [line["end"] for line in transcript] +
                       [slide["start"] for slide in slides])
        if slides:
            slides[-1]["end"] = duration
        namespaced = "sjtu:%s:%s" % (course_id, lecture_id)
        for i, slide in enumerate(slides):
            slide["id"] = "%s:slide:%s" % (namespaced, i + 1)
        return {"version": 1,
                "course": {"id": "sjtu:" + course_id, "title": course_data.get("name") or found["title"],
                           "teacher": found["teacher"], "term": (course_data.get("term") or {}).get("name") or ""},
                "lecture": {"id": namespaced, "course_id": "sjtu:" + course_id,
                            "title": found["title"], "date": found["date"], "duration": duration,
                            "source_url": found["source_url"], "warnings": warnings},
                "slides": slides, "transcript": transcript, "warnings": warnings}

    def image_headers(self, url):
        # Image CDNs never receive Canvas bearer/JWT/cookies. Most platform
        # image URLs are signed; Referer is sufficient when one is required.
        return {"Referer": RESOURCE_UI, "User-Agent": USER_AGENT}
