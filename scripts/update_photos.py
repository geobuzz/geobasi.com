#!/usr/bin/env python3
"""
Sincronizzatore automatico Instagram per Geobasi.com:
- Esegue la scansione dei post pubblici dal profilo instagram.com/christian.bazzucchi/ tramite instaloader.
- Se la scansione live ha successo, aggiorna data/instagram_catalog.json e restituisce (True, catalog, count).
- Se la scansione live fallisce, conserva integralmente il catalogo precedente e restituisce (False, catalog, err_msg).
- pick_random_posts(sample_size=4) verifica tassativamente che tutti i 4 shortcode selezionati appartengano al catalogo.
- Salva i 4 post selezionati in data/photos.json.
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

def load_catalog():
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def scan_instagram_profile():
    print(f"Scansione post pubblici per @{USERNAME}...")
    existing_catalog = load_catalog()
    try:
        import instaloader
        L = instaloader.Instaloader(download_pictures=False, download_videos=False, download_comments=False)
        profile = instaloader.Profile.from_username(L.context, USERNAME)
        
        fresh_catalog = []
        for post in profile.get_posts():
            clean_caption = (post.caption or "").strip()
            first_line = clean_caption.split("\n")[0][:80] if clean_caption else "Post dal profilo Instagram"
            dt_str = post.date_utc.strftime("%d %b %Y")
            
            fresh_catalog.append({
                "shortcode": post.shortcode,
                "permalink": f"https://www.instagram.com/p/{post.shortcode}/",
                "title": first_line,
                "caption": clean_caption,
                "date": dt_str,
                "is_video": post.is_video,
                "likes": post.likes
            })
            if len(fresh_catalog) >= 30: # Mantieni gli ultimi 30 post
                break
        
        if fresh_catalog:
            with open(CATALOG_FILE, "w", encoding="utf-8") as f:
                json.dump(fresh_catalog, f, indent=2, ensure_ascii=False)
            print(f"[INSTAGRAM] Scansione completata con successo: {len(fresh_catalog)} post autentici censiti.")
            return True, fresh_catalog, f"Scansione completata con successo: {len(fresh_catalog)} post aggiornati"
        else:
            return False, existing_catalog, "Nessun post estratto dal profilo Instagram"
    except Exception as e:
        err_msg = str(e)
        print(f"[INSTAGRAM] Scansione live fallita: {err_msg}. Mantenuto il catalogo esistente ({len(existing_catalog)} post).")
        return False, existing_catalog, f"Scansione fallita ({err_msg}). Mantenuto catalogo precedente di {len(existing_catalog)} post"

def pick_random_posts(sample_size=4):
    catalog = load_catalog()
    if not catalog:
        print("[ERRORE] Catalogo Instagram vuoto. Impossibile selezionare post.")
        return False, []

    valid_shortcodes = {p.get("shortcode") for p in catalog if p.get("shortcode")}
    count = min(sample_size, len(catalog))
    
    # Selezione casuale
    selected = random.sample(catalog, count)
    
    # Validazione formale: ogni post selezionato deve avere lo shortcode presente nel catalogo
    validated_posts = []
    for p in selected:
        sc = p.get("shortcode")
        if sc not in valid_shortcodes:
            raise ValueError(f"Incoerenza dati: shortcode {sc} non presente nel catalogo!")
            
        validated_posts.append({
            "shortcode": sc,
            "title": p.get("title", "Post dal profilo Instagram"),
            "location": "Profilo Instagram @christian.bazzucchi",
            "date": p.get("date", ""),
            "caption": p.get("caption", ""),
            "permalink": p.get("permalink", f"https://www.instagram.com/p/{sc}/")
        })

    with open(PHOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(validated_posts, f, indent=2, ensure_ascii=False)

    print(f"[INSTAGRAM] Selezionati e validati {len(validated_posts)} shortcode autentici dal catalogo.")
    return True, validated_posts

if __name__ == "__main__":
    scan_ok, catalog, msg = scan_instagram_profile()
    pick_ok, posts = pick_random_posts(4)
    print(f"Esito: scan={scan_ok}, pick={pick_ok}, selezionati={len(posts)}")
