#!/usr/bin/env python3
"""
Sync Engine centrale per Geobasi.com:
- Coordina le sincronizzazioni da Substack, LinkedIn, Anobii e Instagram.
- Distingue chiaramente gli stati: SUCCESS, ERROR, SKIPPED, PARTIAL.
- Solleva eccezioni e ritorna exit code != 0 in caso di errori di build o critici.
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

# Assicura reperibilità dei moduli script sibling
sys.path.insert(0, os.path.dirname(__file__))

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
    logs = logs[:50] # Conserva gli ultimi 50 eventi

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"[{source.upper()}] {status}: {message}")

def run_sync_all():
    print("Avvio sincronizzazione delle fonti...")
    has_critical_error = False

    # 1. Substack RSS
    try:
        from fetch_substack import fetch_articles
        articles = fetch_articles()
        count = len(articles)
        if count > 0:
            log_sync("substack", "SUCCESS", count, f"Estratti e compilati {count} articoli con pagine interne da geobuzz.substack.com")
        else:
            log_sync("substack", "PARTIAL", 0, "Feed Substack raggiungibile ma nessun articolo estratto")
    except Exception as e:
        log_sync("substack", "ERROR", 0, f"Errore sincronizzazione Substack: {e}")
        has_critical_error = True

    # 2. LinkedIn Portability API Check
    token = os.environ.get("LINKEDIN_PORTABILITY_TOKEN")
    if token:
        try:
            # Endpoint per Member Data Portability secondo DMA
            url = "https://api.linkedin.com/v2/memberDataPortability"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            positions = data.get("positions", [])
            if positions:
                log_sync("linkedin_api", "SUCCESS", len(positions), "Dati DMA LinkedIn estratti ed elaborati con successo")
            else:
                log_sync("linkedin_api", "PARTIAL", 0, "API LinkedIn DMA interrogata ma nessun record restituito")
        except Exception as e:
            log_sync("linkedin_api", "ERROR", 0, f"Errore chiamata API LinkedIn: {e}")
            has_critical_error = True
    else:
        log_sync("linkedin_api", "SKIPPED", 0, "Token non configurato. Importazione assistita gestita tramite scripts/import_linkedin.py")

    # 3. Instagram: Esegui prima scan_instagram_profile() e poi pick_random_posts(4)
    try:
        from update_photos import scan_instagram_profile, pick_random_posts
        
        # Fase 1: Scansione live del profilo
        scan_ok, catalog, scan_msg = scan_instagram_profile()
        
        # Fase 2: Campionamento casuale e validazione dei 4 shortcode
        pick_ok, selected_posts = pick_random_posts(4)
        
        if not pick_ok or len(selected_posts) == 0:
            log_sync("instagram", "ERROR", 0, "Impossibile selezionare i 4 post dal catalogo Instagram")
            has_critical_error = True
        elif not scan_ok:
            # Scansione live fallita ma catalogo precedente preservato: stato PARTIAL rigoroso
            log_sync("instagram", "PARTIAL", len(selected_posts), f"{scan_msg}. Selezionati e validati 4 post dal catalogo locale")
        else:
            # Scansione live riuscita e post selezionati e validati: stato SUCCESS
            log_sync("instagram", "SUCCESS", len(selected_posts), f"{scan_msg}. Selezionati e validati 4 post dal catalogo aggiornato")
            
    except Exception as e:
        log_sync("instagram", "ERROR", 0, f"Errore pipeline Instagram: {e}")
        has_critical_error = True

    # 4. Compilazione deterministica del sito e pagine CV
    try:
        from build_site import build
        build()
        log_sync("site_builder", "SUCCESS", 1, "Homepage index.html, cv-it.html e cv-en.html compilati con successo")
    except Exception as e:
        log_sync("site_builder", "ERROR", 0, f"Errore critico durante la compilazione del sito: {e}")
        has_critical_error = True

    if has_critical_error:
        print("\n[ERRORE CRITICO] Il Sync Engine ha riscontrato anomalie bloccanti. Uscita con codice 1.")
        sys.exit(1)
    else:
        print("\n[SUCCESSO] Sincronizzazione e compilazione completate senza errori.")

if __name__ == "__main__":
    run_sync_all()
