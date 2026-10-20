"""Fetch market news + quotes, write docs/data/news.json, optional AI summary and ntfy push."""
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
ARCHIVE = DATA / "archive"
HEADERS = {"User-Agent": "Mozilla/5.0 (market-brief)"}
MAX_PER_REGION = 15
MAX_AGE = timedelta(hours=36)
KEEP_DAYS = 30
SITE_URL = os.environ.get("SITE_URL", "")


def clean(text, limit=220):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def norm(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())[:60]


def fetch_region(feeds):
    now = datetime.now(timezone.utc)
    items, seen = [], set()
    for f in feeds:
        try:
            r = requests.get(f["url"], headers=HEADERS, timeout=20)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
        except Exception as e:
            print(f"skip {f['source']}: {e}", file=sys.stderr)
            continue
        for e in parsed.entries:
            title = clean(e.get("title", ""), 200)
            link = e.get("link", "")
            if not title or not link.startswith("http"):
                continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            when = datetime.fromtimestamp(time.mktime(ts), timezone.utc) if ts else now
            if now - when > MAX_AGE:
                continue
            key = norm(title)
            if key in seen:
                continue
            seen.add(key)
            src = f["source"]
            if src == "Google News" and " - " in title:  # "Headline - Publisher"
                title, src = title.rsplit(" - ", 1)
            items.append({
                "title": title, "link": link, "source": src,
                "published": when.isoformat(),
                "snippet": "" if f["source"] == "Google News" else clean(e.get("summary", "")),
            })
    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:MAX_PER_REGION]


def fetch_quotes(quotes):
    out = []
    for q in quotes:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{q['symbol']}?range=5d&interval=1d"
            meta = requests.get(url, headers=HEADERS, timeout=15).json()["chart"]["result"][0]["meta"]
            price, prev = meta["regularMarketPrice"], meta.get("chartPreviousClose")
            chg = round((price - prev) / prev * 100, 2) if prev else None
            out.append({"name": q["name"], "price": round(price, 2), "change_pct": chg})
        except Exception as e:
            print(f"quote {q['symbol']} failed: {e}", file=sys.stderr)
    return out


def ai_summary(news):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    lines = []
    for region in ("india", "usa"):
        lines.append(region.upper() + " headlines:")
        lines += [f"- {n['title']}" for n in news[region]]
    prompt = (
        "You are a market news editor for a beginner investor. Using ONLY these headlines, write "
        "two sections 'India' and 'USA', each with 3-4 short bullets on what moved markets today. "
        "Plain language, no advice, no invented numbers.\n\n" + "\n".join(lines)
    )
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers={"x-goog-api-key": key}, timeout=60,
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"ai summary skipped: {e}", file=sys.stderr)
        return None


def notify(news):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    body = "India:\n" + "\n".join(f"- {n['title']}" for n in news["india"][:3])
    body += "\n\nUSA:\n" + "\n".join(f"- {n['title']}" for n in news["usa"][:3])
    headers = {"Title": f"Market Brief {news['date']}", "Tags": "chart_with_upwards_trend"}
    if SITE_URL:
        headers["Click"] = SITE_URL
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"),
                      headers=headers, timeout=20).raise_for_status()
    except Exception as e:
        print(f"ntfy failed: {e}", file=sys.stderr)


def prune_archive():
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).date().isoformat()
    for p in ARCHIVE.glob("*.json"):
        if p.stem < cutoff:
            p.unlink()
    dates = sorted((p.stem for p in ARCHIVE.glob("*.json")), reverse=True)
    (DATA / "archive_index.json").write_text(json.dumps(dates), encoding="utf-8")


def main():
    cfg = json.loads((ROOT / "scripts" / "feeds.json").read_text(encoding="utf-8"))
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    news = {
        "date": ist.date().isoformat(),
        "updated": datetime.now(timezone.utc).isoformat(),
        "quotes": fetch_quotes(cfg["quotes"]),
        "india": fetch_region(cfg["india"]),
        "usa": fetch_region(cfg["usa"]),
    }
    if not news["india"] and not news["usa"]:
        print("no news fetched; keeping previous data", file=sys.stderr)
        return 1
    summary = ai_summary(news)
    if summary:
        news["summary"] = summary
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    text = json.dumps(news, ensure_ascii=False, indent=1)
    (DATA / "news.json").write_text(text, encoding="utf-8")
    (ARCHIVE / f"{news['date']}.json").write_text(text, encoding="utf-8")
    prune_archive()
    notify(news)
    print(f"ok: {len(news['india'])} india, {len(news['usa'])} usa, {len(news['quotes'])} quotes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
