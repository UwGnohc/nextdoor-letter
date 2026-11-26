"""Build the two static files served by GitHub Pages."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import re

from community import fetch_community
from community_media import fetch_media
from feeds import fetch_all
from reader import merge, neighbor_snapshot
from world_feeds import fetch_world


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".state" / "data.json"
DIST = ROOT / "public"
ARTICLE_FIELDS = ("id", "title", "title_zh", "summary_zh", "url", "source", "kind",
                  "published_at", "members", "language", "region", "translation_provider")
EVENT_FIELDS = ("title", "title_zh", "url", "source", "start_at", "end_at")
SOURCE_FIELDS = ("name", "url", "ok", "updated_at", "mode", "region", "language", "provider")


def fields(row, names):
    return {key: row[key] for key in names if key in row}


def clean(section):
    result = {
        "items": [fields(row, ARTICLE_FIELDS) for row in section["items"]],
        "sources": [{**fields(row, SOURCE_FIELDS), "error": "本次未能完整更新" if row.get("error") else ""}
                    for row in section["sources"]],
        "updated_at": section["updated_at"],
    }
    if "events" in section:
        result["events"] = [fields(row, EVENT_FIELDS) for row in section["events"]]
    return result


def collect(previous):
    with ThreadPoolExecutor(max_workers=4) as pool:
        official = pool.submit(fetch_all)
        feeds = [(name, pool.submit(fetch)) for name, fetch in
                 (("粉丝社区", fetch_community), ("中文媒体", fetch_media), ("各地社区", fetch_world))]
        news = merge(previous, official.result())
        discussions = neighbor_snapshot(previous["community"], feeds)
    old_titles = {(r["id"], r["title"]): r for r in previous["community"]["items"] if r.get("title_zh")}
    for row in discussions["items"]:
        saved = old_titles.get((row["id"], row["title"]))
        if saved and not row.get("title_zh"):
            row["title_zh"] = saved["title_zh"]
    return {**clean(news), "community": clean(discussions),
            "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def render(data, output):
    output.mkdir(exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    html, count = re.subn(r'(<script type="application/json" id="initial-data">).*?(</script>)',
                          lambda match: match[1] + encoded.replace("<", r"\u003c") + match[2],
                          html, flags=re.DOTALL)
    if count != 1:
        raise ValueError("Missing edition container in index.html")
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / "data.json").write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    source = CACHE if CACHE.exists() else ROOT / "data.json"
    previous = json.loads(source.read_text(encoding="utf-8"))
    edition = collect(previous)
    render(edition, DIST)
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_bytes((DIST / "data.json").read_bytes())
    print(f"Published {len(edition['items'])} news items and {len(edition['community']['items'])} discussions.")
