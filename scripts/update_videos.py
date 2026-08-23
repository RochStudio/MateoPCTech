"""Pull latest videos from YouTube RSS feeds and rebuild the video grids.

Each channel's full video list lives in data/videos.json (the RSS feed only
carries the latest 15, so the JSON keeps older videos from falling off).
New feed entries are added to the top of the list, then the grid between the
VIDEOS:<key>:START / END markers in each page is regenerated.
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
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

CARD_TEMPLATE = """    <div class="video">
      <a href="https://www.youtube.com/watch?v={id}" target="_blank"><img src="https://i.ytimg.com/vi/{id}/hqdefault.jpg" alt="Video thumbnail"></a>
      <div class="info">
        <a href="https://www.youtube.com/watch?v={id}" target="_blank">{title}</a>
      </div>
    </div>"""


def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
        if vid and title:
            videos.append({"id": vid, "title": title})
    return videos


def rebuild_grid(page_path, key, videos):
    html = page_path.read_text(encoding="utf-8")
    start = f"<!-- VIDEOS:{key}:START -->"
    end = f"<!-- VIDEOS:{key}:END -->"
    if start not in html or end not in html:
        sys.exit(f"Markers for '{key}' not found in {page_path.name}")
    cards = "\n\n".join(
        CARD_TEMPLATE.format(id=v["id"], title=escape_html(v["title"])) for v in videos
    )
    grid = f'{start}\n  <div class="video-grid">\n\n{cards}\n\n  </div>\n  {end}'
    new_html = re.sub(
        re.escape(start) + r".*?" + re.escape(end), grid, html, flags=re.DOTALL
    )
    if new_html != html:
        page_path.write_text(new_html, encoding="utf-8")
        return True
    return False


LATEST_TEMPLATE = """    <div class="video">
      <a href="https://www.youtube.com/watch?v={id}" target="_blank"><img src="https://i.ytimg.com/vi/{id}/hqdefault.jpg" alt="Video thumbnail"></a>
      <div class="info">
        <a href="https://www.youtube.com/watch?v={id}" target="_blank">{title}</a>
        <div class="meta">From {label}</div>
      </div>
    </div>"""


def rebuild_latest(data):
    page_path = ROOT / "index.html"
    html = page_path.read_text(encoding="utf-8")
    start, end = "<!-- LATEST:START -->", "<!-- LATEST:END -->"
    if start not in html or end not in html:
        sys.exit("LATEST markers not found in index.html")
    cards = "\n\n".join(
        LATEST_TEMPLATE.format(
            id=data[ch["key"]][0]["id"],
            title=escape_html(data[ch["key"]][0]["title"]),
            label=ch["label"],
        )
        for ch in CHANNELS
        if data.get(ch["key"])
    )
    section = f'{start}\n  <div class="video-grid">\n\n{cards}\n\n  </div>\n  {end}'
    new_html = re.sub(
        re.escape(start) + r".*?" + re.escape(end), section, html, flags=re.DOTALL
    )
    if new_html != html:
        page_path.write_text(new_html, encoding="utf-8")
        return True
    return False


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    changed_pages = []
    for ch in CHANNELS:
        known = data.get(ch["key"], [])
        known_ids = {v["id"] for v in known}
        try:
            feed = fetch_feed(ch["channel_id"])
        except Exception as exc:
            print(f"WARNING: could not fetch feed for {ch['key']}: {exc}")
            feed = []
        fresh = [v for v in feed if v["id"] not in known_ids]
        if fresh:
            print(f"{ch['key']}: {len(fresh)} new video(s): " + ", ".join(v["title"] for v in fresh))
            data[ch["key"]] = fresh + known
        if rebuild_grid(ROOT / ch["page"], ch["key"], data[ch["key"]]):
            changed_pages.append(ch["page"])
    if rebuild_latest(data):
        changed_pages.append("index.html")
    DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Updated: " + (", ".join(changed_pages) if changed_pages else "nothing to update"))


if __name__ == "__main__":
    main()
