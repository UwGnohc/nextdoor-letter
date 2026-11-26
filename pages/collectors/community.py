"""Public BOYNEXTDOOR fan discussions. Never fetch replies, profiles or linked pages."""

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree


FORUM = "https://kpopsource.com/tags/boynextdoor/"
SOCIAL = "https://mastodon.social/tags/boynextdoor"
REDDIT = "https://www.reddit.com/r/BOYNEXTDOOR_/"
USER_AGENT = "NextdoorLetter/1.0 (personal feed reader)"
LIMIT = 1_000_000
ABOUT = re.compile(
    r"\b(?:boy7?nextdoor|boynextage|onedoor(?:ful)?|woonhak|taesan|leehan|"
    r"riwoo|sungho|jaehyun)\b|보이넥스트도어|운학|태산|이한|리우|성호|명재현", re.I
)
SOCIAL_HOSTS = {"mastodon.social", "kpop.social", "norden.social", "apobangpo.space"}


def read_public(url):
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=6) as response:
        body = response.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise ValueError("来源响应过大")
    return body


def permitted_read(url):
    robots = urljoin(url, "/robots.txt")
    try:
        rules = read_public(robots).decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code != 404:
            raise
        rules = ""
    parser = RobotFileParser()
    parser.parse(rules.splitlines())
    if not parser.can_fetch(USER_AGENT, url):
        raise ValueError("此站仅提供浏览器直达")
    return read_public(url)


def item(source, title, link, published):
    return {
        "id": hashlib.sha256(link.encode()).hexdigest()[:20], "title": title,
        "url": link, "source": source, "kind": "社区讨论", "summary": "",
        "published_at": published.astimezone(timezone.utc).isoformat(timespec="seconds"),
    }


class ForumTags(HTMLParser):
    """Extract thread titles and original posting times from visible tag cards."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self.cards = 0
        self.heading = False
        self.link = ""
        self.text = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "h3" and "contentRow-title" in values.get("class", "").split():
            self.cards += 1
            self.heading, self.link, self.text = True, "", []
        elif tag == "a" and self.heading:
            path = values.get("href", "")
            if re.fullmatch(r"/threads/[A-Za-z0-9_.%-]+\.\d+/", path, re.I):
                self.link = urljoin(FORUM, path)
        elif tag == "time" and self.link and not self.heading:
            try:
                stamp = datetime.fromisoformat(values.get("datetime", ""))
            except ValueError:
                return
            title = " ".join(" ".join(self.text).split())
            if stamp.tzinfo and ABOUT.search(title):
                self.rows.append(item("K-Pop Source", title, self.link, stamp))
            self.link = ""

    def handle_endtag(self, tag):
        if tag == "h3":
            self.heading = False

    def handle_data(self, text):
        if self.heading:
            self.text.append(text)


def forum_threads():
    parser = ForumTags()
    parser.feed(permitted_read(FORUM).decode("utf-8"))
    parser.close()
    if not parser.cards:
        raise ValueError("社区页面未返回可识别的帖子列表")
    return parser.rows


class PostLines(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "li"}:
            self.parts.append("\n")

    def handle_data(self, text):
        self.parts.append(text)


def social_posts():
    rows = []
    root = ElementTree.fromstring(permitted_read(SOCIAL + ".rss"))
    if root.find("channel") is None:
        raise ValueError("社区订阅格式已变化")
    for entry in root.findall("./channel/item"):
        link = (entry.findtext("link") or "").strip()
        parts = urlsplit(link)
        # Federated tags also contain mirrored news articles. Keep native social post URLs.
        if (parts.scheme != "https" or parts.netloc not in SOCIAL_HOSTS or parts.query
                or not re.fullmatch(r"/@[\w.-]+/\d+", parts.path)):
            continue
        parser = PostLines()
        parser.feed(entry.findtext("description", ""))
        parser.close()
        lines = []
        for line in "".join(parser.parts).splitlines():
            clean = re.sub(r"https?://\S+|(?<!\w)#\w+", "", line)
            clean = " ".join(clean.split())
            if ABOUT.search(clean):
                lines.append(clean)
        if not lines:
            continue
        title = lines[0]
        try:
            when = parsedate_to_datetime(entry.findtext("pubDate", ""))
        except (ValueError, TypeError, OverflowError):
            continue
        if when.tzinfo:
            # The feed has no titles. Display an excerpt from the post itself.
            rows.append(item("Mastodon", title if len(title) <= 125 else title[:124] + "…", link, when))
    return rows


def fetch_community():
    """Returns newest-first posts plus source status; link-only communities use ok=None."""
    sources, posts = [], {}
    feeds = [("K-Pop Source", FORUM, forum_threads), ("Mastodon", SOCIAL, social_posts)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [(name, url, pool.submit(fetch)) for name, url, fetch in feeds]
        for name, url, job in jobs:
            try:
                rows = job.result()
                posts.update((row["url"], row) for row in rows)
                status = {"ok": True, "error": ""}
            except (OSError, ValueError, HTTPException, ElementTree.ParseError) as exc:
                status = {"ok": False, "error": str(exc)}
            sources.append({"name": name, "url": url, "mode": "feed", **status})
    sources.append({"name": "Reddit · r/BOYNEXTDOOR_", "url": REDDIT,
                    "ok": None, "mode": "link", "error": ""})
    return {"items": sorted(posts.values(), key=lambda row: row["published_at"], reverse=True),
            "sources": sources}
