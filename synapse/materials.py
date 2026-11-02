"""Lossless course material normalization, slide alignment and local retrieval.

All times in the public bundle format are seconds. Transcript text is retained
verbatim apart from surrounding whitespace; summaries never replace evidence.
"""
import hashlib
import json
import math
import re
from bisect import bisect_left, bisect_right
from collections import Counter


MAX_TEXT = 2_000_000
MAX_SEGMENTS = 50_000
MAX_SLIDES = 5_000
MAX_ALIGNMENT_LINKS = 100_000


def _text(value, name, limit=MAX_TEXT):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("%s 必须是文字" % name)
    if len(value) > limit:
        raise ValueError("%s 过长（最多 %d 字符）；请拆分导入，内容未被截断" % (name, limit))
    return value.strip()


def _time(value, name):
    if isinstance(value, bool):
        raise ValueError("%s 必须是以秒为单位的非负数字" % name)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s 必须是以秒为单位的非负数字" % name)
    if not math.isfinite(number) or number < 0:
        raise ValueError("%s 必须是以秒为单位的非负数字" % name)
    return round(number, 3)


def _id(value, fallback):
    result = str(value).strip() if value is not None else ""
    result = result or fallback
    if len(result) > 256 or any(ord(c) < 32 for c in result):
        raise ValueError("资料 ID 无效或过长")
    return result


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def normalize_knowledge(value):
    if value is None:
        return []
    if isinstance(value, str):
        value = [{"title": "知识点", "detail": value}]
    if not isinstance(value, list) or len(value) > 1000:
        raise ValueError("知识点必须是最多 1000 项的列表")
    output = []
    for item in value:
        if isinstance(item, str):
            item = {"title": item, "detail": ""}
        if not isinstance(item, dict):
            raise ValueError("知识点格式无效")
        title = _text(item.get("title", "知识点"), "知识点标题", 1000)
        detail = _text(item.get("detail", item.get("content", "")), "知识点正文")
        result = {"title": title or "知识点", "detail": detail}
        if item.get("sources"):
            if not isinstance(item["sources"], list):
                raise ValueError("知识点来源必须是列表")
            result["sources"] = item["sources"]
        output.append(result)
    return output


def normalize_bundle(bundle):
    """Validate a JSON bundle and return a complete aligned lecture object."""
    if not isinstance(bundle, dict):
        raise ValueError("导入内容必须是 JSON 对象")
    course = bundle.get("course") or {}
    # A full workspace JSON export is also a valid import. The explicit bundle
    # form remains useful for browser exports and platform adapters.
    lecture = bundle.get("lecture") or (bundle if "slides" in bundle and "id" in bundle else {})
    if not isinstance(course, dict) or not isinstance(lecture, dict):
        raise ValueError("course 和 lecture 必须是对象")
    title = _text(course.get("title", "导入课程"), "课程名", 1000) or "导入课程"
    term = _text(course.get("term", ""), "学期", 256)
    course_id = _id(course.get("id"), "course-" + _hash([title, term])[:16])
    normalized_course = {
        "id": course_id, "title": title,
        "teacher": _text(course.get("teacher", ""), "教师", 1000), "term": term,
    }
    lecture_title = _text(lecture.get("title", "导入课堂"), "课堂名", 1000) or "导入课堂"
    date = _text(lecture.get("date", ""), "课堂日期", 256)
    lecture_id = _id(lecture.get("id"), "lecture-" + _hash([course_id, lecture_title, date])[:20])
    if lecture.get("course_id") is not None and str(lecture["course_id"]) != course_id:
        raise ValueError("lecture.course_id 与 course.id 不一致")
    duration = _time(lecture.get("duration", 0), "课堂时长")
    raw_transcript = bundle.get("transcript", lecture.get("transcript", []))
    raw_slides = bundle.get("slides", lecture.get("slides", []))
    if not isinstance(raw_transcript, list) or len(raw_transcript) > MAX_SEGMENTS:
        raise ValueError("transcript 必须是最多 %d 段的列表" % MAX_SEGMENTS)
    if not isinstance(raw_slides, list) or len(raw_slides) > MAX_SLIDES:
        raise ValueError("slides 必须是最多 %d 页的列表" % MAX_SLIDES)
    transcript = []
    total_chars = 0
    for position, segment in enumerate(raw_transcript):
        if not isinstance(segment, dict):
            raise ValueError("第 %d 段转写格式无效" % (position + 1))
        start = _time(segment.get("start", 0), "转写开始时间")
        end = _time(segment.get("end", start), "转写结束时间")
        if end < start:
            raise ValueError("第 %d 段转写结束时间早于开始时间" % (position + 1))
        text = _text(segment.get("text", ""), "转写正文")
        total_chars += len(text)
        if total_chars > 20_000_000:
            raise ValueError("本节转写超过 2000 万字符，请分节导入；内容未被截断")
        transcript.append({"id": "segment-%s-%d" % (lecture_id, position + 1),
                           "start": start, "end": end, "text": text})
        duration = max(duration, end)
    transcript.sort(key=lambda item: (item["start"], item["end"]))
    for position, segment in enumerate(transcript):
        segment["id"] = "segment-%s-%d" % (lecture_id, position + 1)
    slides = []
    for position, item in enumerate(raw_slides):
        if not isinstance(item, dict):
            raise ValueError("第 %d 页 slide 格式无效" % (position + 1))
        start = _time(item.get("start", 0), "幻灯片开始时间")
        end = _time(item["end"], "幻灯片结束时间") if item.get("end") is not None else None
        if end is not None and end < start:
            raise ValueError("幻灯片结束时间早于开始时间")
        source_id = _id(item.get("source_id", item.get("id")), str(position + 1))
        # Namespace arbitrary external IDs so importing another lecture cannot
        # overwrite this slide's notes or study progress.
        slide_id = "slide-" + _hash([lecture_id, source_id])[:24]
        ocr = _text(item.get("ocr", item.get("text", "")), "课件文字")
        slide_title = _text(item.get("title", ""), "幻灯片标题", 1000)
        if not slide_title:
            first_line = next((line.strip() for line in ocr.splitlines() if line.strip()), "")
            slide_title = first_line[:100] or "Slide %02d" % (position + 1)
        image_url = _text(item.get("image_url", ""), "幻灯片图片地址", 8000)
        notes = _text(item.get("notes", ""), "个人笔记")
        for flag in ("bookmarked", "reviewed"):
            if flag in item and not isinstance(item[flag], bool):
                raise ValueError("%s 必须是布尔值" % flag)
        slides.append({"id": slide_id, "source_id": source_id, "index": position + 1,
                       "title": slide_title, "start": start, "end": end,
                       "image_url": image_url, "ocr": ocr,
                       "knowledge": normalize_knowledge(item.get("knowledge")),
                       "summary": _text(item.get("summary", ""), "本页总结"),
                       "notes": notes, "bookmarked": item.get("bookmarked", False),
                       "reviewed": item.get("reviewed", False)})
        duration = max(duration, start, end or 0)
    if len({item["id"] for item in slides}) != len(slides):
        raise ValueError("同一课堂中存在重复的 slide ID")
    if not slides and not transcript:
        raise ValueError("没有可导入的幻灯片或转写内容")
    if not slides:
        slides = [{"id": "slide-" + _hash([lecture_id, "transcript"])[:24],
                   "source_id": "transcript", "index": 1, "title": "课堂讲稿",
                   "start": 0, "end": duration, "image_url": "", "ocr": "",
                   "knowledge": [], "summary": "", "notes": "", "bookmarked": False, "reviewed": False}]
    slides.sort(key=lambda item: (item["start"], item["index"]))
    for position, slide in enumerate(slides):
        slide["index"] = position + 1
        if slide["end"] is None:
            slide["end"] = slides[position + 1]["start"] if position + 1 < len(slides) else duration
        slide["transcript"] = []
    # Explicit gaps and intro/outro segments are attached to the nearest slide.
    # Spanning sentences may appear on both pages, but the full transcript is
    # stored once and exported once. Shared boundaries use [start, end).
    starts = [slide["start"] for slide in slides]
    ends = [slide["end"] for slide in slides]
    monotone_ends = all(a <= b for a, b in zip(ends, ends[1:]))
    alignment_links = 0
    overlap_checks = 0
    for segment in transcript:
        left = bisect_right(ends, segment["start"]) if monotone_ends else 0
        if segment["end"] == segment["start"]:
            right = bisect_right(starts, segment["start"])
            candidates = slides[left:right]
            matches = [s for s in candidates if s["start"] <= segment["start"] < s["end"]]
        else:
            right = bisect_left(starts, segment["end"])
            candidates = slides[left:right]
            matches = [s for s in candidates if segment["start"] < s["end"] and segment["end"] > s["start"]]
        overlap_checks += len(candidates)
        if overlap_checks > 20_000_000:
            raise ValueError("课件时间范围重叠过于复杂，请校对时间或分节导入；内容未被截断")
        if not matches:
            nearest = max(0, bisect_right(starts, segment["start"]) - 1)
            matches = [slides[nearest]]
        alignment_links += len(matches)
        if alignment_links > MAX_ALIGNMENT_LINKS:
            raise ValueError("跨页转写的重复对齐过多，请校对时间或分节导入；内容未被截断")
        for slide in matches:
            slide["transcript"].append(dict(segment))
    normalized = {
        "id": lecture_id, "course_id": course_id, "course_title": title,
        "title": lecture_title, "date": date, "duration": duration,
        "source_url": _text(lecture.get("source_url", ""), "课堂来源地址", 8000),
        "summary": _text(lecture.get("summary", bundle.get("summary", "")), "课堂概要"),
        "is_demo": bool(lecture.get("is_demo", bundle.get("is_demo", False))),
        "slides": slides, "transcript": transcript,
        "course": normalized_course,
    }
    warnings = list(bundle.get("warnings") or []) if isinstance(bundle.get("warnings", []), list) else None
    lecture_warnings = lecture.get("warnings", [])
    if warnings is None or not isinstance(lecture_warnings, list) or len(warnings) + len(lecture_warnings) > 200:
        raise ValueError("warnings 必须是最多 200 项的列表")
    warnings.extend(lecture_warnings)
    normalized["warnings"] = list(dict.fromkeys(_text(w, "材料提示", 500) for w in warnings))
    provenance = lecture.get("provenance", bundle.get("provenance"))
    if provenance is None:
        provenance = {"kind": "demo" if normalized["is_demo"] else "import",
                      "label": "合成示例" if normalized["is_demo"] else "导入的课程材料"}
    if not isinstance(provenance, (dict, str)) or len(json.dumps(provenance, ensure_ascii=False)) > 8000:
        raise ValueError("资料来源说明格式无效或过长")
    normalized["provenance"] = provenance
    normalized["material_hash"] = _hash({"course_title": title, "lecture_title": lecture_title,
        "transcript": transcript,
        "slides": [{k: s[k] for k in ("id", "title", "start", "end", "ocr", "image_url")} for s in slides]})
    return normalized


def timestamp(seconds):
    number = max(0, int(float(seconds or 0)))
    hours, rem = divmod(number, 3600)
    minutes, secs = divmod(rem, 60)
    return "%d:%02d:%02d" % (hours, minutes, secs) if hours else "%02d:%02d" % (minutes, secs)


def tokenize(text):
    """English identifiers and Chinese unigrams/bigrams for small local corpora."""
    text = (text or "").lower()
    terms = re.findall(r"[a-z0-9_]+", text)
    for run in re.findall(r"[\u3400-\u9fff]+", text):
        terms.extend(run)
        terms.extend(run[i:i + 2] for i in range(len(run) - 1))
    return Counter(terms)


def sources_for(lecture, slide_id=None):
    """Create bounded evidence blocks without dropping any source material."""
    output = []
    slides = lecture.get("slides", [])
    for slide in slides:
        if slide_id is not None and slide["id"] != slide_id:
            continue
        base = {"lecture_id": lecture["id"], "slide_id": slide["id"],
                "course_id": lecture["course_id"], "is_demo": bool(lecture.get("is_demo")),
                "provenance": lecture.get("provenance", {}),
                "title": "%s · 第 %d 页 · %s" % (lecture["title"], slide["index"], slide["title"]),
                "start": slide["start"], "end": slide["end"]}
        if slide.get("ocr"):
            # Split huge slides on paragraphs; every character remains in the
            # local store even when only relevant blocks fit a model request.
            for index, part in enumerate(_evidence_parts(slide["ocr"])):
                output.append(dict(base, id="%s-ocr-%d" % (slide["id"], index + 1),
                                   text=part, kind="slide"))
        if slide.get("notes"):
            for index, part in enumerate(_evidence_parts(slide["notes"])):
                output.append(dict(base, id="%s-note-%d" % (slide["id"], index + 1),
                                   text=part, kind="note"))
        segments = slide.get("transcript", [])
        # Group adjacent sentences into coherent, timestamped evidence.
        group = []
        length = 0
        for segment in segments:
            if not segment.get("text"):
                continue
            if group and (length + len(segment["text"]) > 1600 or segment["start"] - group[0]["start"] > 120):
                output.extend(_transcript_sources(base, group))
                group, length = [], 0
            group.append(segment)
            length += len(segment["text"])
        if group:
            output.extend(_transcript_sources(base, group))
    return output


def _evidence_parts(text, size=1800):
    # This divides evidence, it never truncates or mutates stored original text.
    parts = []
    rest = text
    while len(rest) > size:
        boundary = max(rest.rfind("\n", 0, size), rest.rfind("。", 0, size))
        cut = boundary + 1 if boundary > size // 2 else size
        parts.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        parts.append(rest)
    return parts


def _transcript_sources(base, segments):
    body = "\n".join("[%s–%s] %s" % (timestamp(s["start"]), timestamp(s["end"]), s["text"]) for s in segments)
    result = []
    first_id = str(segments[0].get("id", segments[0]["start"]))
    for index, part in enumerate(_evidence_parts(body)):
        result.append(dict(base, id="%s-transcript-%s-%d" % (base["slide_id"], first_id, index + 1),
                           text=part, kind="transcript", start=segments[0]["start"], end=segments[-1]["end"]))
    return result


def retrieve(lectures, query, slide_id=None, limit=8, budget=24000):
    """Retrieve lexical evidence for a slide, lecture or course; no LLM needed.

    Returned sources fit the requested character budget as whole blocks. A
    selected slide includes all available blocks up to this explicit budget;
    source originals remain available regardless of request limits.
    """
    if isinstance(lectures, dict):
        lectures = [lectures]
    query_terms = tokenize(query)
    sources = [source for lecture in lectures for source in sources_for(lecture, slide_id)]
    if not sources:
        return []
    doc_frequency = Counter()
    term_sets = []
    for source in sources:
        terms = tokenize(source["text"])
        term_sets.append(terms)
        doc_frequency.update(terms.keys())
    scored = []
    for position, (source, terms) in enumerate(zip(sources, term_sets)):
        title_terms = tokenize(source["title"])
        score = 0.0
        for token, frequency in query_terms.items():
            idf = math.log(1 + (len(sources) + 1) / (doc_frequency[token] + 1))
            weight = 1.6 if len(token) > 1 else 0.4
            score += min(frequency, 2) * idf * weight * (min(terms[token], 3) + 1.8 * min(title_terms[token], 1))
        if query and query.lower() in source["text"].lower():
            score += 8
        score /= 1 + len(source["text"]) / 6000
        scored.append((score, position, source))
    # Stable ranking makes the exact same question reproducible offline.
    scored.sort(key=lambda row: (-row[0], row[1]))
    selected, total = [], 0
    # With no lexical match, return a transparent representative selection;
    # the caller must still instruct the model not to invent unsupported facts.
    for score, position, source in scored:
        size = len(source["text"]) + len(source["title"]) + 120
        if total + size > budget:
            continue
        selected.append(dict(source, score=round(score, 3)))
        total += size
        if len(selected) >= max(1, limit):
            break
    return selected
