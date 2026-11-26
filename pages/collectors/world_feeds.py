"""Public Japanese and Korean BOYNEXTDOOR community posts."""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

from community import item, permitted_read


NOTE = "https://note.com/hashtag/BOYNEXTDOOR"
FANPLUS = "https://fanplus.co.kr/community/boynextdoor"
NOTE_NAME = "note · BOYNEXTDOOR"
FANPLUS_NAME = "FanPlus · BOYNEXTDOOR"
JAPANESE = re.compile(r"[ぁ-んァ-ヶ]")
KOREAN = re.compile(r"[가-힣]")
# Tag feeds can include unrelated games and other musicians. Require explicit
# group, fandom or tour references in addition to the tag.
SUBJECT = re.compile(r"BOY\s*NEXT\s*DOOR|ONEDOOR|ボネクド|ボイネク|ボーイネクストドア|"
                     r"보이넥스트도어|KNOCK\s*ON\s*Vol|楽園\s*Vol\.\s*2", re.I)
SHOPPING_GUIDE = re.compile(r"当選枚数|当選ライン|最新ボーダー|ヨントン.{0,12}相場")


def community_item(name, title, url, published, kind, language, region):
    post = item(name, title, url, published)
    post.update(kind=kind, language=language, region=region)
    return post


class ExcerptText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, text):
        self.text.append(text)


def note_posts():
    root = ElementTree.fromstring(permitted_read(NOTE + "/rss"))
    if root.find("channel") is None:
        raise ValueError("note 未返回标签订阅")
    result = []
    for entry in root.findall("./channel/item"):
        title = " ".join(entry.findtext("title", "").split())
        url = entry.findtext("link", "").strip()
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.netloc != "note.com"
                or not re.fullmatch(r"/[A-Za-z0-9_-]+/n/n[0-9a-f]+", parts.path)):
            continue
        excerpt = ExcerptText()
        excerpt.feed(entry.findtext("description", ""))
        excerpt.close()
        text = title + " " + " ".join(excerpt.text).replace("続きをみる", "")
        if not title or not JAPANESE.search(text) or not SUBJECT.search(text) or SHOPPING_GUIDE.search(title):
            continue
        try:
            when = parsedate_to_datetime(entry.findtext("pubDate", ""))
        except (TypeError, ValueError, OverflowError):
            continue
        if when.tzinfo:
            result.append(community_item(NOTE_NAME, title, "https://note.com" + parts.path,
                                         when, "歌迷随笔", "ja", "日本"))
    return result


class FanPlusBoard(HTMLParser):
    """Only read normal post cards linking to the Korean group board itself."""

    def __init__(self):
        super().__init__()
        self.posts = []
        self.card_count = 0
        self.url = ""
        self.heading = False
        self.title = []
        self.when = ""

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("data-board-row-link") == "true":
            path = values.get("href", "")
            if re.fullmatch(r"/community/boynextdoor/[0-9]+", path):
                self.card_count += 1
                self.url = urljoin(FANPLUS, path)
                self.title, self.when = [], ""
        elif self.url and tag == "h3":
            self.heading = True
        elif self.url and tag == "time":
            self.when = values.get("datetime", "")

    def handle_data(self, text):
        if self.heading:
            self.title.append(text)

    def handle_endtag(self, tag):
        if tag == "h3":
            self.heading = False
        if tag != "a" or not self.url:
            return
        link, self.url = self.url, ""
        title = " ".join("".join(self.title).split())
        # Exclude cross-board notices, ads, friend requests, and platform messages.
        match = re.fullmatch(r"\[\s*소통\s*\]\s*(.+)", title)
        if not match or not KOREAN.search(match[1]):
            return
        try:
            when = datetime.fromisoformat(self.when.replace("Z", "+00:00"))
        except ValueError:
            return
        if when.tzinfo:
            self.posts.append(community_item(FANPLUS_NAME, match[1], link, when,
                                             "社区讨论", "ko", "韩国"))


def fanplus_posts():
    parser = FanPlusBoard()
    parser.feed(permitted_read(FANPLUS).decode("utf-8"))
    parser.close()
    if not parser.card_count:
        raise ValueError("FanPlus 韩语版未返回专版帖子列表")
    return parser.posts


def fetch_world():
    specs = [(NOTE_NAME, NOTE, "ja", "日本", note_posts),
             (FANPLUS_NAME, FANPLUS, "ko", "韩国", fanplus_posts)]
    sources, unique = [], {}
    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        tasks = [(name, url, lang, region, pool.submit(get)) for name, url, lang, region, get in specs]
        for name, url, lang, region, task in tasks:
            try:
                rows = task.result()
                unique.update((row["url"], row) for row in rows)
                ok, error = True, ""
            except (OSError, HTTPException, ValueError, ElementTree.ParseError) as exc:
                ok, error = False, str(exc)
            sources.append({"name": name, "url": url, "language": lang, "region": region,
                            "mode": "feed", "ok": ok, "error": error})
    return {"items": sorted(unique.values(), key=lambda row: row["published_at"], reverse=True),
            "sources": sources}
