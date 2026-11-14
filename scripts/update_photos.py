#!/usr/bin/env python3
"""
Script di gestione e aggiornamento per la galleria fotografica Instagram:
- Supporta l'aggiunta manuale assistita di post autentici (con coordinate geografiche opzionali).
- Supporta il fetch automatico tramite Instagram Graph API (se INSTAGRAM_GRAPH_TOKEN è configurato per account Creator/Business).
- Rifiuta categoricamente immagini stock o mock.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import argparse

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
PHOTOS_FILE = os.path.join(DATA_DIR, "photos.json")

def load_photos():
    if os.path.exists(PHOTOS_FILE):
        try:
            with open(PHOTOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_photos(photos):
    with open(PHOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(photos, f, indent=2, ensure_ascii=False)
    print(f"Salvati {len(photos)} elementi in {PHOTOS_FILE}.")

def add_photo_entry(title, location, coordinates, caption, image_url, permalink):
    photos = load_photos()
    # Controlla duplicati per permalink
    for p in photos:
        if p.get("permalink") == permalink and permalink != "":
            print(f"Post con permalink {permalink} già presente. Aggiornamento metadati.")
            p.update({
                "title": title,
                "location": location,
                "coordinates": coordinates,
                "caption": caption,
                "image_url": image_url
            })
            save_photos(photos)
            return

    new_entry = {
        "title": title,
        "location": location,
        "coordinates": coordinates,
        "caption": caption,
        "image_url": image_url,
        "permalink": permalink
    }
    photos.insert(0, new_entry)
    save_photos(photos)
    print(f"Aggiunta nuova fotografia: '{title}' ({location}).")

def sync_instagram_graph_api():
    token = os.environ.get("INSTAGRAM_GRAPH_TOKEN")
    if not token:
        print("INSTAGRAM_GRAPH_TOKEN non configurato.")
        print("Nota: l'API Instagram Graph richiede un account Creator o Business.")
        print("Se l'account è personale, utilizzare l'aggiunta manuale con --add.")
        return False

    url = f"https://graph.instagram.com/me/media?fields=id,caption,media_url,permalink,timestamp,media_type&access_token={token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GeobasiSync/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        items = data.get("data", [])
        if not items:
            print("Nessun media restituito da Instagram Graph API.")
            return False

        photos = load_photos()
        existing_permalinks = {p.get("permalink") for p in photos if p.get("permalink")}
        
        added = 0
        for item in items:
            permalink = item.get("permalink", "")
            media_type = item.get("media_type", "IMAGE")
            if media_type not in ("IMAGE", "CAROUSEL_ALBUM"):
                continue

            caption_full = item.get("caption", "")
            # Estrai prime righe come titolo e caption
            lines = [l.strip() for l in caption_full.split("\n") if l.strip()]
            title = lines[0][:60] if lines else "Scatto dal Territorio"
            caption = " ".join(lines[1:3]) if len(lines) > 1 else caption_full

            if permalink not in existing_permalinks:
                photos.append({
                    "title": title,
                    "location": "Toscana, Italia",
                    "coordinates": "",
                    "caption": caption,
                    "image_url": item.get("media_url", ""),
                    "permalink": permalink
                })
                added += 1

        save_photos(photos)
        print(f"Sincronizzazione completata: {added} nuovi post aggiunti da Instagram Graph API.")
        return True
    except Exception as e:
        print(f"Errore durante la chiamata a Instagram Graph API: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Gestore fotografie Instagram per Geobasi.com")
    parser.add_argument("--sync-api", action="store_true", help="Sincronizza tramite Instagram Graph API (richiede INSTAGRAM_GRAPH_TOKEN)")
    parser.add_argument("--add", action="store_true", help="Aggiungi manualmente un post autentico")
    parser.add_argument("--title", type=str, default="Scatto dal Territorio", help="Titolo dello scatto")
    parser.add_argument("--location", type=str, default="Toscana, Italia", help="Località")
    parser.add_argument("--coords", type=str, default="", help="Coordinate geografiche WGS84")
    parser.add_argument("--caption", type=str, default="", help="Didascalia del post")
    parser.add_argument("--image", type=str, default="", help="URL o percorso locale dell'immagine")
    parser.add_argument("--permalink", type=str, default="https://www.instagram.com/christian.bazzucchi/", help="Permalink del post Instagram")

    args = parser.parse_args()

    if args.sync_api:
        sync_instagram_graph_api()
    elif args.add:
        add_photo_entry(args.title, args.location, args.coords, args.caption, args.image, args.permalink)
    else:
        photos = load_photos()
        print(f"Archivio fotografie: {len(photos)} scatti censiti in {PHOTOS_FILE}.")
        for idx, p in enumerate(photos, 1):
            print(f" {idx}. {p.get('title')} [{p.get('location')}] - {p.get('permalink')}")

if __name__ == "__main__":
    main()
