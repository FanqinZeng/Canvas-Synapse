"""Bounded network operations with TLS and redirect credential isolation."""
import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(url, local=False):
    p = urlsplit(url)
    if not p.hostname or p.username or p.password or p.fragment:
        raise ValueError("网络地址格式无效")
    loopback = p.hostname in ("localhost", "127.0.0.1", "::1")
    if p.scheme != "https" and not (local and loopback and p.scheme == "http"):
        raise ValueError("仅支持 HTTPS（本机模型可使用 HTTP）")
    if local and loopback:
        return url
    try:
        addresses = socket.getaddrinfo(p.hostname, p.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        raise ValueError("无法解析服务器地址，请检查网络或代理")
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("不允许访问局域网或保留地址")
    return url


def open_request(url, data=None, headers=None, local=False, timeout=90):
    validate_url(url, local=local)
    request = Request(url, data=data, headers=headers or {})
    try:
        return build_opener(NoRedirect()).open(request, timeout=timeout)
    except HTTPError as e:
        # Avoid reflecting provider responses, request URLs or credentials into logs/UI.
        messages = {401: "凭证无效或已过期", 403: "当前凭证没有访问权限", 404: "接口或模型不存在",
                    429: "请求频率或额度受限", 400: "模型不支持当前请求参数或格式"}
        raise ValueError("远端服务 HTTP %s：%s" % (e.code, messages.get(e.code, "请稍后重试或检查服务配置"))) from None
    except (URLError, OSError):
        raise ValueError("连接远端服务失败，请检查网络、代理和接口地址") from None


def read_limited(response, limit):
    value = response.read(limit + 1)
    if len(value) > limit:
        raise ValueError("远端响应超出大小上限")
    return value


def post_json(url, payload, headers=None, local=False):
    combined = {"Content-Type": "application/json", "Accept": "application/json"}
    combined.update(headers or {})
    with open_request(url, json.dumps(payload, ensure_ascii=False).encode("utf-8"), combined, local=local) as r:
        return json.loads(read_limited(r, 8 * 1024 * 1024))
