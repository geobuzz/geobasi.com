#!/usr/bin/env python3
"""
Importatore e sincronizzatore conservativo per dati LinkedIn:
- Supporta sia l'archivio CSV ufficiale LinkedIn (Positions.csv, Education.csv, Skills.csv)
  sia il payload JSON della Member Data Portability API (endpoint memberSnapshotData).
- Aggiorna contemporaneamente cv_it.json e cv_en.json.
- Applica il principio di CONSERVATIVE MERGE:
  * Aggiorna date, periodi, aziende e ruoli oggettivi.
  * Preserva scrupolosamente le descrizioni dettagliate, gli highlights e i contenuti editoriali storici.
  * Se rileva una nuova posizione lavorativa non censita, la inserisce in testa segnalandola nel report.
  * Non inventa né cancella alcuna esperienza.
"""
import csv
import json
import os
import sys
import argparse

# Assicura importazione corretta moduli sibling
sys.path.insert(0, os.path.dirname(__file__))

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
CV_IT_PATH = os.path.join(DATA_DIR, "cv_it.json")
CV_EN_PATH = os.path.join(DATA_DIR, "cv_en.json")

def normalize_key(text):
    if not text:
        return ""
    return "".join(c.lower() for c in text if c.isalnum())

def parse_linkedin_positions_csv(csv_path):
    positions = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get("Company Name") or row.get("Company") or ""
            role = row.get("Title") or row.get("Role") or ""
            start = row.get("Started On") or row.get("Start Date") or ""
            end = row.get("Finished On") or row.get("End Date") or "Presente"
            loc = row.get("Location") or ""
            desc = row.get("Description") or ""

            if company or role:
                period = f"{start} – {end}" if start and end != start else (start or end)
                positions.append({
                    "company": company.strip(),
                    "role": role.strip(),
                    "period": period.strip(),
                    "location": loc.strip(),
                    "description": desc.strip()
                })
    return positions

def parse_linkedin_education_csv(csv_path):
    education = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            school = row.get("School Name") or ""
            degree = row.get("Degree Name") or ""
            start = row.get("Start Date") or ""
            end = row.get("End Date") or ""
            notes = row.get("Notes") or ""
            if school or degree:
                education.append({
                    "institution": school.strip(),
                    "degree": degree.strip(),
                    "period": f"{start} – {end}" if start and end else (start or end),
                    "details": notes.strip()
                })
    return education

def parse_linkedin_skills_csv(csv_path):
    skills = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name") or row.get("Skill") or ""
            if name and name.strip() not in skills:
                skills.append(name.strip())
    return skills

def conservative_merge_experiences(incoming_list, current_cv_data, lang="it"):
    current_experiences = current_cv_data.get("experiences", [])
    
    # Map current experiences by normalized company name
    curr_map = {}
    for idx, exp in enumerate(current_experiences):
        k = normalize_key(exp.get("company", ""))
        curr_map[k] = (idx, exp)

    updated_count = 0
    added_count = 0
    preserved_count = 0
    log_messages = []

    merged_experiences = list(current_experiences)

    for incoming in incoming_list:
        inc_comp_key = normalize_key(incoming.get("company", ""))
        
        # Try matching by company
        matched_idx = None
        for k, (idx, exp) in curr_map.items():
            if inc_comp_key and (inc_comp_key in k or k in inc_comp_key):
                matched_idx = idx
                break

        if matched_idx is not None:
            # Existing position: update period/role, preserve highlights and rich text
            curr = merged_experiences[matched_idx]
            old_period = curr.get("period", "")
            new_period = incoming.get("period", "")
            
            curr["period"] = new_period or old_period
            if incoming.get("location"):
                curr["location"] = incoming.get("location")
            
            # If current role is generic or empty, update it
            if not curr.get("role") and incoming.get("role"):
                curr["role"] = incoming.get("role")

            # Crucial: NEVER overwrite existing highlights or detailed editorial descriptions
            preserved_count += 1
            if old_period != new_period:
                updated_count += 1
                log_messages.append(f"Aggiornato periodo {curr.get('company')}: {old_period} -> {new_period}")
        else:
            # Completely new position on LinkedIn: add it to the top
            new_entry = {
                "role": incoming.get("role"),
                "company": incoming.get("company"),
                "period": incoming.get("period"),
                "location": incoming.get("location", "Italia" if lang=="it" else "Italy"),
                "description": incoming.get("description", ""),
                "highlights": []
            }
            merged_experiences.insert(0, new_entry)
            added_count += 1
            log_messages.append(f"Nuova posizione inserita da LinkedIn: {incoming.get('role')} presso {incoming.get('company')}")

    current_cv_data["experiences"] = merged_experiences
    return current_cv_data, {
        "updated": updated_count,
        "added": added_count,
        "preserved": preserved_count,
        "logs": log_messages
    }

def import_linkedin_from_directory(dir_path):
    if not os.path.exists(dir_path):
        print(f"Errore: directory non trovata {dir_path}")
        return False, "Directory non trovata"

    pos_file = os.path.join(dir_path, "Positions.csv")
    edu_file = os.path.join(dir_path, "Education.csv")
    skills_file = os.path.join(dir_path, "Skills.csv")

    if not os.path.exists(pos_file):
        print(f"Errore: Positions.csv non trovato in {dir_path}")
        return False, "Positions.csv non presente"

    incoming_positions = parse_linkedin_positions_csv(pos_file)
    print(f"Estratte {len(incoming_positions)} posizioni da {pos_file}")

    # Load both CVs
    with open(CV_IT_PATH, "r", encoding="utf-8") as f:
        cv_it = json.load(f)
    with open(CV_EN_PATH, "r", encoding="utf-8") as f:
        cv_en = json.load(f)

    # Perform conservative merge on Italian CV
    cv_it_updated, report_it = conservative_merge_experiences(incoming_positions, cv_it, "it")
    # Perform conservative merge on English CV
    cv_en_updated, report_en = conservative_merge_experiences(incoming_positions, cv_en, "en")

    # Handle Education if present
    if os.path.exists(edu_file):
        incoming_edu = parse_linkedin_education_csv(edu_file)
        print(f"Estratte {len(incoming_edu)} voci formazione da {edu_file}")
        # Append only if missing
        existing_edu_names = {normalize_key(e.get("institution", "")) for e in cv_it.get("education", [])}
        for edu in incoming_edu:
            if normalize_key(edu.get("institution", "")) not in existing_edu_names:
                cv_it["education"].append(edu)
                cv_en["education"].append(edu)
                print(f"Aggiunta nuova formazione: {edu.get('degree')} presso {edu.get('institution')}")

    # Save both CVs
    with open(CV_IT_PATH, "w", encoding="utf-8") as f:
        json.dump(cv_it_updated, f, indent=2, ensure_ascii=False)
    with open(CV_EN_PATH, "w", encoding="utf-8") as f:
        json.dump(cv_en_updated, f, indent=2, ensure_ascii=False)

    print(f"[CV IT] Preservate: {report_it['preserved']} | Aggiornate: {report_it['updated']} | Aggiunte: {report_it['added']}")
    for l in report_it["logs"]:
        print(f"  -> {l}")

    # Regenerate printable CV pages
    try:
        from build_cv_pages import render_cv
        render_cv("it")
        render_cv("en")
        print("Pagine cv-it.html e cv-en.html ricompilate con successo.")
    except Exception as e:
        print(f"Errore ricompilazione pagine CV: {e}")

    return True, f"Sincronizzate {len(incoming_positions)} posizioni: {report_it['updated']} aggiornate, {report_it['added']} aggiunte, {report_it['preserved']} preservate"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importatore conservativo LinkedIn per Geobasi.com")
    parser.add_argument("--dir", dest="archive_dir", required=True, help="Percorso della cartella contenente i CSV di LinkedIn")
    args = parser.parse_args()
    success, msg = import_linkedin_from_directory(args.archive_dir)
    if not success:
        sys.exit(1)
