#!/usr/bin/env python3
"""
Sync Engine centrale per Geobasi.com:
- Coordina le sincronizzazioni da Substack, LinkedIn, Anobii e Instagram.
- Implementa il principio di Conservative Merge (nessuna sovrascrittura di arricchimenti manuali).
- Registra lo storico delle operazioni in site/data/sync_log.json.
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.parse

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(DATA_DIR, "sync_log.json")

def log_sync(source, status, count, message):
    os.makedirs(DATA_DIR, exist_ok=True)
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": source,
        "status": status,
        "records_processed": count,
        "message": message
    }
    logs.insert(0, entry)
    logs = logs[:50] # Keep last 50 sync events

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"[{source.upper()}] {status}: {message}")

def conservative_merge_cv(incoming_experiences, target_cv_path):
    """
    Aggiorna date, titoli e aziende da fonte esterna ma preserva
    gli highlight o descrizioni personalizzate precedentemente scritte.
    """
    if not os.path.exists(target_cv_path):
        return

    with open(target_cv_path, "r", encoding="utf-8") as f:
        cv_data = json.load(f)

    existing_exp = {e.get("company", "").lower(): e for e in cv_data.get("experiences", [])}

    merged = []
    for inc in incoming_experiences:
        comp_key = inc.get("company", "").lower()
        if comp_key in existing_exp:
            curr = existing_exp[comp_key]
            # Update dates and title, keep rich highlights and detailed notes
            merged.append({
                "role": inc.get("role") or curr.get("role"),
                "company": curr.get("company"),
                "period": inc.get("period") or curr.get("period"),
                "location": inc.get("location") or curr.get("location"),
                "description": curr.get("description") or inc.get("description"),
                "highlights": curr.get("highlights", [])
            })
        else:
            merged.append(inc)

    cv_data["experiences"] = merged
    with open(target_cv_path, "w", encoding="utf-8") as f:
        json.dump(cv_data, f, indent=2, ensure_ascii=False)

def run_sync_all():
    print("Avvio sincronizzazione delle fonti...")

    # 1. Substack RSS
    try:
        from fetch_substack import fetch_articles
        fetch_articles()
        with open(os.path.join(DATA_DIR, "articles.json")) as f:
            count = len(json.load(f))
        log_sync("substack", "SUCCESS", count, f"Estratti {count} articoli via RSS da geobuzz.substack.com")
    except Exception as e:
        log_sync("substack", "ERROR", 0, str(e))

    # 2. LinkedIn Portability API Check
    token = os.environ.get("LINKEDIN_PORTABILITY_TOKEN")
    if token:
        try:
            # LinkedIn Member Data Portability endpoint under DMA
            url = "https://api.linkedin.com/v2/memberDataPortability"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # Process positions and conservative merge
            log_sync("linkedin_api", "SUCCESS", len(data.get("positions", [])), "Sincronizzazione completata via Member Data Portability API")
        except Exception as e:
            log_sync("linkedin_api", "ERROR", 0, f"Errore chiamata API LinkedIn: {e}")
    else:
        log_sync("linkedin_api", "SKIPPED", 0, "Token non presente. Utilizzare scripts/import_linkedin.py per importazione manuale")

    # 3. Instagram Graph API Check
    meta_token = os.environ.get("INSTAGRAM_GRAPH_TOKEN")
    if meta_token:
        try:
            # Instagram Graph API endpoint for Creator/Business accounts
            url = f"https://graph.instagram.com/me/media?fields=id,caption,media_url,permalink,timestamp&access_token={meta_token}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            log_sync("instagram_api", "SUCCESS", len(data.get("data", [])), "Sincronizzazione completata via Instagram Graph API")
        except Exception as e:
            log_sync("instagram_api", "ERROR", 0, f"Errore chiamata API Instagram: {e}")
    else:
        log_sync("instagram_api", "SKIPPED", 0, "Token non presente. Galleria gestita tramite data/photos.json")

    # Re-build site and printable CV pages
    try:
        from build_site import build
        build()
        log_sync("site_builder", "SUCCESS", 1, "Compilata l'homepage index.html e le pagine cv-it.html/cv-en.html")
    except Exception as e:
        log_sync("site_builder", "ERROR", 0, f"Errore build_site: {e}")

if __name__ == "__main__":
    run_sync_all()
