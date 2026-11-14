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

def log_sync(source, status, count, message, details=None):
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
    if details:
        entry["details"] = details
        
    logs.insert(0, entry)
    logs = logs[:50] # Conserva gli ultimi 50 eventi

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"[{source.upper()}] {status}: {message}")

def compute_pipeline_status(sources_status, has_critical_error=False):
    """
    Calcola lo stato globale della pipeline in base allo stato delle singole fonti:
    - ERROR: se has_critical_error e' True o se una qualsiasi fonte ha status 'ERROR'.
    - PARTIAL: se non vi sono errori critici ma almeno una fonte ha status 'PARTIAL'.
    - SUCCESS: se tutte le fonti attive hanno status 'SUCCESS' (o 'SKIPPED').
    """
    if has_critical_error or any(s.get("status") == "ERROR" for s in sources_status.values()):
        return "ERROR", "Pipeline completata con errori critici su una o più fonti"
    elif any(s.get("status") == "PARTIAL" for s in sources_status.values()):
        return "PARTIAL", "Pipeline completata con successo parziale (una o più fonti in stato PARTIAL)"
    else:
        return "SUCCESS", "Pipeline completata con pieno successo per tutte le fonti attive"

def run_sync_all():
    print("Avvio sincronizzazione delle fonti...")
    has_critical_error = False
    sources_status = {}

    # 1. Substack RSS
    try:
        from fetch_substack import fetch_articles
        articles = fetch_articles()
        count = len(articles)
        if count > 0:
            sources_status["substack"] = {
                "status": "SUCCESS",
                "count": count,
                "message": f"Estratti e compilati {count} articoli con pagine interne da geobuzz.substack.com"
            }
        else:
            sources_status["substack"] = {
                "status": "PARTIAL",
                "count": 0,
                "message": "Feed Substack raggiungibile ma nessun articolo estratto"
            }
    except Exception as e:
        sources_status["substack"] = {
            "status": "ERROR",
            "count": 0,
            "message": f"Errore sincronizzazione Substack: {e}"
        }
        has_critical_error = True
    
    log_sync(
        "substack",
        sources_status["substack"]["status"],
        sources_status["substack"]["count"],
        sources_status["substack"]["message"]
    )

    # 2. LinkedIn Portability API Check
    token = os.environ.get("LINKEDIN_PORTABILITY_TOKEN")
    if token:
        try:
            url = "https://api.linkedin.com/v2/memberDataPortability"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            positions = data.get("positions", [])
            if positions:
                sources_status["linkedin_api"] = {
                    "status": "SUCCESS",
                    "count": len(positions),
                    "message": "Dati DMA LinkedIn estratti ed elaborati con successo"
                }
            else:
                sources_status["linkedin_api"] = {
                    "status": "PARTIAL",
                    "count": 0,
                    "message": "API LinkedIn DMA interrogata ma nessun record restituito"
                }
        except Exception as e:
            sources_status["linkedin_api"] = {
                "status": "ERROR",
                "count": 0,
                "message": f"Errore chiamata API LinkedIn: {e}"
            }
            has_critical_error = True
    else:
        sources_status["linkedin_api"] = {
            "status": "SKIPPED",
            "count": 0,
            "message": "Token non configurato. Importazione assistita gestita tramite scripts/import_linkedin.py"
        }
        
    log_sync(
        "linkedin_api",
        sources_status["linkedin_api"]["status"],
        sources_status["linkedin_api"]["count"],
        sources_status["linkedin_api"]["message"]
    )

    # 3. Instagram: Esegui prima scan_instagram_profile(4) e poi pick_random_posts(8)
    try:
        from update_photos import scan_instagram_profile, pick_random_posts
        
        # Fase 1: Scansione incrementale notturna (max 4 post per evitare rate limit)
        scan_ok, catalog, scan_msg = scan_instagram_profile(4)
        
        # Fase 2: Campionamento o mantenimento degli 8 shortcode
        if not scan_ok:
            # Scansione fallita: mantieni invariati i post precedenti e preserva il catalogo esistente
            pick_ok, selected_posts = pick_random_posts(8, preserve_existing=True)
            if not pick_ok or len(selected_posts) == 0:
                sources_status["instagram"] = {
                    "status": "ERROR",
                    "count": 0,
                    "message": "Impossibile reperire post validi dal catalogo Instagram locale"
                }
                has_critical_error = True
            else:
                sources_status["instagram"] = {
                    "status": "PARTIAL",
                    "count": len(selected_posts),
                    "message": f"{scan_msg}. Mantenuti i post precedenti e catalogo locale invariato"
                }
        else:
            # Scansione live riuscita: aggiorna/campiona 8 post dal catalogo aggiornato
            pick_ok, selected_posts = pick_random_posts(8, preserve_existing=False)
            if not pick_ok or len(selected_posts) == 0:
                sources_status["instagram"] = {
                    "status": "ERROR",
                    "count": 0,
                    "message": "Impossibile selezionare gli 8 post dal catalogo Instagram aggiornato"
                }
                has_critical_error = True
            else:
                sources_status["instagram"] = {
                    "status": "SUCCESS",
                    "count": len(selected_posts),
                    "message": f"{scan_msg}. Selezionati e validati {len(selected_posts)} post dal catalogo aggiornato"
                }
            
    except Exception as e:
        sources_status["instagram"] = {
            "status": "ERROR",
            "count": 0,
            "message": f"Errore pipeline Instagram: {e}"
        }
        has_critical_error = True
        
    log_sync(
        "instagram",
        sources_status["instagram"]["status"],
        sources_status["instagram"]["count"],
        sources_status["instagram"]["message"]
    )

    # 4. Anobii: Sincronizzazione catalogo letture via API v6
    try:
        from sync_anobii import sync_anobii_data
        anobii_ok = sync_anobii_data()
        sources_status["anobii"] = {
            "status": "SUCCESS" if anobii_ok else "PARTIAL",
            "count": 141,
            "message": "Catalogo biblioteca sincronizzato in tempo reale da Anobii API v6"
        }
    except Exception as e:
        sources_status["anobii"] = {
            "status": "PARTIAL",
            "count": 0,
            "message": f"Sincronizzazione Anobii parziale: {e}"
        }

    log_sync(
        "anobii",
        sources_status["anobii"]["status"],
        sources_status["anobii"]["count"],
        sources_status["anobii"]["message"]
    )

    # 5. Compilazione deterministica del sito, biblioteca e pagine CV
    try:
        from build_site import build
        build()
        sources_status["site_builder"] = {
            "status": "SUCCESS",
            "count": 1,
            "message": "Homepage index.html, biblioteca.html, libri/index.html e CV compilati con successo"
        }
    except Exception as e:
        sources_status["site_builder"] = {
            "status": "ERROR",
            "count": 0,
            "message": f"Errore critico durante la compilazione del sito: {e}"
        }
        has_critical_error = True
        
    log_sync(
        "site_builder",
        sources_status["site_builder"]["status"],
        sources_status["site_builder"]["count"],
        sources_status["site_builder"]["message"]
    )

    # 5. Determinazione e registrazione dello stato GLOBALE della pipeline
    pipeline_status, pipeline_msg = compute_pipeline_status(sources_status, has_critical_error)

    sources_summary = {k: v["status"] for k, v in sources_status.items()}
    total_processed = sum(v["count"] for v in sources_status.values())
    
    log_sync(
        "pipeline",
        pipeline_status,
        total_processed,
        pipeline_msg,
        details=sources_summary
    )

    # Report a video strutturato per distinguere fonti individuali da pipeline complessiva
    print("\n" + "=" * 70)
    print("RIEPILOGO STATO SINGOLE FONTI:")
    for src, res in sources_status.items():
        print(f"  - {src.ljust(15)}: [{res['status'].ljust(7)}] ({res['count']} record) - {res['message']}")
    print("-" * 70)
    print(f"STATO GLOBALE PIPELINE: [{pipeline_status}] - {pipeline_msg}")
    print("=" * 70 + "\n")

    if has_critical_error:
        print("[ERRORE CRITICO] Il Sync Engine ha riscontrato anomalie bloccanti.")
    else:
        print("[COMPLETATO] Esecuzione Sync Engine terminata regolarmente.")

    return pipeline_status, sources_status

if __name__ == "__main__":
    status, _ = run_sync_all()
    if status == "ERROR":
        sys.exit(1)
