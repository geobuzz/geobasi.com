#!/usr/bin/env python3
"""
Sincronizzatore della biblioteca Anobii per Geobasi.com:
- Supporta nativamente l'esportazione ufficiale di Anobii (inclusi i file con byte nulli/encoding cp1252/utf-16).
- Campi Anobii gestiti: ISBN, Titolo, Sottotitolo, Autore, Editore, Formato, Stato di lettura, Voto, Titolo Commento, Contenuto Commento.
- Supporta anche i file Goodreads/StoryGraph (Title, Author, ISBN, My Rating, Bookshelves, My Review).
- Non inventa MAI citazioni o testi non presenti nell'esportazione originale.
- Preserva note e arricchimenti esistenti qualora il CSV in ingresso presenti campi vuoti.
- Verifica le copertine reali tramite Open Library Books API (default=false per evitare pixel vuoti).
- Gestisce i libri rimossi: segnalazione analitica e rimozione consentita ESCLUSIVAMENTE con flag esplicito --prune.
"""
import csv
import json
import os
import sys
import io
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

def clean_isbn(isbn_str):
    if not isbn_str:
        return ""
    digits = re.sub(r'[^0-9X]', '', isbn_str.upper())
    return digits if len(digits) in (10, 13) else ""

def verify_and_get_cover_url(isbn):
    clean = clean_isbn(isbn)
    if not clean:
        return ""

    test_url = f"https://covers.openlibrary.org/b/isbn/{clean}-M.jpg?default=false"
    try:
        req = urllib.request.Request(test_url, headers={"User-Agent": "GeobasiSync/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                return f"https://covers.openlibrary.org/b/isbn/{clean}-M.jpg"
    except Exception:
        pass
    return ""

def read_anobii_or_generic_csv(csv_path):
    with open(csv_path, "rb") as f:
        raw = f.read()

    # Rimuove byte nulli spuri tipici di export Anobii Windows
    clean_bytes = raw.replace(b'\x00', b'')

    text = None
    for enc in ['utf-8-sig', 'utf-8', 'cp1252', 'latin1']:
        try:
            text = clean_bytes.decode(enc)
            break
        except Exception:
            continue

    if text is None:
        raise ValueError(f"Impossibile decodificare il file CSV {csv_path}")

    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for r in reader:
        # Rileva colonne Anobii ufficiali o Goodreads
        title = r.get("Titolo") or r.get("Title") or ""
        subtitle = r.get("Sottotitolo") or r.get("Subtitle") or ""
        author = r.get("Autore") or r.get("Author") or ""
        isbn = r.get("ISBN") or r.get("ISBN13") or ""
        status_raw = r.get("Stato di lettura") or r.get("Status") or r.get("Bookshelves") or ""
        rating_raw = r.get("Voto") or r.get("Rating") or r.get("My Rating") or "0"
        
        # Commenti e recensioni autentiche
        comm_title = r.get("Titolo Commento") or ""
        comm_body = r.get("Contenuto Commento") or r.get("My Review") or r.get("Review") or ""
        review_full = f"{comm_title}: {comm_body}".strip(": ") if comm_title and comm_body else (comm_body or comm_title)

        if not title.strip():
            continue

        # Normalizzazione dello stato
        status_lower = status_raw.lower()
        if any(w in status_lower for w in ["in lettura", "reading", "currently-reading", "in corso", "started"]):
            status = "in_corso"
        elif any(w in status_lower for w in ["da leggere", "to-read"]):
            status = "da_leggere"
        else:
            status = "letto"

        try:
            rating = float(rating_raw) if rating_raw else 0
        except ValueError:
            rating = 0

        rows.append({
            "title": title.strip(),
            "subtitle": subtitle.strip(),
            "author": author.strip(),
            "isbn": clean_isbn(isbn),
            "status": status,
            "status_raw": status_raw.strip(),
            "rating": rating,
            "review": review_full.strip(),
            "publisher": (r.get("Editore") or r.get("Publisher") or "").strip()
        })

    return rows

def import_books(csv_path, prune=False):
    if not os.path.exists(csv_path):
        print(f"[ERRORE] File CSV non trovato: {csv_path}")
        return False, "File CSV non trovato"

    incoming_rows = read_anobii_or_generic_csv(csv_path)
    print(f"Letti {len(incoming_rows)} libri dal file CSV {csv_path}.")

    existing_books = []
    if os.path.exists(BOOKS_JSON_PATH):
        try:
            with open(BOOKS_JSON_PATH, "r", encoding="utf-8") as f:
                existing_books = json.load(f)
        except Exception:
            existing_books = []

    isbn_map = {}
    title_map = {}
    for idx, b in enumerate(existing_books):
        b_isbn = clean_isbn(b.get("isbn", ""))
        if b_isbn:
            isbn_map[b_isbn] = idx
        t_key = normalize_text(b.get("title", "")) + normalize_text(b.get("author", ""))
        title_map[t_key] = idx

    matched_indices = set()
    final_books = []
    updated_count = 0
    added_count = 0

    for inc in incoming_rows:
        inc_isbn = inc["isbn"]
        inc_key = normalize_text(inc["title"]) + normalize_text(inc["author"])

        target_idx = None
        if inc_isbn and inc_isbn in isbn_map:
            target_idx = isbn_map[inc_isbn]
        elif inc_key in title_map:
            target_idx = title_map[inc_key]

        if target_idx is not None:
            matched_indices.add(target_idx)
            curr = dict(existing_books[target_idx])
            
            # Aggiornamento dati reali
            curr["status"] = inc["status"]
            curr["status_raw"] = inc["status_raw"]
            if inc["rating"] > 0:
                curr["rating"] = inc["rating"]
            if inc["isbn"]:
                curr["isbn"] = inc["isbn"]
            if inc["subtitle"]:
                curr["subtitle"] = inc["subtitle"]
            if inc["publisher"]:
                curr["publisher"] = inc["publisher"]

            # Preserva recensioni se presenti nell'incoming, altrimenti mantieni quelle esistenti
            if inc["review"]:
                curr["review"] = inc["review"]
            
            # Recupera copertina autentica se non già presente
            if not curr.get("cover") and curr.get("isbn"):
                cov = verify_and_get_cover_url(curr.get("isbn"))
                if cov:
                    curr["cover"] = cov

            final_books.append(curr)
            updated_count += 1
        else:
            # Nuovo libro da Anobii
            cov = verify_and_get_cover_url(inc["isbn"]) if inc["isbn"] else ""
            new_b = {
                "title": inc["title"],
                "subtitle": inc["subtitle"],
                "author": inc["author"],
                "isbn": inc["isbn"],
                "status": inc["status"],
                "status_raw": inc["status_raw"],
                "rating": inc["rating"],
                "review": inc["review"],
                "publisher": inc["publisher"],
                "cover": cov,
                "anobii_url": ANOBII_PROFILE
            }
            final_books.append(new_b)
            added_count += 1

    # Libri nel JSON ma non nel CSV in ingresso
    unmatched_existing = [b for idx, b in enumerate(existing_books) if idx not in matched_indices]
    if unmatched_existing:
        print(f"\n[REPORT VERIFICA CONFRONTO LIBRERIA]")
        print(f"Rilevati {len(unmatched_existing)} libri presenti in data/books.json ma non inclusi nel CSV importato:")
        for m in unmatched_existing:
            print(f"  * '{m.get('title')}' di {m.get('author')}")

        if prune:
            print("Flag --prune attivo: rimozione applicata ai libri non presenti nel CSV Anobii.")
        else:
            print("Flag --prune non specificato: i libri sono stati CONSERVATI come selezioni editoriali del sito.")
            final_books.extend(unmatched_existing)

    # Scrittura finale del file JSON
    with open(BOOKS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(final_books, f, indent=2, ensure_ascii=False)

    summary = f"Anobii Sync: {updated_count} libri aggiornati, {added_count} nuovi libri aggiunti. Totale biblioteca: {len(final_books)} libri."
    print(f"\n[COMPLETATO] {summary}")
    return True, summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincronizzatore Biblioteca Anobii per Geobasi.com")
    parser.add_argument("--import-csv", dest="csv_file", required=True, help="Percorso del file CSV esportato da Anobii")
    parser.add_argument("--prune", action="store_true", help="Rimuovi dal sito i libri non più presenti nel CSV di Anobii")
    args = parser.parse_args()

    success, msg = import_books(args.csv_file, args.prune)
    if not success:
        sys.exit(1)
