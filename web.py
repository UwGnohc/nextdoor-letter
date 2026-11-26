"""Public WSGI entry point for the BOYNEXTDOOR reader."""

from collections import deque
from http import HTTPStatus
import json
import os
from pathlib import Path
from threading import BoundedSemaphore, Lock
from time import monotonic

from app import Mailbox
from translate import known_title


ROOT = Path(__file__).resolve().parent
HOSTS = frozenset(
    value.strip().lower()
    for value in (os.getenv("RENDER_EXTERNAL_HOSTNAME"), os.getenv("APP_HOST"))
    if value and value.strip()
)
SECTIONS = ("official", "community")
POST_PATHS = ("/api/refresh", "/api/community/refresh", "/api/community/translate")
READ_PATHS = ("/", "/index.html", "/snapshot.js", "/api/news", "/api/community/news", "/favicon.ico")
JSON_TYPE = "application/json; charset=utf-8"
SOURCE_FIELDS = ("name", "url", "ok", "updated_at", "mode", "region", "language")
ITEM_FIELDS = (
    "id", "title", "title_zh", "summary_zh", "url", "source", "kind", "published_at",
    "members", "language", "region", "translation_provider",
)
EVENT_FIELDS = ("title", "title_zh", "url", "source", "start_at", "end_at")

mailbox = Mailbox()
refresh_gate = Lock()
translation_slots = BoundedSemaphore(2)
translation_gate = Lock()
recent_translations = deque()


def fields(row, names):
    return {name: row[name] for name in names if name in row}


def public_section(state, official=False):
    """Only publish fields used by the UI, including safe public status messages."""
    data = {
        "items": [fields(entry, ITEM_FIELDS) for entry in state.get("items", ())],
        "sources": [
            {**fields(src, SOURCE_FIELDS), "error": "来源暂时未能完整更新" if src.get("error") else ""}
            for src in state.get("sources", ())
        ],
        "updated_at": state.get("updated_at", ""),
        "refreshing": bool(state.get("refreshing")),
        "error": "更新暂时未完成，请稍后再试。" if state.get("error") else "",
        "storage_warning": "本次更新可在线查看，服务器暂未保存快照。" if state.get("storage_warning") else "",
    }
    if official:
        data["events"] = [fields(event, EVENT_FIELDS) for event in state.get("events", ())]
        data["community"] = public_section(state.get("community", {}))
    return data


def check(sections, manual=False):
    """Automatic updates use Mailbox's ten-minute interval. Explicit ones share a cooldown."""
    with refresh_gate:
        if manual:
            with mailbox.lock:
                sections = tuple(
                    name for name in sections
                    if monotonic() - mailbox.attempt[name] >= 30 and not mailbox.busy[name]
                )
        mailbox.check(force=manual, sections=sections)


def acquire_translation_budget():
    now = monotonic()
    with translation_gate:
        while recent_translations and recent_translations[0] <= now - 60:
            recent_translations.popleft()
        if len(recent_translations) >= 6:
            return False
        recent_translations.append(now)
        return True


def encode(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def response(environ, start, code, body, mime=JSON_TYPE, extra=()):
    if isinstance(body, dict):
        body = encode(body)
    headers = [
        ("Content-Type", mime),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "same-origin"),
        ("Content-Security-Policy", "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"),
        *extra,
    ]
    start(f"{code} {HTTPStatus(code).phrase}", headers)
    return [] if environ["REQUEST_METHOD"] == "HEAD" else [body]


def origin_allowed(environ, host):
    origin = environ.get("HTTP_ORIGIN", "")
    site = environ.get("HTTP_SEC_FETCH_SITE", "")
    if site and site != "same-origin":
        return False
    # Render terminates TLS. Browser-origin checks use a configured external host,
    # independently of the internal proxy scheme and client-supplied forwarding fields.
    expected = {"https://" + host}
    if host.split(":", 1)[0] in {"localhost", "127.0.0.1"}:
        expected.add("http://" + host)
    return origin.lower() in expected if origin else site == "same-origin"


def translate_request(environ, start, length):
    def reply(code, result, extra=()):
        return response(environ, start, code, result, extra=extra)
    if not 0 < length <= 1024:
        return reply(413 if length > 1024 else 400, {"error": "请选择当前列表中的一条标题。"})
    if environ.get("CONTENT_TYPE", "").partition(";")[0].strip().lower() != "application/json":
        return reply(415, {"error": "翻译请求需要 JSON 格式。"})
    try:
        body = json.loads(environ["wsgi.input"].read(length))
        if not isinstance(body, dict) or set(body) != {"id"} or not isinstance(body["id"], str):
            raise ValueError()
        post_id = body["id"]
    except (ValueError, UnicodeError, RecursionError):
        return reply(400, {"error": "请选择当前列表中的一条标题。"})

    with mailbox.lock:
        row = next((r for r in mailbox.state.get("community", {}).get("items", ()) if r["id"] == post_id), None)
        if row:
            cached = known_title(row)
            if cached:
                return reply(200, {"translation": cached, "provider": row.get("translation_provider") or "已保存译文"})
    if row is None:
        return reply(404, {"error": "帖子已移出当前列表，请更新讨论后重试。"})
    if not translation_slots.acquire(blocking=False):
        return reply(429, {"error": "其他标题正在翻译，请稍后再试。"}, [("Retry-After", "5")])
    try:
        if not acquire_translation_budget():
            return reply(429, {"error": "翻译请求较多，请在一分钟后再试。"}, [("Retry-After", "60")])
        return reply(200, mailbox.translate(post_id))
    except KeyError:
        return reply(404, {"error": "帖子已移出当前列表，请更新讨论后重试。"})
    except Exception:
        return reply(503, {"error": "暂时没有可用的中文译文，可使用网页版翻译。"})
    finally:
        translation_slots.release()


def application(environ, start_response):
    method = environ["REQUEST_METHOD"]
    path = environ.get("PATH_INFO", "/")

    def reply(code, body, mime=JSON_TYPE, extra=()):
        return response(environ, start_response, code, body, mime, extra)

    # Render can use an internal Host header for its load-balancer health checks.
    if path == "/healthz" and method in ("GET", "HEAD"):
        return reply(200, {"ok": True})
    host = environ.get("HTTP_HOST", "").lower()
    if not HOSTS:
        return reply(503, {"error": "尚未配置服务域名。"})
    if host not in HOSTS:
        return reply(403, {"error": "访问域名无效。"})
    if path not in READ_PATHS and path not in POST_PATHS:
        return reply(404, {"error": "页面不存在。"})
    if path in POST_PATHS:
        if method != "POST":
            return reply(405, {"error": "请求方式无效。"}, extra=[("Allow", "POST")])
        if not origin_allowed(environ, host):
            return reply(403, {"error": "请在当前站点内操作。"})
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            return reply(400, {"error": "请求长度无效。"})
        if path == "/api/community/translate":
            return translate_request(environ, start_response, length)
        if length != 0:
            return reply(413 if length > 0 else 400, {"error": "刷新请求应为空。"})
        official = path == "/api/refresh"
        check(("official" if official else "community",), manual=True)
        state = mailbox.read()
        return reply(200, public_section(state if official else state["community"], official))

    if method not in ("GET", "HEAD"):
        return reply(405, {"error": "请求方式无效。"}, extra=[("Allow", "GET, HEAD")])
    if path in ("/", "/index.html"):
        return reply(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
    if path == "/favicon.ico":
        return reply(204, b"", "image/x-icon")
    if path == "/api/news" and method == "GET":
        check(SECTIONS)
    state = mailbox.read()
    if path == "/api/community/news":
        return reply(200, public_section(state["community"]))
    payload = public_section(state, official=True)
    if path == "/snapshot.js":
        script = b"window.NEXTDOOR_SNAPSHOT = " + encode(payload).replace(b"<", b"\\u003c") + b";\n"
        return reply(200, script, "text/javascript; charset=utf-8")
    return reply(200, payload)
