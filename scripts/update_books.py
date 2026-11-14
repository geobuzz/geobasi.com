#!/usr/bin/env python3
"""
Utility per aggiornare site/data/books.json:
- Supporta l'importazione diretta del CSV esportato da Anobii (Profilo -> Impostazioni -> Esporta libreria CSV)
- Recupera in automatico l'URL della copertina tramite ISBN su Open Library Covers API
- Mantiene lo stato di lettura ('in_corso', 'letto'), rating, recensioni e citazioni
"""
import csv
import json
import os
import sys
import argparse
import urllib.request

BOOKS_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "books.json")
ANOBII_PROFILE = "https://www.anobii.com/it/01d6d75099d9c1d4bb/profile"

def get_cover_url(isbn):
    if not isbn:
        return ""
    clean_isbn = isbn.replace("-", "").strip()
    return f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-M.jpg"

def import_anobii_csv(csv_path):
    if not os.path.exists(csv_path):
        print(f"Errore: file non trovato {csv_path}")
        sys.exit(1)

    books = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map common Anobii CSV column headers (case-insensitive)
            title = row.get("Title") or row.get("Titolo") or ""
            author = row.get("Author") or row.get("Autore") or ""
            isbn = row.get("ISBN") or row.get("ISBN13") or ""
            status_raw = (row.get("Status") or row.get("Stato") or "").lower()
            rating_raw = row.get("Rating") or row.get("Valutazione") or "0"
            review = row.get("Review") or row.get("Recensione") or row.get("Comment") or ""
            quotes = row.get("Quote") or row.get("Citazione") or ""

            if not title:
                continue

            status = "in_corso" if "leggendo" in status_raw or "reading" in status_raw else "letto"
            try:
                rating = int(float(rating_raw))
            except ValueError:
                rating = 0

            cover = get_cover_url(isbn) if isbn else ""

            books.append({
                "title": title.strip(),
                "author": author.strip(),
                "status": status,
                "rating": rating,
                "isbn": isbn.strip(),
                "note": review.strip(),
                "quote": quotes.strip(),
                "cover": cover,
                "anobii_url": ANOBII_PROFILE
            })

    # Save to data/books.json
    with open(BOOKS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2, ensure_ascii=False)

    print(f"Importati con successo {len(books)} libri da {csv_path} in {BOOKS_JSON_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gestione libreria libri Anobii")
    parser.add_argument("--import-csv", dest="csv_file", help="Percorso del file CSV esportato da Anobii")
    args = parser.parse_args()

    if args.csv_file:
        import_anobii_csv(args.csv_file)
    else:
        print("Uso: python3 update_books.py --import-csv <percorso_file.csv>")
        print(f"File attuale: {BOOKS_JSON_PATH}")
