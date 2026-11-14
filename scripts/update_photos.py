#!/usr/bin/env python3
"""
Sincronizzatore automatico Instagram per Geobasi.com:
- Esegue la scansione dei post pubblici dal profilo instagram.com/christian.bazzucchi/ tramite instaloader.
- Salva l'elenco completo dei post autentici in data/instagram_catalog.json.
- Seleziona casualmente (random sample) 4 post autentici per la visualizzazione corrente in data/photos.json.
- Supporta anche l'embed ufficiale o la visualizzazione di schede con didascalia reale e data.
"""
import os
import sys
import json
import random
import datetime

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
CATALOG_FILE = os.path.join(DATA_DIR, "instagram_catalog.json")
PHOTOS_FILE = os.path.join(DATA_DIR, "photos.json")
USERNAME = "christian.bazzucchi"

def scan_instagram_profile():
    print(f"Scansione post pubblici per @{USERNAME}...")
    try:
        import instaloader
        L = instaloader.Instaloader(download_pictures=False, download_videos=False, download_comments=False)
        profile = instaloader.Profile.from_username(L.context, USERNAME)
        
        catalog = []
        for post in profile.get_posts():
            clean_caption = (post.caption or "").strip()
            first_line = clean_caption.split("\n")[0][:80] if clean_caption else "Scatto dal profilo Instagram"
            
            dt_str = post.date_utc.strftime("%d %b %Y")
            
            catalog.append({
                "shortcode": post.shortcode,
                "permalink": f"https://www.instagram.com/p/{post.shortcode}/",
                "title": first_line,
                "caption": clean_caption,
                "date": dt_str,
                "is_video": post.is_video,
                "likes": post.likes
            })
            if len(catalog) >= 30: # Mantieni gli ultimi 30 post
                break
        
        if catalog:
            with open(CATALOG_FILE, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=2, ensure_ascii=False)
            print(f"Catalogo aggiornato con {len(catalog)} post autentici da Instagram.")
            return catalog
    except Exception as e:
        print(f"Errore durante la scansione live Instagram: {e}")
        if os.path.exists(CATALOG_FILE):
            print("Utilizzo catalogo salvato in precedenza.")
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    return []

def pick_random_posts(sample_size=4):
    catalog = []
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception:
            catalog = []
            
    if not catalog:
        catalog = scan_instagram_profile()
        
    if not catalog:
        print("Nessun post disponibile nel catalogo.")
        return []

    # Selezione casuale di sample_size post
    count = min(sample_size, len(catalog))
    selected = random.sample(catalog, count)
    
    photos_data = []
    for p in selected:
        photos_data.append({
            "shortcode": p.get("shortcode"),
            "title": p.get("title"),
            "location": "Profilo Instagram @christian.bazzucchi",
            "date": p.get("date"),
            "caption": p.get("caption"),
            "permalink": p.get("permalink")
        })

    with open(PHOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(photos_data, f, indent=2, ensure_ascii=False)

    print(f"Selezionati casualmente {len(photos_data)} post autentici in {PHOTOS_FILE}.")
    return photos_data

if __name__ == "__main__":
    scan_instagram_profile()
    pick_random_posts(4)
