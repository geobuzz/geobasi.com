#!/usr/bin/env python3
"""
Sincronizzatore della biblioteca Anobii per Geobasi.com:
- Importa l'esportazione ufficiale CSV da Anobii (Libreria -> Impostazioni -> Esporta libreria CSV).
- Esegue il match conservativo per ISBN o titolo/autore normalizzato.
- Preserva recensioni arricchite, citazioni personali e valutazioni.
- Non inventa alcun contenuto mancante.
- Recupera le copertine tramite ISBN su Open Library Covers API verificando con default=false
  che l'immagine esista realmente e non sia un pixel vuoto (HTTP 404).
- Gestisce i libri non presenti nel CSV segnalandoli nel report come selezioni editoriali
  senza cancellarli silenziosamente, consentendo la rimozione solo con flag esplicito --prune.
"""
import csv
import json
import os
import sys
import argparse
import urllib.request
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
BOOKS_JSON_PATH = os.path.join(DATA_DIR, "books.json")
ANOBII_PROFILE = "https://www.anobii.com/it/01d6d75099d9c1d4bb/profile"

def normalize_text(text):
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def verify_and_get_cover_url(isbn):
    if not isbn:
        return ""
    clean_isbn = re.sub(r'[^0-9X]', '', isbn.upper())
    if not clean_isbn:
        return ""

    test_url = f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-M.jpg?default=false"
    try:
        req = urllib.request.Request(test_url, headers={"User-Agent": "GeobasiSync/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                # OpenLibrary image exists
                return f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-M.jpg"
    except Exception:
        pass
    return ""

def import_anobii_csv(csv_path, prune=False):
    if not os.path.exists(csv_path):
        print(f"Errore: file CSV non trovato {csv_path}")
        return False, "File CSV non trovato"

    # Load existing books
    existing_books = []
    if os.path.exists(BOOKS_JSON_PATH):
        with open(BOOKS_JSON_PATH, "r", encoding="utf-8") as f:
            existing_books = json.load(f)

    # Index existing books by ISBN and by normalized title+author
    isbn_map = {}
    title_map = {}
    for idx, b in enumerate(existing_books):
        b_isbn = re.sub(r'[^0-9X]', '', (b.get("isbn") or "").upper())
        if b_isbn:
            isbn_map[b_isbn] = idx
        t_key = normalize_text(b.get("title", "")) + normalize_text(b.get("author", ""))
        title_map[t_key] = idx

    incoming_rows = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Title") or row.get("Titolo") or ""
            author = row.get("Author") or row.get("Autore") or ""
            isbn = row.get("ISBN") or row.get("ISBN13") or ""
            status_raw = (row.get("Status") or row.get("Stato") or "").lower()
            rating_raw = row.get("Rating") or row.get("Valutazione") or "0"
            review = row.get("Review") or row.get("Recensione") or row.get("Comment") or ""
            quote = row.get("Quote") or row.get("Citazione") or ""

            if title.strip():
                status = "in_corso" if any(w in status_raw for w in ["leggendo", "reading", "in corso", "started"]) else "letto"
                try:
                    rating = int(float(rating_raw))
                except ValueError:
                    rating = 0

                incoming_rows.append({
                    "title": title.strip(),
                    "author": author.strip(),
                    "isbn": isbn.strip(),
                    "status": status,
                    "rating": rating,
                    "review": review.strip(),
                    "quote": quote.strip()
                })

    matched_indices = set()
    added_books = []
    updated_count = 0
    preserved_count = 0

    for inc in incoming_rows:
        inc_isbn = re.sub(r'[^0-9X]', '', inc["isbn"].upper())
        inc_key = normalize_text(inc["title"]) + normalize_text(inc["author"])

        target_idx = None
        if inc_isbn and inc_isbn in isbn_map:
            target_idx = isbn_map[inc_isbn]
        elif inc_key in title_map:
            target_idx = title_map[inc_key]

        if target_idx is not None:
            # Match existing book: Conservative merge
            matched_indices.add(target_idx)
            curr = existing_books[target_idx]

            curr["status"] = inc["status"]
            if inc["rating"] > 0:
                curr["rating"] = inc["rating"]
            if inc["isbn"] and not curr.get("isbn"):
                curr["isbn"] = inc["isbn"]

            # Preserve existing note/quote if incoming is empty
            if inc["review"]:
                curr["note"] = inc["review"]
            if inc["quote"]:
                curr["quote"] = inc["quote"]

            # If cover is missing or broken, try fetching
            if not curr.get("cover") and curr.get("isbn"):
                cover = verify_and_get_cover_url(curr.get("isbn"))
                if cover:
                    curr["cover"] = cover

            updated_count += 1
        else:
            # New book from Anobii CSV
            cover_url = verify_and_get_cover_url(inc["isbn"]) if inc["isbn"] else ""
            new_book = {
                "title": inc["title"],
                "author": inc["author"],
                "status": inc["status"],
                "rating": inc["rating"],
                "isbn": inc["isbn"],
                "note": inc["review"],
                "quote": inc["quote"],
                "cover": cover_url,
                "anobii_url": ANOBII_PROFILE
            }
            added_books.append(new_book)

    # Check books present in books.json but missing from Anobii CSV
    missing_from_csv = [b for i, b in enumerate(existing_books) if i not in matched_indices]

    if missing_from_csv:
        print(f"\n[REPORT VERIFICA RIMODULAZIONI / RIMODULAZIONI]")
        print(f"Rilevati {len(missing_from_csv)} libri presenti nel sito ma non inclusi nel CSV Anobii:")
        for m in missing_from_csv:
            print(f"  * '{m.get('title')}' di {m.get('author')}")

        if prune:
            print("Flag --prune attivo: rimozione applicata ai libri non presenti nel CSV.")
            final_books = [b for i, b in enumerate(existing_books) if i in matched_indices] + added_books
        else:
            print("Flag --prune non specificato: i libri sono stati CONSERVATI come selezioni editoriali del sito.")
            final_books = existing_books + added_books
    else:
        final_books = existing_books + added_books

    # Save books.json
    with open(BOOKS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(final_books, f, indent=2, ensure_ascii=False)

    summary = f"Anobii Sync: {updated_count} aggiornati, {len(added_books)} aggiunti, {len(missing_from_csv)} mantenuti come editoriali"
    print(f"\n[COMPLETATO] {summary}")
    return True, summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincronizzatore Biblioteca Anobii per Geobasi.com")
    parser.add_argument("--import-csv", dest="csv_file", required=True, help="Percorso del file CSV esportato da Anobii")
    parser.add_argument("--prune", action="store_true", help="Rimuovi dal sito i libri non più presenti nel CSV di Anobii")
    args = parser.parse_args()

    success, msg = import_anobii_csv(args.csv_file, args.prune)
    if not success:
        sys.exit(1)
