#!/usr/bin/env python3
"""
Sincronizzatore RSS Substack per Geobasi.com:
- Interroga https://geobuzz.substack.com/feed
- Estrae tutti gli articoli, li ordina rigorosamente dal più recente al più vecchio
- Estrae titolo, link diretto, cover image (da tag enclosure), estratto pulito e data formattata
- Salva i dati in site/data/articles.json
"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import os
import sys
import email.utils
import datetime

SUBSTACK_FEED_URL = "https://geobuzz.substack.com/feed"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "articles.json")
MAX_ARTICLES = 6

MONTHS_IT = {
    1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mag", 6: "Giu",
    7: "Lug", 8: "Ago", 9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
}

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^<]+?>', '', raw_html)
    clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
    clean = clean.replace('&#233;', 'é').replace('&#224;', 'à').replace('&#242;', 'ò')
    clean = clean.replace('&#236;', 'ì').replace('&#249;', 'ù').replace('&#8217;', "'")
    clean = clean.replace('&#8220;', '"').replace('&#8221;', '"').replace('&#8230;', '...')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def fetch_articles():
    req = urllib.request.Request(
        SUBSTACK_FEED_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; GeobasiStaticSync/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Feed RSS Substack non valido o privo di tag channel")

    raw_items = []
    for item in channel.findall("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date_str = item.findtext("pubDate", "").strip()
        desc = item.findtext("description", "")

        enclosure = item.find("enclosure")
        cover_image = enclosure.get("url") if enclosure is not None else ""

        # Parse date RFC-822
        try:
            dt = email.utils.parsedate_to_datetime(pub_date_str)
        except Exception:
            dt = datetime.datetime.now(datetime.timezone.utc)

        excerpt = clean_html(desc)
        if len(excerpt) > 220:
            excerpt = excerpt[:217] + "..."

        formatted_date = f"{dt.day:02d} {MONTHS_IT.get(dt.month, '')} {dt.year}"

        raw_items.append({
            "datetime": dt,
            "title": title,
            "link": link,
            "date": formatted_date,
            "raw_date": pub_date_str,
            "excerpt": excerpt,
            "cover_image": cover_image
        })

    # Sort strictly descending (newest first)
    raw_items.sort(key=lambda x: x["datetime"], reverse=True)

    articles = []
    for it in raw_items[:MAX_ARTICLES]:
        articles.append({
            "title": it["title"],
            "link": it["link"],
            "date": it["date"],
            "raw_date": it["raw_date"],
            "excerpt": it["excerpt"],
            "cover_image": it["cover_image"]
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"Estratti e ordinati con successo {len(articles)} articoli in {OUTPUT_FILE}")
    return articles

if __name__ == "__main__":
    fetch_articles()
