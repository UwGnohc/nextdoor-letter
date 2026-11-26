"""Merge independent public sources while retaining the last successful reads."""
from datetime import datetime, timedelta, timezone

from editorial import enrich
from community_titles import chinese_title
from translate import title_language

CHINA = timezone(timedelta(hours=8))


COMMUNITY_LINKS = [
    {"name": "哔哩哔哩 · 视频与二创", "url": "https://search.bilibili.com/all?keyword=BOYNEXTDOOR"},
    {"name": "微博 · 话题讨论", "url": "https://s.weibo.com/weibo?q=BOYNEXTDOOR"},
    {"name": "Dcard · BOYNEXTDOOR 板", "url": "https://www.dcard.tw/f/boynextdoor", "region": "台湾", "language": "zh-Hant"},
]


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
