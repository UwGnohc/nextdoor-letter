"""Read BOYNEXTDOOR coverage from the public simplified-Chinese KSD topic page."""

from datetime import date
from html.parser import HTMLParser
from http.client import HTTPException
import re
from urllib.robotparser import RobotFileParser

from feeds import make_item, read_url


ORIGIN = "https://www.koreastardaily.com"
TOPIC_URL = ORIGIN + "/sc/tags/BOYNEXTDOOR"
SOURCE = "KSD 韩星网"
GROUP = re.compile(r"BOY\s*NEXT\s*DOOR|보이넥스트도어", re.I)
DATE = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")


class TopicArticles(HTMLParser):
    def __init__(self):
        super().__init__()
        self.card = None
        self.field = ""
        self.items = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "div" and "list-item" in classes:
            self.card = {"title": "", "intro": "", "date": "", "path": ""}
            self.field = ""
        if self.card is None:
            return
        if tag == "h2":
            self.field = "title"
        elif tag == "h3":
            self.field = "date"
        elif tag == "p" and "list-body-summary" in classes:
            self.field = "intro"
        elif tag == "a" and self.field == "title":
            path = attrs.get("href") or ""
            if re.fullmatch(r"/sc/news/\d+", path):
                self.card["path"] = path

    def handle_data(self, value):
        if self.card is not None and self.field:
            self.card[self.field] += value

    def handle_endtag(self, tag):
        if self.card is None:
            return
        if tag == "h3" and self.field == "date":
            self.add_article(self.card)
            self.card = None
            self.field = ""
        elif (tag, self.field) in (("h2", "title"), ("p", "intro")):
            self.field = ""

    def add_article(self, card):
        title = " ".join(card["title"].split())
        match = DATE.search(card["date"])
        # Some tag pages include festival and TV round-ups. Require an explicit group reference.
        if not title or not card["path"] or not match or not GROUP.search(title + " " + card["intro"]):
            return
        try:
            # The topic list does not declare a time zone; keep its local publication date.
            day = date(*map(int, match.groups())).isoformat()
        except ValueError:
            return
        url = ORIGIN + card["path"]
        item = make_item(title, url, SOURCE, "媒体报道", day)
        item["title_zh"] = title
        self.items[url] = item


def fetch_media():
    status = {"name": SOURCE, "url": TOPIC_URL, "ok": False, "error": ""}
    try:
        rules = RobotFileParser()
        robots = read_url(ORIGIN + "/robots.txt").decode("utf-8-sig")
        rules.parse(robots.splitlines())
        if not rules.can_fetch("NextdoorLetter", TOPIC_URL):
            raise ValueError("来源的访问规则不允许读取该专题")
        parser = TopicArticles()
        parser.feed(read_url(TOPIC_URL).decode("utf-8"))
        parser.close()
        items = sorted(parser.items.values(), key=lambda item: item["published_at"], reverse=True)
        if not items:
            raise ValueError("专题暂未返回可核实日期的组合报道")
        status["ok"] = True
    except (HTTPException, OSError, ValueError) as exc:
        status["error"] = str(exc)
        items = []
    return {"items": items, "sources": [status]}
