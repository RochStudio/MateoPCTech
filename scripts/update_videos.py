"""Pull latest videos from YouTube RSS feeds and rebuild the video sections.

Each channel's full video list lives in data/videos.json (the RSS feed only
carries the latest 15, so the JSON keeps older videos from falling off).
New feed entries are added to the top of the list and view counts are
refreshed for any video still in the feed, then every marked section is
regenerated:

  youtube.html    LATEST3:<key> / POPULAR3:<key> for both channels,
                  plus the full VIDEOS:mateopctech grid
  benchmarking.html  full VIDEOS:benchmarking grid
  index.html      LATEST (newest video from each channel)

Note: view counts for videos older than the feed's 15 entries stay frozen at
their last known value.
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "videos.json"

CHANNELS = [
    {"key": "mateopctech", "channel_id": "UCD3Pt35kAHzTV33K2yqwxpQ", "page": "youtube.html", "label": "Mateo PC Tech"},
    {"key": "benchmarking", "channel_id": "UCxLvCr1i21JT2uxkZr1XvcA", "page": "benchmarking.html", "label": "Mateo Benchmarking"},
]

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

CARD_TEMPLATE = """    <div class="video">
      <a href="https://www.youtube.com/watch?v={id}" target="_blank"><img src="https://i.ytimg.com/vi/{id}/hqdefault.jpg" alt="Video thumbnail"></a>
      <div class="info">
        <a href="https://www.youtube.com/watch?v={id}" target="_blank">{title}</a>{meta}
      </div>
    </div>"""


def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_views(views):
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M views"
    if views >= 1_000:
        return f"{views / 1_000:.1f}".rstrip("0").rstrip(".") + "K views"
    return f"{views} views"


def fetch_feed(channel_id):
    req = urllib.request.Request(
        FEED_URL.format(channel_id), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        tree = ET.fromstring(resp.read())
    videos = []
    for entry in tree.findall("atom:entry", NS):
        vid = entry.findtext("yt:videoId", namespaces=NS)
        title = entry.findtext("atom:title", namespaces=NS)
        stats = entry.find("media:group/media:community/media:statistics", NS)
        views = int(stats.get("views", 0)) if stats is not None else 0
        if vid and title:
            videos.append({"id": vid, "title": title, "views": views})
    return videos


def make_card(video, meta_text=None):
    meta = f'\n        <div class="meta">{meta_text}</div>' if meta_text else ""
    return CARD_TEMPLATE.format(
        id=video["id"], title=escape_html(video["title"]), meta=meta
    )


def rebuild_section(page_path, marker, cards):
    html = page_path.read_text(encoding="utf-8")
    start = f"<!-- {marker}:START -->"
    end = f"<!-- {marker}:END -->"
    if start not in html or end not in html:
        sys.exit(f"Marker '{marker}' not found in {page_path.name}")
    section = f'{start}\n  <div class="video-grid">\n\n' + "\n\n".join(cards) + f"\n\n  </div>\n  {end}"
    new_html = re.sub(
        re.escape(start) + r".*?" + re.escape(end), section, html, flags=re.DOTALL
    )
    if new_html != html:
        page_path.write_text(new_html, encoding="utf-8")
        return True
    return False


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    changed_pages = set()
    for ch in CHANNELS:
        known = data.get(ch["key"], [])
        known_by_id = {v["id"]: v for v in known}
        try:
            feed = fetch_feed(ch["channel_id"])
        except Exception as exc:
            print(f"WARNING: could not fetch feed for {ch['key']}: {exc}")
            feed = []
        fresh = []
        for v in feed:
            if v["id"] in known_by_id:
                if v["views"]:
                    known_by_id[v["id"]]["views"] = v["views"]
                known_by_id[v["id"]]["title"] = v["title"]
            else:
                fresh.append(v)
        if fresh:
            print(f"{ch['key']}: {len(fresh)} new video(s): " + ", ".join(v["title"] for v in fresh))
            data[ch["key"]] = fresh + known

        videos = data[ch["key"]]
        popular = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)

        # Full archive grid on the channel's own page
        if rebuild_section(ROOT / ch["page"], f"VIDEOS:{ch['key']}", [make_card(v) for v in videos]):
            changed_pages.add(ch["page"])

        # Overview rows on the YouTube tab
        yt = ROOT / "youtube.html"
        if rebuild_section(yt, f"LATEST3:{ch['key']}", [make_card(v) for v in videos[:3]]):
            changed_pages.add("youtube.html")
        if rebuild_section(
            yt,
            f"POPULAR3:{ch['key']}",
            [make_card(v, format_views(v.get("views", 0))) for v in popular[:3]],
        ):
            changed_pages.add("youtube.html")

    # Newest video from each channel on the home page
    latest_cards = [
        make_card(data[ch["key"]][0], f"From {ch['label']}")
        for ch in CHANNELS
        if data.get(ch["key"])
    ]
    if rebuild_section(ROOT / "index.html", "LATEST", latest_cards):
        changed_pages.add("index.html")

    DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Updated: " + (", ".join(sorted(changed_pages)) if changed_pages else "nothing to update"))


if __name__ == "__main__":
    main()
