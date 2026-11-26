"""Local reader for BOYNEXTDOOR's public news, calendar and videos."""
import argparse
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from threading import Lock, Thread
from time import monotonic
from urllib.request import urlopen
import webbrowser

from editorial import enrich
from feeds import fetch_all
from community import fetch_community
from community_media import fetch_media
from community_titles import chinese_title
from world_feeds import fetch_world
from translate import known_title, title_language, translate_title


HOME = Path(__file__).resolve().parent
SNAPSHOT = HOME / "snapshot.js"
JS_PREFIX = "window.NEXTDOOR_SNAPSHOT = "
PORT = 18771
INTERVAL = 600
CHINA = timezone(timedelta(hours=8))


def instance_identity():
    build = sha256()
    for source in sorted(HOME.glob("*.py")):
        build.update(source.read_bytes())
    return {
        "app": "nextdoor-letter",
        "folder": sha256(os.path.normcase(str(HOME)).encode("utf-8")).hexdigest()[:16],
        "build": build.hexdigest()[:16],
    }


COMMUNITY_LINKS = [
    {"name": "哔哩哔哩 · 视频与二创", "url": "https://search.bilibili.com/all?keyword=BOYNEXTDOOR"},
    {"name": "微博 · 话题讨论", "url": "https://s.weibo.com/weibo?q=BOYNEXTDOOR"},
    {"name": "Dcard · BOYNEXTDOOR 板", "url": "https://www.dcard.tw/f/boynextdoor", "region": "台湾", "language": "zh-Hant"},
]


def load_snapshot():
    try:
        raw = SNAPSHOT.read_text(encoding="utf-8").removeprefix(JS_PREFIX).strip().removesuffix(";")
        saved = json.loads(raw)
        if all(isinstance(saved[k], list) for k in ("items", "events", "sources")):
            return saved
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {"items": [], "sources": [], "events": [], "updated_at": ""}


def sort_date(row):
    stamp = row["published_at"]
    if len(stamp) == 10:
        return stamp
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(CHINA).isoformat()


def merge(previous, result):
    checked = datetime.now(timezone.utc).isoformat(timespec="seconds")
    status = {src["name"]: src for src in previous["sources"]}
    events = {(row["url"], row["start_at"]): row for row in previous["events"]}
    stories = {row["id"]: row for row in previous["items"]}
    for src in result["sources"]:
        name = src["name"]
        last_success = status.get(name, {}).get("updated_at", "")
        status[name] = dict(src, updated_at=checked if src["ok"] else last_success)
        if src["ok"] and not src.get("error"):
            events = {key: row for key, row in events.items() if row["source"] != name}
    for row in result["items"]:
        stories[row["id"]] = {**row, **enrich(row)}
    for row in result["events"]:
        event = dict(row, title_zh=enrich(row).get("title_zh", ""))
        events[(row["url"], row["start_at"])] = event
    successes = [src["updated_at"] for src in status.values() if src.get("updated_at")]
    return {
        "items": sorted(stories.values(), key=sort_date, reverse=True)[:180],
        "events": sorted(events.values(), key=lambda e: e["start_at"]),
        "sources": list(status.values()), "updated_at": max(successes, default=""),
    }


def neighbor_snapshot(previous, fetches):
    """Replace the latest page on success and serve each source's cache on failure."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    old_sources = {s["name"]: s for s in previous.get("sources", [])}
    rows, sources = {}, []
    for provider, job in fetches:
        try:
            data = job.result()
        except Exception:
            fallback = [s for s in old_sources.values() if s.get("provider") == provider]
            data = {"items": [], "sources": [
                dict(s, ok=False, error="暂时无法更新来源")
                for s in fallback if s.get("mode") != "link"
            ] + [s for s in fallback if s.get("mode") == "link"]}
            if not data["sources"]:
                data["sources"] = [{"name": provider, "ok": False, "error": "暂时无法更新来源", "url": ""}]
        for src in data["sources"]:
            name = src["name"]
            old = old_sources.get(name, {})
            ok = src.get("ok")
            sources.append(dict(src, provider=provider, updated_at=stamp if ok else old.get("updated_at", "")))
            if ok is False:
                for row in previous.get("items", []):
                    if row["source"] == name:
                        rows[row["url"]] = row
        for row in data["items"]:
            label = row.get("title_zh") or chinese_title(row)
            region = row.get("region") or ("中文圈" if row["kind"] == "媒体报道" else "国际")
            lang = "zh-Hans" if row["source"] == "KSD 韩星网" else title_language(row)
            rows[row["url"]] = dict(row, region=region, language=lang, title_zh=label if label != row["title"] else "")
    sources.extend(dict(s, mode="link", ok=None, error="", updated_at="") for s in COMMUNITY_LINKS)
    return {
        "items": sorted(rows.values(), key=sort_date, reverse=True)[:120],
        "sources": sources,
        "updated_at": max((s["updated_at"] for s in sources), default=""),
    }


class Mailbox:
    def __init__(self):
        self.state = load_snapshot()
        self.lock = Lock()
        self.busy = {"official": False, "community": False}
        self.attempt = dict.fromkeys(self.busy, float("-inf"))
        self.errors = dict.fromkeys(self.busy, "")
        self.storage_warning = ""
        self.translating = {}

    def read(self):
        with self.lock:
            community = {"items": [], "sources": [], "updated_at": "", **self.state.get("community", {}),
                         "refreshing": self.busy["community"], "error": self.errors["community"],
                         "storage_warning": self.storage_warning}
            return dict(self.state, refreshing=self.busy["official"], error=self.errors["official"],
                        storage_warning=self.storage_warning, community=community)

    def check(self, force=False, background=True, sections=("official", "community")):
        for section in sections:
            with self.lock:
                if self.busy[section] or monotonic() - self.attempt[section] < (0 if force else INTERVAL):
                    continue
                self.busy[section] = True
                self.errors[section] = ""
                self.attempt[section] = monotonic()
            if background:
                Thread(target=self.update, args=(section,), daemon=True).start()
            else:
                self.update(section)

    def save_locked(self, state):
        encoded = json.dumps(state, ensure_ascii=False).replace("<", r"\u003c")
        temp = SNAPSHOT.with_name(f".snapshot-{os.getpid()}.tmp")
        try:
            temp.write_text(JS_PREFIX + encoded + ";\n", encoding="utf-8")
            temp.replace(SNAPSHOT)
            self.storage_warning = ""
        except OSError:
            self.storage_warning = "已在本次浏览中更新。要保存离线快照，请将完整文件夹解压到可写目录。"
        self.state = state

    def update(self, section):
        try:
            if section == "official":
                data = fetch_all()
                with self.lock:
                    self.save_locked({**self.state, **merge(self.state, data)})
            else:
                with ThreadPoolExecutor(max_workers=3) as pool:
                    neighbors = [("粉丝社区", pool.submit(fetch_community)), ("中文媒体", pool.submit(fetch_media)),
                                 ("各地社区", pool.submit(fetch_world))]
                with self.lock:
                    previous = self.state.get("community", {})
                    community = neighbor_snapshot(previous, neighbors)
                    saved = {(r["id"], r["title"]): r for r in previous.get("items", []) if r.get("translation_provider")}
                    for row in community["items"]:
                        old = saved.get((row["id"], row["title"]))
                        if old and not known_title(row):
                            row.update(title_zh=old["title_zh"], translation_provider=old["translation_provider"])
                    self.save_locked(dict(self.state, community=community))
        except Exception as err:
            with self.lock:
                self.errors[section] = "更新未完成：" + str(err)
        finally:
            with self.lock:
                self.busy[section] = False

    def translate(self, post_id):
        with self.lock:
            row = next((r for r in self.state.get("community", {}).get("items", []) if r["id"] == post_id), None)
            if row is None:
                raise KeyError("这条帖子已移出当前列表，请更新讨论后重试。")
            local = known_title(row)
            if local:
                return {"translation": local, "provider": row.get("translation_provider", "本地译文")}
            key = (post_id, row["title"])
            future = self.translating.get(key)
            owner = future is None
            if owner:
                future = self.translating[key] = Future()
        if not owner:
            return future.result()
        try:
            translated = translate_title(row)
            result = {"translation": translated, "provider": "在线翻译"}
            with self.lock:
                c = self.state["community"]
                items = [dict(i, title_zh=translated, translation_provider=result["provider"])
                         if (i["id"], i["title"]) == key else i for i in c["items"]]
                self.save_locked(dict(self.state, community=dict(c, items=items)))
            future.set_result(result)
            return result
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            with self.lock:
                self.translating.pop(key, None)


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False
    allow_reuse_port = False

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_data(self, payload, mime, status=200):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except ConnectionError:
            pass

    def json(self, data, status=200):
        self.send_data(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

    def valid_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.valid_host():
            self.send_error(403)
            return
        self.server.last_visit = monotonic()
        path = self.path.partition("?")[0]
        if path in ("/", "/index.html"):
            self.send_data((HOME / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/snapshot.js":
            self.send_data(SNAPSHOT.read_bytes() if SNAPSHOT.is_file() else b"", "text/javascript; charset=utf-8")
        elif path == "/api/identity":
            self.json(self.server.app_identity)
        elif path == "/api/news":
            self.server.mailbox.check()
            self.json(self.server.mailbox.read())
        elif path == "/api/community/news":
            self.json(self.server.mailbox.read()["community"])
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path not in ("/api/refresh", "/api/community/refresh", "/api/community/translate"):
            self.send_error(404)
            return
        origin = self.headers.get("Origin")
        if not self.valid_host() or self.headers.get("Sec-Fetch-Site") == "cross-site" or (origin and origin != "http://" + self.headers["Host"]):
            self.send_error(403)
            return
        self.server.last_visit = monotonic()
        mailbox = self.server.mailbox
        if self.path == "/api/community/translate":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not (0 < size <= 1024) or self.headers.get_content_type() != "application/json":
                    raise ValueError("请选择当前帖子进行翻译。")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict) or set(body) != {"id"} or not isinstance(body["id"], str):
                    raise ValueError("翻译请求缺少有效的帖子编号。")
            except (ValueError, UnicodeError):
                self.json({"error": "请选择当前列表中的一条帖子进行翻译。"}, 400)
                return
            try:
                self.json(mailbox.translate(body["id"]))
            except KeyError:
                self.json({"error": "帖子已移出当前列表，请更新后重试。"}, 404)
            except ValueError as exc:
                self.json({"error": str(exc)}, 503)
            except Exception:
                self.json({"error": "翻译服务暂时不可用，请稍后重试。"}, 503)
        elif self.path == "/api/community/refresh":
            mailbox.check(force=True, sections=("community",))
            self.json(mailbox.read()["community"])
        else:
            mailbox.check(force=True, sections=("official",))
            self.json(mailbox.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--refresh-only", action="store_true")
    args = parser.parse_args()
    mailbox = Mailbox()
    if args.refresh_only:
        mailbox.check(background=False)
        state = mailbox.read()
        print(len(state["items"]), "条动态", state["sources"], state["error"])
        neighbors = state.get("community", {})
        print(len(neighbors.get("items", [])), "条邻里消息", neighbors.get("sources", []))
        return int(bool(state["error"] or neighbors.get("error") or state["storage_warning"])
                   or not any(src["ok"] for src in state["sources"])
                   or not any(src.get("ok") for src in neighbors.get("sources", [])))
    identity = instance_identity()
    for port in range(PORT, PORT + 8):
        url = f"http://127.0.0.1:{port}/"
        try:
            server = LocalServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            try:
                with urlopen(url + "api/identity", timeout=.8) as response:
                    if json.load(response) == identity:
                        if not args.no_browser:
                            webbrowser.open(url)
                        print(url, flush=True)
                        return 0
            except (OSError, ValueError):
                pass
    else:
        raise SystemExit("本地端口已被占用，请重试。")
    server.mailbox = mailbox
    server.app_identity = identity
    if mailbox.state.get("online_port") != port:
        mailbox.save_locked(dict(mailbox.state, online_port=port))
    server.last_visit = monotonic()
    server.timeout = 10
    print("隔壁来信  " + url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        with server:
            while monotonic() - server.last_visit < 3600:
                server.handle_request()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
