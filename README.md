# Geobasi.com — Spazio Professionale Personale di Christian Bazzucchi

Repository ufficiale per il nuovo sito statico di **Christian Bazzucchi** (Geologo & Spatial Data Engineer).

- **Anteprima Live GitHub Pages**: [https://geobuzz.github.io/geobasi.com/](https://geobuzz.github.io/geobasi.com/)
- **Payoff**: *"Il territorio è fatto di dati. Il valore sta nel saperli connettere."*
- **Architettura**: Statico, data-driven, zero build tools obbligatori.

---

## Struttura del Progetto

```
geobasi.com/
├── index.html                 # Homepage completa (design cartografico ed editoriale)
├── cv-it.html                 # Curriculum Vitae consultabile e stampabile in PDF (Italiano)
├── cv-en.html                 # Curriculum Vitae consultabile e stampabile in PDF (Inglese)
├── data/                      # SINGLE SOURCE OF TRUTH (modificabile senza toccare codice)
│   ├── profile.json           # Bio, payoff, contatti, coordinate WGS84
│   ├── skills.json            # Competenze per domini verticali
│   ├── projects.json          # Casi di studio (Agrinex, Brunello, Environ, GISFO)
│   ├── cv_it.json / cv_en.json# Dati strutturati CV bilingue
│   ├── articles.json          # Articoli Substack sincronizzati via feed RSS
│   ├── books.json             # Biblioteca personale (Anobii) con quote e rating
│   └── photos.json            # Selezione fotografica territorio (Instagram)
├── scripts/                   # Automazioni e manutenzione
│   ├── fetch_substack.py      # Estrazione articoli RSS da geobuzz.substack.com
│   ├── update_books.py        # Importazione esportazione CSV Anobii + Open Library Covers
│   ├── import_linkedin.py     # Aggiornamento assistito da export CSV ufficiale LinkedIn
│   ├── build_cv_pages.py      # Compilazione pagine CV bilingui
│   └── create_historical_redirects.py # Generatore pagine redirect per URL storici
├── assets/                    # Immagini, scansioni storiche, badge e paper
├── archive/                   # Audit integrale del sito originario (Google Sites)
│   ├── AUDIT_RECUPERO_SITO.md # Matrice di conservazione, classificazione e inventario
│   ├── inventory.json         # Dump dei metadati e link storici
│   ├── pages/                 # Copia conforme delle pagine HTML originarie
│   ├── images/                # 16 immagini e scansioni originali ad alta risoluzione
│   └── documents/             # Testi e PDF estratti dai Google Docs originali
└── .github/workflows/         # GitHub Actions
    └── sync_substack.yml      # Sincronizzazione notturna programmata Substack RSS
```

---

## Obiettivo e Linee Guida per la Revisione Esterna
Questo repository è aperto per la revisione tecnica, contenutistica e visiva. In particolare:
1. **Identità e posizionamento**: verificare la coerenza della narrazione professionale (geologo + spatial data engineer, approccio orientato alla soluzione e all'open source maturo).
2. **Architettura dati**: verificare la rigorosa separazione tra dati (`data/*.json`) e presentazione (`index.html`, `cv-*.html`).
3. **Integrità storica**: verificare [AUDIT_RECUPERO_SITO.md](archive/AUDIT_RECUPERO_SITO.md) per confermare la piena conservazione di materiali, scansioni e URL storici.
