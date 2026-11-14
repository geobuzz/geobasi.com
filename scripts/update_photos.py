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

def scan_instagram_profile(max_new_posts=4):
    print(f"Scansione incrementale post pubblici per @{USERNAME} (fino a {max_new_posts} post)...")
    existing_catalog = load_catalog()
    existing_shortcodes = {p.get("shortcode") for p in existing_catalog if p.get("shortcode")}
    
    try:
        import instaloader
        L = instaloader.Instaloader(download_pictures=False, download_videos=False, download_comments=False)
        profile = instaloader.Profile.from_username(L.context, USERNAME)
        
        scanned_count = 0
        new_posts = []
        for post in profile.get_posts():
            scanned_count += 1
            sc = post.shortcode
            
            if sc in existing_shortcodes:
                if scanned_count >= max_new_posts:
                    break
                continue
                
            clean_caption = (post.caption or "").strip()
            first_line = clean_caption.split("\n")[0][:80] if clean_caption else "Post dal profilo Instagram"
            dt_str = post.date_utc.strftime("%d %b %Y")
            
            # Estrazione del geotag autentico nativo dal nodo del post
            node = getattr(post, "_node", {})
            loc_dict = node.get("location") if isinstance(node, dict) else None
            loc_name = loc_dict.get("name") if isinstance(loc_dict, dict) else None
            
            # Se manca il geotag nativo ma c'è una didascalia con toponimo
            effective_loc = loc_name
            if not effective_loc and clean_caption:
                cand = clean_caption.split("\n")[0].strip()
                if not cand.startswith("#") and len(cand) >= 3 and not any(tag in cand.lower() for tag in ["geobasi", "instagram"]):
                    effective_loc = cand[:50]

            post_dict = {
                "shortcode": sc,
                "permalink": f"https://www.instagram.com/p/{sc}/",
                "title": first_line,
                "caption": clean_caption,
                "location": effective_loc or loc_name or "Territorio & Paesaggio",
                "raw_location": loc_name or "",
                "date": dt_str,
                "is_video": post.is_video,
                "likes": post.likes,
                "image_url": post.url
            }
            
            is_valid, reason = validate_post_coherence(post_dict)
            if not is_valid:
                print(f"[AVVISO] Post scartato durante la scansione: {reason}")
                continue
                
            download_photo_image(sc, post.url)
            new_posts.append(post_dict)
            if len(new_posts) >= max_new_posts or scanned_count >= max_new_posts:
                break
        
        if new_posts:
            updated_catalog = new_posts + [p for p in existing_catalog if p.get("shortcode") not in {np["shortcode"] for np in new_posts}]
            with open(CATALOG_FILE, "w", encoding="utf-8") as f:
                json.dump(updated_catalog, f, indent=2, ensure_ascii=False)
            print(f"[INSTAGRAM] Aggiunti {len(new_posts)} nuovi post al catalogo (totale: {len(updated_catalog)}).")
            return True, updated_catalog, f"Scansione completata con successo: {len(new_posts)} nuovi post aggiunti"
        else:
            print(f"[INSTAGRAM] Nessun nuovo post rilevato tra i primi {scanned_count} esaminati. Catalogo invariato ({len(existing_catalog)} post).")
            return True, existing_catalog, f"Nessun nuovo post rilevato. Catalogo aggiornato e invariato ({len(existing_catalog)} post)"
    except Exception as e:
        err_msg = str(e)
        print(f"[INSTAGRAM] Scansione live non disponibile: {err_msg}. Mantenuto il catalogo esistente ({len(existing_catalog)} post).")
        return False, existing_catalog, f"Scansione fallita ({err_msg}). Mantenuto catalogo precedente di {len(existing_catalog)} post"

def download_photo_image(shortcode, image_url=None):
    """Scarica e memorizza la foto in assets/img/photos/<shortcode>.jpg se non già presente."""
    img_dir = os.path.join(BASE_DIR, "assets", "img", "photos")
    os.makedirs(img_dir, exist_ok=True)
    dest_path = os.path.join(img_dir, f"{shortcode}.jpg")
    rel_path = f"assets/img/photos/{shortcode}.jpg"
    
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return rel_path

    urls_to_try = []
    if image_url:
        urls_to_try.append(image_url)
    urls_to_try.append(f"https://www.instagram.com/p/{shortcode}/media/?size=l")

    import urllib.request
    for u in urls_to_try:
        try:
            req = urllib.request.Request(
                u,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
                if len(content) > 1000:
                    with open(dest_path, "wb") as f:
                        f.write(content)
                    return rel_path
        except Exception:
            continue

    return rel_path

def determine_location(post_dict):
    """Estrae il luogo autentico da raw_location, geotag o didascalia nativa di Instagram."""
    raw_loc = post_dict.get("raw_location")
    if raw_loc and raw_loc.strip() and raw_loc.strip() not in ("Profilo Instagram @christian.bazzucchi", "Toscana, Italia"):
        return raw_loc.strip()
        
    loc = post_dict.get("location")
    if loc and loc.strip() and loc.strip() not in ("Profilo Instagram @christian.bazzucchi", "Toscana, Italia"):
        return loc.strip()
        
    caption = post_dict.get("caption", "").strip()
    if caption:
        first_line = caption.split("\n")[0].strip()
        clean = " ".join([w for w in first_line.split() if not w.startswith("#")]).strip()
        if len(clean) >= 3 and not any(tag in clean.lower() for tag in ["geobasi", "instagram", "post dal profilo"]):
            return clean[:50]
            
    return "Territorio & Paesaggio"

def pick_random_posts(sample_size=8, preserve_existing=False):
    catalog = load_catalog()
    if not catalog:
        print("[ERRORE] Catalogo Instagram vuoto. Impossibile selezionare post.")
        return False, []

    # Se richiesto di preservare i post esistenti (es. scansione live fallita)
    if preserve_existing:
        existing_photos = load_photos()
        if existing_photos:
            catalog_shortcodes = {p.get("shortcode") for p in catalog if p.get("shortcode")}
            all_valid = True
            for p in existing_photos:
                is_valid, reason = validate_post_coherence(p)
                if not is_valid or p.get("shortcode") not in catalog_shortcodes:
                    all_valid = False
                    break
            if all_valid:
                print(f"[INSTAGRAM] Mantenuti invariati i {len(existing_photos)} post precedenti.")
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

    # Privilegia i post con toponimi reali e specifici
    specific_posts = [p for p in valid_catalog_posts if p.get("location") and p.get("location") not in ("Toscana, Italia", "Territorio & Paesaggio")]
    pool = specific_posts if len(specific_posts) >= sample_size else valid_catalog_posts

    valid_shortcodes = {p["shortcode"] for p in valid_catalog_posts}
    count = min(sample_size, len(pool))
    
    # Selezione casuale (8 foto)
    selected = random.sample(pool, count)
    
    validated_posts = []
    for p in selected:
        sc = p.get("shortcode")
        if sc not in valid_shortcodes:
            raise ValueError(f"Incoerenza dati: shortcode {sc} non presente nel catalogo!")
            
        is_valid, reason = validate_post_coherence(p)
        if not is_valid:
            raise ValueError(f"Incoerenza validazione post {sc}: {reason}")

        img_rel = download_photo_image(sc, p.get("image_url"))
        loc = determine_location(p)
            
        validated_posts.append({
            "shortcode": sc,
            "location": loc,
            "image": img_rel,
            "date": p.get("date", ""),
            "caption": p.get("caption", ""),
            "permalink": p.get("permalink", f"https://www.instagram.com/p/{sc}/")
        })

    with open(PHOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(validated_posts, f, indent=2, ensure_ascii=False)

    print(f"[INSTAGRAM] Selezionati e validati {len(validated_posts)} shortcode autentici e coerenti dal catalogo.")
    return True, validated_posts

if __name__ == "__main__":
    scan_ok, catalog, msg = scan_instagram_profile(4)
    pick_ok, posts = pick_random_posts(8, preserve_existing=not scan_ok)
    print(f"Esito: scan={scan_ok}, pick={pick_ok}, selezionati={len(posts)}")
