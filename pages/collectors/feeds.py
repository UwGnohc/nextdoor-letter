"""BOYNEXTDOOR's public Japan news, schedule and official video channel."""

import hashlib
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree


JAPAN = "https://boynextdoor-official.jp"
CHANNEL_ID = "UChhKBlh_wvspTh5n4mL0b5g"
VIDEO_HOME = f"https://www.youtube.com/channel/{CHANNEL_ID}"
VIDEO_FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
JST = timezone(timedelta(hours=9))
NEWS = "日本官网 · 新闻"
SCHEDULE = "日本官网 · 日程"
VIDEOS = "BOYNEXTDOOR 官方 YouTube"
MAX_BYTES = 2 * 1024 * 1024


def read_url(url):
    req = Request(url, headers={"User-Agent": "NextdoorLetter/1.0 (personal feed reader)"})
    with urlopen(req, timeout=8) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("来源响应过大")
    return data


def make_item(title, url, source, kind, published_at, summary=""):
    return {
        "id": hashlib.sha256(url.encode("utf-8")).hexdigest()[:20],
        "title": title, "url": url, "source": source, "kind": kind,
        "published_at": published_at, "summary": summary,
    }


class JapanList(HTMLParser):
    """Read dated cards with a public detail link. Skip membership-only buttons."""

    def __init__(self, section):
        super().__init__()
        self.path = re.compile(r"/" + section + r"/[a-z0-9-]+/?", re.I)
        self.rows = []
        self.day = ""
        self.category = ""
        self.tag = ""
        self.text = []
        self.link = ""

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.tag, self.text = "p", []
        elif tag == "a":
            path = urlsplit(dict(attrs).get("href") or "")
            self.link = ""
            if not path.netloc and self.path.fullmatch(path.path):
                self.link = JAPAN + path.path.rstrip("/")
            self.tag, self.text = "a", []

    def handle_data(self, data):
        if self.tag:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag != self.tag:
            return
        value = " ".join("".join(self.text).split())
        if tag == "p" and re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", value):
            self.day = date.fromisoformat(value.replace(".", "-")).isoformat()
            self.category = ""
        elif tag == "p" and self.day and re.fullmatch(r"[A-Z& ]{2,}", value):
            self.category = value
        elif tag == "a" and self.link and self.day and value:
            self.rows.append((value, self.link, self.day, self.category))
            self.day = ""
        self.tag = ""


def japan_rows(section):
    parser = JapanList(section)
    parser.feed(read_url(f"{JAPAN}/{section}").decode("utf-8"))
    parser.close()
    if not parser.rows:
        raise ValueError("官网列表未返回带日期的公开条目")
    return parser.rows


class BodyText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fragments = []

    def handle_data(self, text):
        self.fragments.append(text.strip())


# Only accept an explicitly labelled event period. Sales, application deadlines,
# shipment estimates, and the news article's publication date are different things.
PERIOD = re.compile(
    r"開催期間\s*[:：]?\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日"
    r"(?:\s*\([^)]{1,10}\))?\s*[~〜～]\s*(?:(\d{4})年\s*)?(\d{1,2})月\s*(\d{1,2})日"
)


def event_from_news(row):
    title, url, _, _ = row
    parser = BodyText()
    parser.feed(read_url(url).decode("utf-8"))
    parser.close()
    text = unicodedata.normalize("NFKC", " ".join(parser.fragments))
    periods = list(PERIOD.finditer(text))
    if len(periods) != 1:
        return None
    y1, m1, d1, y2, m2, d2 = periods[0].groups()
    start = date(int(y1), int(m1), int(d1))
    end = date(int(y2 or y1), int(m2), int(d2))
    if end < start:
        return None
    return {"title": title, "start_at": start.isoformat(), "end_at": end.isoformat(),
            "url": url, "source": NEWS}


def fetch_news():
    rows = japan_rows("news")
    items = [make_item(title, url, NEWS, "官方公告", day) for title, url, day, _ in rows]
    recent = (datetime.now(JST).date() - timedelta(days=30)).isoformat()
    notices = [r for r in rows if r[3] == "EVENT & LIVE" and r[2] >= recent][:3]
    events, errors = [], []
    for row in notices:
        try:
            event = event_from_news(row)
            if event:
                events.append(event)
        except (HTTPException, OSError, ValueError) as exc:
            errors.append(f"活动日期暂未更新：{exc}")
    return items, events, "；".join(errors)


def fetch_calendar():
    events = [{"title": title, "start_at": day, "url": url, "source": SCHEDULE}
              for title, url, day, _ in japan_rows("schedule")]
    return [], events, ""


def fetch_videos():
    atom = "{http://www.w3.org/2005/Atom}"
    yt = "{http://www.youtube.com/xml/schemas/2015}"
    root = ElementTree.fromstring(read_url(VIDEO_FEED))
    items = []
    for entry in root.findall(atom + "entry"):
        channel = entry.findtext(yt + "channelId")
        video = entry.findtext(yt + "videoId", "")
        title = entry.findtext(atom + "title", "").strip()
        raw_date = entry.findtext(atom + "published", "")
        if channel != CHANNEL_ID or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video) or not title:
            continue
        try:
            published = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError:
            continue
        if published.tzinfo is None:
            continue
        items.append(make_item(title, f"https://www.youtube.com/watch?v={video}", VIDEOS,
                               "官方视频", published.astimezone(timezone.utc).isoformat()))
    if not items:
        raise ValueError("频道未返回有效视频")
    return items, [], ""


def fetch_all():
    sources = [(NEWS, JAPAN + "/news", fetch_news),
               (SCHEDULE, JAPAN + "/schedule", fetch_calendar),
               (VIDEOS, VIDEO_HOME, fetch_videos)]
    result = {"items": [], "sources": [], "events": []}
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        pending = [(name, url, pool.submit(fetch)) for name, url, fetch in sources]
        for name, url, task in pending:
            try:
                items, events, warning = task.result()
            except (HTTPException, OSError, ValueError, ElementTree.ParseError) as exc:
                result["sources"].append({"name": name, "url": url, "ok": False, "error": str(exc)})
                continue
            result["items"].extend(items)
            result["events"].extend(events)
            result["sources"].append({"name": name, "url": url, "ok": True, "error": warning})
    # Both time stamps and Japanese site dates retain the precision supplied by the publisher.
    result["items"].sort(key=lambda i: i["published_at"], reverse=True)
    result["events"].sort(key=lambda e: e["start_at"])
    return result
