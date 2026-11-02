# JSON 资料格式

所有时间统一使用**秒**，可带小数。不要把平台原始毫秒值直接填入；平台连接器和导出扩展会负责换算。

```json
{
  "schema_version": 1,
  "course": {"id": "course-001", "title": "课程名", "teacher": "老师", "term": "2026 秋"},
  "lecture": {
    "id": "lecture-001", "course_id": "course-001", "title": "第一讲",
    "date": "2026-10-27", "duration": 3307,
    "source_url": "https://oc.sjtu.edu.cn/courses/123"
  },
  "slides": [
    {"id": "page-1", "title": "课程引入", "start": 0, "end": 120,
     "image_url": "https://example.com/slide-1.jpg", "ocr": "该页课件的完整文字"},
    {"id": "page-2", "title": "第一个概念", "start": 120,
     "image_url": "", "ocr": "没有图片时仍然可以查看课件文字"}
  ],
  "transcript": [
    {"start": 0, "end": 15.4, "text": "老师的第一段转写。"},
    {"start": 118.2, "end": 125.7, "text": "这句话跨过了换页时间，会在两页都显示。"}
  ]
}
```

- `course.id` 和 `lecture.id` 用于去重，跨课程使用不同 lecture ID。相同 slide ID 会自动按课堂隔离。
- slide 的 `end` 可省略，默认使用下一页开始时间，最后一页使用课堂时长。
- `transcript` 和 `slides` 至少有一种有内容；只有转写时自动建立讲稿页。
- 课前、课后或时间空隙里的转写会关联到最近的 slide；完整原始讲稿不会因对齐而丢失。
- 图片支持公开 HTTPS 图片地址。校验后通过后端代理按需获取，不会把模型或 Canvas 凭证发送到图片服务器。签名图片地址过期时，需要重新同步。
- 不支持把任意本地文件路径作为 `image_url`。离线示例使用本程序内置的 `/demo-slides/*.svg`。
- 可选 `knowledge: [{"title":"概念","detail":"解释"}]`、`notes`、`bookmarked`、`reviewed`、`summary` 用于资料迁移。
- 可选 `lecture.warnings` 或顶层 `warnings` 记录缺失材料信息。`is_demo: true` 用于明确标记合成示例。
- 单次 HTTP 导入上限 16MB；超出时明确拒绝，不会静默截断。
- 导出的 JSON 可直接重新导入，或使用规范化的 `course` / `lecture` / `slides` / `transcript` 资料包。

JSON 中不要包含 Token、Cookie、API Key 或其他登录凭证。图片与课堂来源 URL 可能带临时签名，导出资料按个人学习数据保存即可。
