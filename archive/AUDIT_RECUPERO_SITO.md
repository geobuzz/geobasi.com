# Audit Integrale e Recupero Contenuti: Geobasi.com

Documento di inventario, classificazione e piano di conservazione del sito storico prima della migrazione su GitHub Pages e Cloudflare.

---

## 1. Mappatura Pagine e Matrice di Intervento

| URL Esistente | Titolo Storico | Contenuti & Materiali Rilevati | Azione | Destinazione nel Nuovo Geobasi |
| :--- | :--- | :--- | :--- | :--- |
| **`/`** e **`/home`** | Home | Bio sintetica, elenco competenze geologiche/informatiche (15+ anni), coordinate Empoli, recapiti. | **Aggiornato** | Nuova homepage con design cartografico, payoff integrato, bio coerente e dati reali aggiornati al 2026. |
| **`/lavori/agrinex`** | Agrinex | Testo descrittivo del progetto WebGIS per agricoltura di precisione; 3 scansioni originali dell'articolo pubblicato su "L'Enologo" (dicembre). | **Mantenuto & Valorizzato** | Scheda progetto dedicata con le immagini ad alta risoluzione conservate; redirect permanente da `/lavori/agrinex/`. |
| **`/lavori/brunello_app`** | Brunello App | Presentazione dell'app mobile per il Consorzio del Brunello di Montalcino, badge App Store, Google Play, QR code. | **Mantenuto** | Scheda caso di studio con badge vettoriali storici conservati; redirect da `/lavori/brunello_app/`. |
| **`/lavori/environ`** | Environ | Descrizione del WebGIS per monitoraggio ambientale e bonifiche; link al paper scientifico Consoil 2008. | **Mantenuto** | Scheda caso di studio arricchita con il PDF originale Consoil 2008 scaricabile; redirect da `/lavori/environ/`. |
| **`/lavori`** | alcuni lavori | Indice sommario dei progetti. | **Riscritto** | Sostituito dalla sezione "Quadro d'Unione" (Portfolio) nella homepage, con redirect da `/lavori/`. |
| **`/CVga`** | CURRICULUM VITAE | CV in formato Google Doc italiano (`1uZp3owP...`) dal 2004 al presente (Environ, DBCAD, Accenture, Ingegnerie Toscane, Eagle Projects). | **Aggiornato** | Dati strutturati in `data/cv_it.json`, visualizzatore web e generazione PDF unificata; redirect da `/CVga/`. |
| **`/CVga/CV_En`** | English resume | Resume in formato Google Doc inglese (`1fqbXstZwS...`). | **Aggiornato** | Dati strutturati in `data/cv_en.json`, versione consultabile e PDF in lingua inglese; redirect da `/CVga/CV_En/`. |
| **`/libri`** | libri / STO LEGGENDO | Selezione di letture (Lovecraft, Neuman, Chiang, Clarke, Hoyle, Hearn, Rothbard) con recensioni personali. | **Mantenuto & Integrato** | Sezione "Biblioteca" collegata ad Anobii con copertine, quote e status; redirect da `/libri/`. |
| **`/blog`** | blog | Vecchio contenitore note. | **Aggiornato** | Sostituito dall'integrazione automatica via feed RSS con il blog Substack (`geobuzz.substack.com`); redirect da `/blog/`. |
| **`/share/ENVIRON_webgis.pdf`** | Documento Consoil 2008 | Presentazione tecnica WebGIS Environ a Consoil 2008 (1.45 MB). | **Mantenuto Inalterato** | File fisico collocato in `site/share/ENVIRON_webgis.pdf` per preservare il link esatto senza 404. |

---

## 2. Inventario Asset Multimediali Recuperati

Tutti gli asset originali sono stati scaricati e archiviati localmente in `site/archive/`:

1. **Agrinex (Rivista "L'Enologo")**:
   - `img_2_lavori_agrinex.jpg` (367 KB) — Copertina e introduzione articolo L'Enologo.
   - `img_3_lavori_agrinex.jpg` (626 KB) — Tavole cartografiche WebGIS e indici NDVI/NDRE.
   - `img_4_lavori_agrinex.jpg` (570 KB) — Dettaglio zonazione pedologica e conclusioni agronomiche.
2. **Brunello App**:
   - `img_5_lavori_brunello_app.jpg` (72 KB) — Schermate dell'applicazione mobile.
   - `Download_on_the_App_Store_Badge_US-UK_135x40.svg` (SVG originale).
   - `google-play-badge.png` (Badge ufficiale Google Play).
   - `onlink_to_n9esxy.svg` (QR Code originale di download).
3. **Environ WebGIS**:
   - `ENVIRON_webgis.pdf` (1.45 MB) — Pubblicazione Consoil 2008 conservata in `site/share/`.
4. **Documenti Ufficiali di Carriera**:
   - `cv_italiano_originale.pdf` e `cv_italiano_originale.txt` — Testo integrale dal Google Doc.
   - `cv_inglese_originale.pdf` e `cv_inglese_originale.txt` — Testo integrale dal Google Doc.
5. **Copertine Libri Storiche**:
   - 10 immagini di copertina salvate in `site/archive/images/` (Lovecraft, Neuman, Chiang, Clarke, Tolkien, Hoyle, Hearn, Rothbard).

---

## 3. Strategia di Conservazione degli URL Storici (Zero Broken Links)

Per garantire la piena compatibilità con i motori di ricerca e i link esterni pre-esistenti:
- Verranno create le relative pagine HTML statiche nelle cartelle storiche (`/lavori/agrinex/index.html`, `/lavori/brunello_app/index.html`, `/lavori/environ/index.html`, `/libri/index.html`, `/CVga/index.html`, ecc.) contenenti:
  - Canonical link alla sezione corrispondente.
  - Redirect immediato `meta http-equiv="refresh"` per gli utenti.
  - Testo completo accessibile per i crawler dei motori di ricerca.
- Il percorso `/share/ENVIRON_webgis.pdf` rimane invariato come file statico nativo.
