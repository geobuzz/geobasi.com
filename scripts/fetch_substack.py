#!/usr/bin/env python3
"""
Sincronizzatore Substack per Geobasi.com:
- Interroga https://geobuzz.substack.com/feed con gestione robusta degli errori e retry anti-403.
- In caso di errore o indisponibilità di rete, preserva tassativamente l'archivio esistente in data/articles.json.
- Estrae sia i metadati (titolo, data RFC-822, cover image, estratto) sia il testo integrale (content:encoded).
- Genera per ciascun articolo una pagina di lettura interna permanente in site/articoli/<slug>.html.
- Ordina rigorosamente gli articoli per data decrescente (newest first).
"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import os
import sys
import email.utils
import datetime
import time

SUBSTACK_FEED_URL = "https://geobuzz.substack.com/feed"
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "articles.json")
ARTICOLI_DIR = os.path.join(BASE_DIR, "articoli")
MAX_ARTICLES = 12

MONTHS_IT = {
    1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mag", 6: "Giu",
    7: "Lug", 8: "Ago", 9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
}

def slugify(title):
    s = title.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')[:60]

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

def render_article_page(article):
    slug = article["slug"]
    os.makedirs(ARTICOLI_DIR, exist_ok=True)
    out_path = os.path.join(ARTICOLI_DIR, f"{slug}.html")

    cover_markup = ""
    if article.get("cover_image"):
        cover_markup = f'<div class="article-hero-cover"><img src="{article["cover_image"]}" alt="{article["title"]}"></div>'

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{article['title']} — Christian Bazzucchi | geobasi.com</title>
  <meta name="description" content="{article['excerpt']}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-paper: #FBF9F4;
      --bg-surface: #F3ECE1;
      --border-carto: #DDD5C7;
      --ink-primary: #12222E;
      --ink-secondary: #3D505D;
      --ink-muted: #6B7C87;
      --accent-copper: #C25928;
      --font-serif: "Newsreader", Georgia, serif;
      --font-sans: "Plus Jakarta Sans", system-ui, sans-serif;
      --font-mono: "Fira Code", monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg-paper);
      color: var(--ink-primary);
      font-family: var(--font-sans);
      font-size: 17px;
      line-height: 1.7;
    }}
    .wrapper {{
      max-width: 820px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }}
    .back-nav {{
      margin-bottom: 32px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-carto);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: var(--font-mono);
      font-size: 13px;
    }}
    .back-nav a {{
      color: var(--accent-copper);
      text-decoration: none;
      font-weight: 600;
    }}
    .back-nav a:hover {{ text-decoration: underline; }}
    .article-header {{
      margin-bottom: 32px;
    }}
    .article-meta {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--ink-muted);
      margin-bottom: 12px;
    }}
    .article-title {{
      font-family: var(--font-serif);
      font-size: 40px;
      line-height: 1.2;
      font-weight: 600;
      color: var(--ink-primary);
      margin-bottom: 16px;
    }}
    .article-hero-cover {{
      margin: 28px 0;
      border-radius: 2px;
      overflow: hidden;
      border: 1px solid var(--border-carto);
    }}
    .article-hero-cover img {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .article-body {{
      font-size: 18px;
      line-height: 1.8;
      color: var(--ink-secondary);
    }}
    .article-body p {{ margin-bottom: 24px; }}
    .article-body h2, .article-body h3 {{
      font-family: var(--font-serif);
      color: var(--ink-primary);
      margin: 36px 0 16px;
    }}
    .article-body blockquote {{
      border-left: 3px solid var(--accent-copper);
      padding-left: 18px;
      margin: 24px 0;
      font-family: var(--font-serif);
      font-style: italic;
      color: var(--ink-primary);
    }}
    .article-body img {{
      max-width: 100%;
      height: auto;
      border: 1px solid var(--border-carto);
      margin: 20px 0;
    }}
    .original-source-box {{
      margin-top: 50px;
      padding: 24px;
      background: var(--bg-surface);
      border: 1px solid var(--border-carto);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .original-source-box p {{
      font-size: 14px;
      color: var(--ink-muted);
      margin: 0;
    }}
    .btn-source {{
      font-family: var(--font-mono);
      font-size: 12px;
      background: var(--ink-primary);
      color: #FFF;
      padding: 8px 16px;
      text-decoration: none;
      border-radius: 2px;
    }}
    .btn-source:hover {{ background: var(--accent-copper); }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="back-nav">
      <a href="../index.html#appunti">&larr; Torna a Geobasi.com</a>
      <span>Appunti da Substack</span>
    </div>

    <article>
      <header class="article-header">
        <div class="article-meta">{article['date']} &bull; Christian Bazzucchi</div>
        <h1 class="article-title">{article['title']}</h1>
      </header>

      {cover_markup}

      <div class="article-body">
        {article['content_html']}
      </div>

      <div class="original-source-box">
        <p>Pubblicato originariamente su <strong>geobuzz.substack.com</strong>.</p>
        <a href="{article['link']}" class="btn-source" target="_blank" rel="noopener">Consulta su Substack originale &nearr;</a>
      </div>
    </article>
  </div>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path

def fetch_articles():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    xml_data = None
    last_err = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(SUBSTACK_FEED_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                xml_data = resp.read()
            break
        except urllib.error.HTTPError as e:
            last_err = e
            print(f"[SUBSTACK] Tentativo {attempt}/3 fallito: HTTP {e.code}")
            time.sleep(2 * attempt)
        except Exception as e:
            last_err = e
            print(f"[SUBSTACK] Tentativo {attempt}/3 fallito: {e}")
            time.sleep(2 * attempt)

    if xml_data is None:
        if os.path.exists(OUTPUT_FILE):
            print(f"[SUBSTACK] Impossibile raggiungere il feed ({last_err}). Mantenuto l'archivio esistente.")
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        raise RuntimeError(f"Errore recupero feed Substack: {last_err}")

    root = ET.fromstring(xml_data)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Feed RSS Substack non valido o privo di tag channel")

    namespaces = {'content': 'http://purl.org/rss/1.0/modules/content/'}
    raw_items = []

    for item in channel.findall("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date_str = item.findtext("pubDate", "").strip()
        desc = item.findtext("description", "")
        
        # Testo completo content:encoded
        content_encoded = item.find("content:encoded", namespaces)
        content_html = content_encoded.text if content_encoded is not None and content_encoded.text else desc

        enclosure = item.find("enclosure")
        cover_image = enclosure.get("url") if enclosure is not None else ""

        try:
            dt = email.utils.parsedate_to_datetime(pub_date_str)
        except Exception:
            dt = datetime.datetime.now(datetime.timezone.utc)

        excerpt = clean_html(desc)
        if len(excerpt) > 220:
            excerpt = excerpt[:217] + "..."

        formatted_date = f"{dt.day:02d} {MONTHS_IT.get(dt.month, '')} {dt.year}"
        slug = slugify(title)

        raw_items.append({
            "datetime": dt,
            "title": title,
            "slug": slug,
            "link": link,
            "date": formatted_date,
            "raw_date": pub_date_str,
            "excerpt": excerpt,
            "cover_image": cover_image,
            "content_html": content_html,
            "internal_url": f"articoli/{slug}.html"
        })

    # Ordinamento decrescente
    raw_items.sort(key=lambda x: x["datetime"], reverse=True)

    articles = []
    for it in raw_items[:MAX_ARTICLES]:
        # Genera la pagina interna
        render_article_page(it)
        articles.append({
            "title": it["title"],
            "slug": it["slug"],
            "link": it["link"],
            "internal_url": it["internal_url"],
            "date": it["date"],
            "raw_date": it["raw_date"],
            "excerpt": it["excerpt"],
            "cover_image": it["cover_image"]
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"Estratti, salvati e compilati {len(articles)} articoli con pagine di dettaglio interne.")
    return articles

if __name__ == "__main__":
    fetch_articles()
