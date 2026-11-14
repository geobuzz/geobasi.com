# Architettura del Sistema di Sincronizzazione: Geobasi.com

Questo documento definisce il modello architetturale in cui ciascuna piattaforma esterna funge da **fonte principale dei dati (Single Source of Truth)** per Geobasi.com, specificando canali, protocolli di integrazione, gestione del fallback manuale e meccanismi di salvaguardia.

---

## 1. Mappatura Piattaforme & Fonti Dati

| Dominio Contenuto | Piattaforma Fonte | Meccanismo Principale | Fallback Assistito | Frequenza / Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **Percorso Professionale & CV** | **LinkedIn** | **Member Data Portability API** (DMA Art. 6.9 - SEE/UE) | Import archivio ufficiale CSV (`Positions.csv`, `Education.csv`) | On-demand / GitHub Action via Pull Request |
| **Biblioteca & Letture** | **Anobii** | Import CSV ufficiale esportato da aNobii + Open Library Covers API | Script CLI `update_books.py` | Periodico / a ogni aggiornamento letture |
| **Articoli & Note Editoriali** | **Substack** | **Feed RSS nativo** (`geobuzz.substack.com/feed`) | Script manuale `fetch_substack.py` | Automatico notturno (GitHub Actions) |
| **Fotografie del Territorio** | **Instagram** | **Instagram Graph API** (se account Creator) | Struttura JSON assistita (`data/photos.json`) | Periodico |

---

## 2. Analisi Tecnica di Fattibilità delle API Esterne

### A. LinkedIn — Member Data Portability API (SEE / GDPR / DMA)
- **Fattibilità Ufficiale**: **PIENAMENTE DISPONIBILE**. In quanto cittadino residente nell'Unione Europea/SEE (Italia), Microsoft/LinkedIn è designata come *gatekeeper* ai sensi del **Digital Markets Act (DMA, Articolo 6, paragrafo 9)**.
- **Dettagli Tecnici**:
  - La suite è inclusa nei **Regulatory Developer Products** del portale LinkedIn Developer.
  - La variante **Member Variant** consente all'utente di autorizzare una propria applicazione personale (script) a scaricare in formato JSON il footprint completo del proprio profilo (esperienze, date, aziende, formazione, competenze).
  - A differenza delle vecchie API Consumer di LinkedIn (fortemente limitate), questa API è garantita per legge e supporta l'estrazione continua dei dati.
- **Configurazione**:
  1. Creare una Developer App su [developer.linkedin.com](https://developer.linkedin.com).
  2. Richiedere il prodotto *Member Data Portability API* nella scheda *Products*.
  3. Generare il token OAuth e inserirlo come Secret protetto su GitHub (`LINKEDIN_PORTABILITY_TOKEN`).

### B. Instagram — Stato delle API Meta
- **Stato Ufficiale**: Meta ha **ufficialmente dismesso e spento la vecchia *Instagram Basic Display API* il 4 dicembre 2024**. Non esistono più API ufficiali per account personali generici.
- **Soluzione Conforme**:
  - Se l'account `@christian.bazzucchi` è impostato come **Account Professionale / Creator** (passaggio gratuito dall'app Instagram: *Impostazioni -> Strumenti per Creator*), è possibile utilizzare l'**Instagram Graph API** (`GET /me/media`) per recuperare permalink, immagini e didascalie.
  - Se l'account rimane personale, si adotta la procedura semi-automatica assistita (`data/photos.json`), evitando qualsiasi scraping illegale o fragile.

### C. Anobii — Esportazione Dati
- **Stato Ufficiale**: Anobii non espone API REST pubbliche documentate. L'applicazione web è una SPA generata lato client.
- **Soluzione Robusta**: Esportazione nativa da interfaccia (*Libreria -> Impostazioni -> Esporta libreria CSV*). Lo script `site/scripts/update_books.py` parsa il CSV, estrae ISBN, rating e commenti, recuperando le copertine tramite Open Library.

### D. Substack — Integrazione RSS
- **Stato Ufficiale**: Feed pubblico standard (`https://geobuzz.substack.com/feed`). Piena compatibilità con parsing XML/RSS, copertine in enclosure e gestione estratti.

---

## 3. I 5 Principi di Salvaguardia e Governance

1. **Automazione dove affidabile, procedura assistita dove necessario**:
   - Substack e LinkedIn Portability sono gestibili via GitHub Actions.
   - Anobii e Instagram adottano script di importazione sicuri e verificabili.
2. **Log delle sincronizzazioni (`data/sync_log.json` & `SYNC_LOG.md`)**:
   - Ogni operazione registra: timestamp, piattaforma, numero entità elaborate, esito e commit generato.
3. **Nessuna sovrascrittura silenziosa (Conservative Merge)**:
   - Se una scheda progetto o un'esperienza ha dettagli arricchiti manualmente (es. note riservate omesse, formulazioni specifiche), la sincronizzazione aggiorna solo i campi anagrafici (ruolo, periodo, date) senza cancellare gli highlight curati.
4. **Verifica preventiva prima della pubblicazione (Staging via Pull Request)**:
   - Per modifiche critiche (es. aggiornamento del CV professionale da LinkedIn), la GitHub Action non effettua un push cieco sul branch `main`, ma apre automaticamente una **Pull Request di aggiornamento** (`sync/linkedin-update`), consentendo di revisionare il diff prima della messa online.
5. **Tracciabilità completa e conformità legale**:
   - Nessun uso di web scraping abusivo o contrario ai Terms of Service delle piattaforme.
