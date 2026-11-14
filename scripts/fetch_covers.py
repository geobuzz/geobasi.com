#!/usr/bin/env python3
"""
Recuperatore e verificatore di copertine per la biblioteca di Geobasi.com:
- Verifica ed estrae copertine da Amazon CDN (tramite conversione ISBN-13 -> ISBN-10).
- Interroga Open Library Books API per copertine ad alta risoluzione.
- Supporta cataloghi e fonti specializzate per edizioni senza ISBN standard o con prefisso 979.
- Salva le copertine autentiche localmente in site/assets/img/covers/<isbn>.jpg per garantire caricamento istantaneo e affidabile.
- Aggiorna i percorsi relativi in site/data/books.json.
"""
import os
import sys
import json
import urllib.request
import re
import time

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
BOOKS_JSON = os.path.join(DATA_DIR, "books.json")
COVERS_DIR = os.path.join(BASE_DIR, "assets", "img", "covers")

def isbn13_to_isbn10(isbn13):
    if not isbn13 or len(isbn13) != 13 or not isbn13.startswith("978"):
        return None
    core = isbn13[3:12]
    try:
        check = sum((10 - i) * int(d) for i, d in enumerate(core)) % 11
        check_digit = "0" if check == 0 else ("X" if (11 - check) == 10 else str(11 - check))
        return core + check_digit
    except ValueError:
        return None

# Mappatura manuale curata per volumi privi di ISBN commerciale o con prefisso 979
SPECIAL_COVERS = {
    "9791254781715": "https://img.libreriadelsanto.it/books/q/QOV0vZ3yrXuU_s4-mb.jpg", # Credo - Athanasius Schneider
    "9791254781975": "https://images-na.ssl-images-amazon.com/images/I/71u9s2qGZXL.jpg", # Vangeli canonici
    "9791280131522": "https://img.libreriadelsanto.it/books/a/A9vOzrqz37gD_s4-mb.jpg", # L'educazione cristiana
    "9791280938206": "https://img.libreriadelsanto.it/books/f/fN4E5gOqL2bA_s4-mb.jpg", # La divina provvidenza
    "9788854126138": "https://images-na.ssl-images-amazon.com/images/P/8854126136.01.LZZZZZZZ.jpg", # Pirenne - Storia d'Europa
    "9791259920843": "https://images-na.ssl-images-amazon.com/images/I/71y9Tz2E-sL.jpg", # In solitaria - Wielicki
    "San Paolo": "https://covers.openlibrary.org/b/id/9644013-M.jpg",
    "La storia infinita": "https://covers.openlibrary.org/b/id/7383413-M.jpg",
    "La libertà e la legge": "https://covers.openlibrary.org/b/id/7890272-M.jpg",
    "2001 Odissea nello spazio": "https://covers.openlibrary.org/b/id/11344400-M.jpg",
    "L'inferno a rovescio": "https://covers.openlibrary.org/b/id/11105942-M.jpg",
    "Il Napoleone di Notting Hill": "https://covers.openlibrary.org/b/id/10534213-M.jpg",
    "Il pilota": "https://covers.openlibrary.org/b/id/10636603-M.jpg",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_and_save_cover(url, dest_path):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = resp.read()
            # Le risposte placeholder 1x1 di Amazon o Open Library sono inferiori a 1500 byte
            if len(data) > 1500:
                with open(dest_path, "wb") as f:
                    f.write(data)
                return True
    except Exception:
        pass
    return False

def sync_all_covers():
    os.makedirs(COVERS_DIR, exist_ok=True)
    
    if not os.path.exists(BOOKS_JSON):
        print(f"[ERRORE] File {BOOKS_JSON} non trovato.")
        return False

    with open(BOOKS_JSON, "r", encoding="utf-8") as f:
        books = json.load(f)

    updated_count = 0
    total_books = len(books)
    print(f"Avvio sincronizzazione e download copertine per {total_books} libri...")

    for idx, b in enumerate(books):
        title = b.get("title", "")
        author = b.get("author", "")
        isbn = (b.get("isbn") or "").strip()
        existing_cover = b.get("cover", "").strip()

        # Genera identificatore file univoco e pulito
        file_slug = isbn if isbn else re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:40].strip("_")
        dest_filename = f"{file_slug}.jpg"
        dest_path = os.path.join(COVERS_DIR, dest_filename)
        rel_path = f"assets/img/covers/{dest_filename}"

        # Se il file locale esiste già ed è valido (>1500 byte)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1500:
            if b.get("cover") != rel_path:
                b["cover"] = rel_path
                updated_count += 1
            continue

        success = False

        # 1. Mappatura speciale per volumi noti
        special_url = SPECIAL_COVERS.get(isbn) or SPECIAL_COVERS.get(title)
        if special_url:
            if fetch_and_save_cover(special_url, dest_path):
                b["cover"] = rel_path
                updated_count += 1
                success = True
                print(f"[{idx+1}/{total_books}] [SPECIALE] Copertina salvata per '{title}'")

        # 2. Se ha già una copertina Open Library valida, scarichiamola in locale
        if not success and existing_cover and existing_cover.startswith("http"):
            if fetch_and_save_cover(existing_cover, dest_path):
                b["cover"] = rel_path
                updated_count += 1
                success = True
                print(f"[{idx+1}/{total_books}] [CACHE] Salvata copertina da {existing_cover[:40]}... per '{title}'")

        # 3. Amazon CDN via ISBN-10
        if not success and isbn:
            isbn10 = isbn13_to_isbn10(isbn)
            if isbn10:
                amz_url = f"https://images-na.ssl-images-amazon.com/images/P/{isbn10}.01.LZZZZZZZ.jpg"
                if fetch_and_save_cover(amz_url, dest_path):
                    b["cover"] = rel_path
                    updated_count += 1
                    success = True
                    print(f"[{idx+1}/{total_books}] [AMAZON] Copertina salvata per '{title}' ({isbn})")

        # 4. Open Library via ISBN
        if not success and isbn:
            ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false"
            if fetch_and_save_cover(ol_url, dest_path):
                b["cover"] = rel_path
                updated_count += 1
                success = True
                print(f"[{idx+1}/{total_books}] [OPENLIBRARY] Copertina salvata per '{title}' ({isbn})")

    # Salva il file books.json aggiornato
    with open(BOOKS_JSON, "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2, ensure_ascii=False)

    total_with_covers = sum(1 for b in books if b.get("cover") and os.path.exists(os.path.join(BASE_DIR, b.get("cover"))))
    print(f"\n[FINE] Copertine sincronizzate: {total_with_covers}/{total_books} libri dotati di copertina reale salvata in locale.")
    return True

if __name__ == "__main__":
    sync_all_covers()
