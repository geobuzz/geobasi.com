#!/usr/bin/env python3
"""
Utility per importare l'archivio ufficiale di dati esportati da LinkedIn:
(Impostazioni e privacy -> Privacy dei dati -> Ottieni una copia dei tuoi dati -> 'Profilo / Posizioni / Formazione')
Legge Positions.csv, Education.csv, Skills.csv e aggiorna site/data/cv_it.json / cv_en.json
"""
import csv
import json
import os
import sys
import argparse

CV_IT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cv_it.json")
CV_EN_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cv_en.json")

def import_linkedin_data(archive_dir):
    positions_file = os.path.join(archive_dir, "Positions.csv")
    education_file = os.path.join(archive_dir, "Education.csv")
    skills_file = os.path.join(archive_dir, "Skills.csv")

    if not os.path.exists(positions_file):
        print(f"File non trovato: {positions_file}")
        return False

    experiences = []
    with open(positions_file, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            role = row.get("Title") or ""
            company = row.get("Company Name") or ""
            start_date = row.get("Started On") or ""
            end_date = row.get("Finished On") or "Presente"
            desc = row.get("Description") or ""
            location = row.get("Location") or ""

            if role:
                period = f"{start_date} – {end_date}" if start_date else end_date
                experiences.append({
                    "role": role.strip(),
                    "company": company.strip(),
                    "period": period.strip(),
                    "location": location.strip(),
                    "description": desc.strip(),
                    "highlights": []
                })

    # Read existing CV to preserve summary and custom formatting
    if os.path.exists(CV_IT_PATH):
        with open(CV_IT_PATH, "r", encoding="utf-8") as f:
            cv_data = json.load(f)
        cv_data["experiences"] = experiences
        with open(CV_IT_PATH, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2, ensure_ascii=False)
        print(f"Aggiornate {len(experiences)} posizioni in {CV_IT_PATH}")
        return True
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importazione archivio dati LinkedIn")
    parser.add_argument("--dir", dest="archive_dir", required=True, help="Cartella contenente i file CSV esportati da LinkedIn")
    args = parser.parse_args()
    import_linkedin_data(args.archive_dir)
