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
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
CATALOG_FILE = os.path.join(DATA_DIR, "instagram_catalog.json")
PHOTOS_FILE = os.path.join(DATA_DIR, "photos.json")
USERNAME = "christian.bazzucchi"

SHORTCODE_REGEX = re.compile(r"^[A-Za-z0-9_-]{9,15}$")
PERMALINK_REGEX = re.compile(r"^https://(?:www\.)?instagram\.com/(?:p|reel)/([A-Za-z0-9_-]{9,15})/?$")

def validate_shortcode_format(shortcode):
    """Verifica che lo shortcode sia conforme alle specifiche base64url di Instagram."""
    if not isinstance(shortcode, str):
        return False
    return bool(SHORTCODE_REGEX.match(shortcode))

def validate_post_coherence(post):
    """Verifica che lo shortcode sia valido e coerente con il permalink Instagram."""
    if not isinstance(post, dict):
        return False, "Il record del post deve essere un dizionario"
    
    sc = post.get("shortcode")
    if not sc or not validate_shortcode_format(sc):
        return False, f"Formato shortcode Instagram non valido: '{sc}'"
    
    permalink = post.get("permalink", "")
    if not isinstance(permalink, str):
        return False, "Permalink mancante o di tipo non valido"
    
    m = PERMALINK_REGEX.match(permalink)
    if not m:
        return False, f"Formato permalink non conforme a Instagram (deve essere /p/<shortcode>/ o /reel/<shortcode>/): '{permalink}'"
    
    permalink_shortcode = m.group(1)
    if permalink_shortcode != sc:
        return False, f"Incoerenza tra shortcode ('{sc}') e permalink ('{permalink}')"
    
    return True, ""

def load_catalog():
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
    return []

def load_photos():
    if os.path.exists(PHOTOS_FILE):
        try:
            with open(PHOTOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
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
            
            post_dict = {
                "shortcode": post.shortcode,
                "permalink": f"https://www.instagram.com/p/{post.shortcode}/",
                "title": first_line,
                "caption": clean_caption,
                "date": dt_str,
                "is_video": post.is_video,
                "likes": post.likes
            }
            
            is_valid, reason = validate_post_coherence(post_dict)
            if not is_valid:
                print(f"[AVVISO] Post scartato durante la scansione: {reason}")
                continue
                
            fresh_catalog.append(post_dict)
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

def pick_random_posts(sample_size=4, preserve_existing=False):
    catalog = load_catalog()
    if not catalog:
        print("[ERRORE] Catalogo Instagram vuoto. Impossibile selezionare post.")
        return False, []

    # Se richiesto di preservare i post esistenti (es. scansione live fallita)
    if preserve_existing:
        existing_photos = load_photos()
        if len(existing_photos) == sample_size:
            catalog_shortcodes = {p.get("shortcode") for p in catalog if p.get("shortcode")}
            all_valid = True
            for p in existing_photos:
                is_valid, reason = validate_post_coherence(p)
                if not is_valid or p.get("shortcode") not in catalog_shortcodes:
                    all_valid = False
                    break
            if all_valid:
                print(f"[INSTAGRAM] Mantenuti invariati i {sample_size} post precedenti.")
                return True, existing_photos

    # Filtra il catalogo garantendo che ogni elemento rispetti formato e coerenza
    valid_catalog_posts = []
    for p in catalog:
        is_valid, _ = validate_post_coherence(p)
        if is_valid:
            valid_catalog_posts.append(p)

    if not valid_catalog_posts:
        print("[ERRORE] Nessun post valido reperibile nel catalogo Instagram.")
        return False, []

    valid_shortcodes = {p["shortcode"] for p in valid_catalog_posts}
    count = min(sample_size, len(valid_catalog_posts))
    
    # Selezione casuale
    selected = random.sample(valid_catalog_posts, count)
    
    # Validazione formale e di coerenza: ogni post selezionato deve avere lo shortcode nel catalogo
    validated_posts = []
    for p in selected:
        sc = p.get("shortcode")
        if sc not in valid_shortcodes:
            raise ValueError(f"Incoerenza dati: shortcode {sc} non presente nel catalogo!")
            
        is_valid, reason = validate_post_coherence(p)
        if not is_valid:
            raise ValueError(f"Incoerenza validazione post {sc}: {reason}")
            
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

    print(f"[INSTAGRAM] Selezionati e validati {len(validated_posts)} shortcode autentici e coerenti dal catalogo.")
    return True, validated_posts

if __name__ == "__main__":
    scan_ok, catalog, msg = scan_instagram_profile()
    pick_ok, posts = pick_random_posts(4, preserve_existing=not scan_ok)
    print(f"Esito: scan={scan_ok}, pick={pick_ok}, selezionati={len(posts)}")
