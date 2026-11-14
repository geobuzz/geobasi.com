#!/usr/bin/env python3
"""
Fetch recent articles from Substack RSS feed and save them to data/articles.json
"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import os
import sys

SUBSTACK_FEED_URL = "https://geobuzz.substack.com/feed"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "articles.json")
MAX_ARTICLES = 6

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
    with urllib.request.urlopen(req) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    channel = root.find("channel")
    if channel is None:
        print("Error: invalid RSS feed")
        sys.exit(1)

    articles = []
    for item in channel.findall("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        desc = item.findtext("description", "")

        enclosure = item.find("enclosure")
        cover_image = enclosure.get("url") if enclosure is not None else ""

        date_match = re.search(r'\d{1,2}\s+[A-Za-z]{3}\s+\d{4}', pub_date)
        formatted_date = date_match.group(0) if date_match else pub_date

        excerpt = clean_html(desc)
        if len(excerpt) > 220:
            excerpt = excerpt[:217] + "..."

        articles.append({
            "title": title,
            "link": link,
            "date": formatted_date,
            "raw_date": pub_date,
            "excerpt": excerpt,
            "cover_image": cover_image
        })

        if len(articles) >= MAX_ARTICLES:
            break

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"Aggiornati con successo {len(articles)} articoli in {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_articles()
