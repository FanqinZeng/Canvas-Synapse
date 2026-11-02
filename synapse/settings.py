"""Private local configuration. Never return credentials to the browser."""
import json
import os
import threading
from pathlib import Path
from urllib.parse import urlsplit

DEFAULTS = {
    "provider": "glm", "protocol": "chat", "api_base": "https://open.bigmodel.cn/api/paas/v4",
    "model": "", "api_key": "", "canvas_base": "https://oc.sjtu.edu.cn", "canvas_token": "",
    "context_chars": 24000, "send_images": False,
}


class Settings:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / "settings.json"
        self.lock = threading.RLock()
        self.values = dict(DEFAULTS)
        if self.path.exists():
            self.values.update(json.loads(self.path.read_text("utf-8")))
        for env, key in [("SYNAPSE_API_KEY", "api_key"), ("SYNAPSE_API_BASE", "api_base"),
                         ("SYNAPSE_MODEL", "model"), ("SYNAPSE_CANVAS_TOKEN", "canvas_token")]:
            if os.getenv(env):
                self.values[key] = os.environ[env]

    def get(self):
        with self.lock:
            return dict(self.values)

    def public(self):
        values = self.get()
        for key in ("api_key", "canvas_token"):
            values[key + "_set"] = bool(values.pop(key, ""))
        return values

    def update(self, changes):
        if not isinstance(changes, dict):
            raise ValueError("设置必须为 JSON 对象")
        with self.lock:
            next_values = dict(self.values)
            for key in DEFAULTS:
                if key in changes:
                    value = changes[key]
                    if key in ("api_key", "canvas_token") and value == "":
                        continue  # Empty password fields preserve existing credentials.
                    next_values[key] = value
            for key in ("api_key", "canvas_token"):
                if changes.get("clear_" + key) is True:
                    next_values[key] = ""
            if next_values["provider"] not in ("glm", "openai", "compatible"):
                raise ValueError("未知模型服务")
            if next_values["protocol"] not in ("chat", "responses"):
                raise ValueError("协议应为 chat 或 responses")
            for key in ("api_key", "canvas_token", "model", "api_base", "canvas_base"):
                if not isinstance(next_values[key], str) or len(next_values[key]) > 8192:
                    raise ValueError("设置字段无效：" + key)
                next_values[key] = next_values[key].strip()
            for key in ("api_key", "canvas_token"):
                if any(ord(c) < 33 or ord(c) > 126 for c in next_values[key]):
                    raise ValueError("凭证须为可打印的 ASCII 字符，请检查是否包含空格或换行")
            base = urlsplit(next_values["api_base"])
            if base.username or base.password or base.query or base.fragment or not base.hostname:
                raise ValueError("模型地址必须是完整 Base URL，不含凭证或查询参数")
            if base.scheme != "https" and not (base.scheme == "http" and base.hostname in ("localhost", "127.0.0.1", "::1")):
                raise ValueError("模型接口须使用 HTTPS，本机接口可使用 HTTP")
            previous = urlsplit(self.values["api_base"])
            old_origin = (previous.scheme, previous.hostname, previous.port or (443 if previous.scheme == "https" else 80))
            new_origin = (base.scheme, base.hostname, base.port or (443 if base.scheme == "https" else 80))
            if old_origin != new_origin and not changes.get("api_key", "").strip():
                # A provider change must never silently disclose the old provider's key.
                next_values["api_key"] = ""
            if next_values["canvas_base"].rstrip("/") != "https://oc.sjtu.edu.cn":
                raise ValueError("当前支持上海交大本部 Canvas：https://oc.sjtu.edu.cn")
            chars = next_values["context_chars"]
            if isinstance(chars, bool) or not isinstance(chars, int) or not 4000 <= chars <= 160000:
                raise ValueError("上下文字符预算应为 4000–160000")
            if not isinstance(next_values["send_images"], bool):
                raise ValueError("send_images 必须为布尔值")
            tmp = self.path.with_suffix(".tmp")
            fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(next_values, f, ensure_ascii=False, indent=2)
            os.replace(str(tmp), str(self.path))
            os.chmod(str(self.path), 0o600)
            self.values = next_values
        return self.public()
