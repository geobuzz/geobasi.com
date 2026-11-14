#!/usr/bin/env python3
"""
Sincronizzatore ufficiale Anobii v6 API per Geobasi.com:
- Autenticazione diretta via OAuth2 client_credentials verso https://v6.api.anobii.com/auth/token.
- Scaricamento in tempo reale dell'intera libreria personale dell'utente (141+ libri).
- Estrazione esatta dello stato di lettura nativo (started, finished, abandoned, not_started).
- Estrazione delle date reali (start/end/last_finish_date), valutazioni (stelle) e recensioni complete.
- Conservazione o scaricamento delle copertine autentiche in assets/img/covers/.
- Aggiornamento deterministico di site/data/books.json.
"""
import os
import sys
import json
import urllib.request
import re
import time

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
BOOKS_JSON_PATH = os.path.join(DATA_DIR, "books.json")
COVERS_DIR = os.path.join(BASE_DIR, "assets", "img", "covers")

ANOBII_USER_ID = "01d6d75099d9c1d4bb"
ANOBII_CLIENT_ID = "6cb3a6ab746f553c4330b74906ba55cb"
ANOBII_CLIENT_SECRET = "fG3d1y1izNS5cZlClKkxm5bC1MjQch5z"
API_BASE = "https://v6.api.anobii.com"

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def clean_html_markup(text):
    if not text:
        return ""
    clean = re.sub(r'<br\s*/?>', '\n', text)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
    clean = clean.replace('&#233;', 'é').replace('&#224;', 'à').replace('&#242;', 'ò')
    clean = clean.replace('&#236;', 'ì').replace('&#249;', 'ù').replace('&#8217;', "'")
    clean = clean.replace('&apos;', "'")
    return clean.strip()

def get_anobii_token():
    url = f"{API_BASE}/auth/token"
    payload = json.dumps({
        "grant_type": "client_credentials",
        "client_id": ANOBII_CLIENT_ID,
        "client_secret": ANOBII_CLIENT_SECRET
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", **HEADERS_BASE}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["result"]["token"]

def fetch_anobii_library():
    token = get_anobii_token()
    auth_headers = {"Authorization": f"Bearer {token}", **HEADERS_BASE}

    all_editions = []
    page = 0
    limit = 25

    print(f"[ANOBII API] Interrogazione libreria live per utente {ANOBII_USER_ID}...")

    while True:
        url = f"{API_BASE}/users/{ANOBII_USER_ID}/library?limit={limit}&page={page}"
        req = urllib.request.Request(url, headers=auth_headers)
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            res = data.get("result", {})
            eds = res.get("edition_list", [])
            if not eds:
                break
            all_editions.extend(eds)
            total = res.get("edition_total", 0)
            print(f"  * Pagina {page}: ricevuti {len(eds)} libri (totale: {len(all_editions)}/{total})")
            if len(all_editions) >= total:
                break
            page += 1
            time.sleep(0.2)

    print(f"[ANOBII API] Recuperati {len(all_editions)} libri in tempo reale.")
    return all_editions

def sync_anobii_data():
    os.makedirs(COVERS_DIR, exist_ok=True)
    editions = fetch_anobii_library()

    # Mappa copertine esistenti per preservare i file già scaricati
    existing_covers_map = {}
    if os.path.exists(BOOKS_JSON_PATH):
        try:
            with open(BOOKS_JSON_PATH, "r", encoding="utf-8") as f:
                old_books = json.load(f)
                for b in old_books:
                    key = (b.get("isbn") or b.get("title", "")).strip().lower()
                    if b.get("cover"):
                        existing_covers_map[key] = b.get("cover")
        except Exception:
            pass

    processed_books = []

    for ed in editions:
        title = (ed.get("title") or "").strip()
        subtitle = (ed.get("subtitle") or "").strip()
        authors_list = [a.get("name", "").strip() for a in ed.get("authors", []) if a.get("name")]
        author = ", ".join(authors_list)
        publisher = (ed.get("publisher") or "").strip()
        isbn = (ed.get("ean") or ed.get("isbn") or "").strip()

        KNOWN_AUTHORS = {
            "9788849884753": "Mario Caligiuri (a cura di)",
            "9791254781975": "Mons. Angelo Galli (a cura di)",
            "9788884042996": "Anonimo",
            "A000012821": "Ruggiero Romano, Corrado Vivanti (a cura di)"
        }
        if not author:
            if isbn in KNOWN_AUTHORS:
                author = KNOWN_AUTHORS[isbn]
            elif publisher:
                author = f"AA.VV. ({publisher})"
        format_name = ed.get("format", {}).get("name", "")
        pages = ed.get("pages_count")
        publish_date = ed.get("publish_date") or ""

        url_part = ed.get("url") or ""
        anobii_url = f"https://www.anobii.com/it{url_part}" if url_part else f"https://www.anobii.com/it/{ANOBII_USER_ID}/profile"

        up = ed.get("user_personal", {})
        rs_dict = up.get("reading_status") if isinstance(up.get("reading_status"), dict) else {}
        raw_status = rs_dict.get("status")

        start_date = rs_dict.get("start")
        end_date = rs_dict.get("end") or up.get("last_finish_date")

        # Mappatura dello stato canonico
        if raw_status == "started":
            status = "in_corso"
            status_raw = f"In lettura dal {start_date}" if start_date else "In lettura"
        elif raw_status == "finished":
            status = "letto"
            status_raw = f"Finito nel {end_date}" if end_date else "Letto"
        elif raw_status == "abandoned":
            status = "abbandonato"
            status_raw = f"Abbandonato nel {end_date}" if end_date else "Abbandonato"
        elif raw_status in ("not_started", "not_finished"):
            status = "da_leggere"
            status_raw = "Da leggere"
        else:
            status = "letto" if end_date else "da_leggere"
            status_raw = f"Finito nel {end_date}" if end_date else ""

        # Rating (stelle)
        stars = float(up.get("stars") or 0)

        # Recensione / Note critiche
        last_rev = up.get("last_review") or {}
        rev_title = clean_html_markup(last_rev.get("title") or "")
        rev_desc = clean_html_markup(last_rev.get("description") or "")
        
        if rev_title and rev_desc:
            review_full = f"{rev_title}: {rev_desc}"
        else:
            review_full = rev_desc or rev_title

        # Gestione copertina
        lookup_key = (isbn or title).strip().lower()
        cover_path = existing_covers_map.get(lookup_key)

        file_slug = isbn if isbn else re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:40].strip("_")
        dest_filename = f"{file_slug}.jpg"
        local_dest = os.path.join(COVERS_DIR, dest_filename)
        rel_dest = f"assets/img/covers/{dest_filename}"

        if os.path.exists(local_dest) and os.path.getsize(local_dest) > 1500:
            cover_path = rel_dest
        elif not cover_path:
            anobii_img_url = ed.get("share", {}).get("image_url")
            cover_path = anobii_img_url or ""

        book_record = {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "isbn": isbn,
            "status": status,
            "status_raw": status_raw,
            "start_date": start_date or (up.get("added_at")[:10] if up.get("added_at") else None),
            "end_date": end_date,
            "rating": stars,
            "review": review_full,
            "publisher": publisher,
            "publish_date": publish_date,
            "pages": pages,
            "format": format_name,
            "cover": cover_path or "",
            "anobii_url": anobii_url
        }
        processed_books.append(book_record)

    # Scrittura di books.json
    with open(BOOKS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(processed_books, f, indent=2, ensure_ascii=False)

    print(f"[COMPLETATO] Aggiornato {BOOKS_JSON_PATH} con {len(processed_books)} libri reali da Anobii API v6.")
    return True

if __name__ == "__main__":
    sync_anobii_data()
