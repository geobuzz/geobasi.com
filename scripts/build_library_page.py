#!/usr/bin/env python3
"""
Compilatore della pagina dedicata alla Biblioteca Personale per Geobasi.com:
- Genera site/biblioteca.html e aggiorna site/libri/index.html.
- Mostra l'intero catalogo di 141 libri sincronizzato con Anobii.
- Include filtri interattivi istantanei (Tutti, In Lettura, Con Recensione, Valutati, Letti).
- Include barra di ricerca in tempo reale per titolo, autore ed editore (vanilla JS, zero dipendenze).
- Presenta copertine reali locali (Amazon CDN / Open Library) o legature editoriali tipografiche.
- Supporta note critiche e recensioni integrali tramite elementi HTML5 nativi e accessibili.
- Mantiene l'identità visiva cartografica del sito (isoipse di Valtopina e graticola geodetica).
"""
import os
import sys
import json
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_BIBLIO = os.path.join(BASE_DIR, "biblioteca.html")
OUTPUT_LIBRI = os.path.join(BASE_DIR, "libri", "index.html")

def load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or []

def render_biblioteca_page():
    books = load_json("books.json", [])
    profile = load_json("profile.json", {})
    sync_logs = load_json("sync_log.json", [])

    last_sync_text = "N/D"
    if sync_logs and isinstance(sync_logs, list):
        last_sync_text = sync_logs[0].get("timestamp", "N/D")[:16].replace("T", " ") + " UTC"

    total_books = len(books)
    in_progress_books = [b for b in books if b.get("status") == "in_corso"]
    reviewed_books = [b for b in books if b.get("review")]
    rated_books = [b for b in books if float(b.get("rating", 0)) > 0]
    finished_books = [b for b in books if b.get("status") != "in_corso"]

    # Ordinamento prioritario:
    # 0 = In corso
    # 1 = Con recensione scritta (ordinati per voto decrescente)
    # 2 = Con voto (ordinati per voto decrescente)
    # 3 = Altri libri letti
    def biblio_sort_key(b):
        status = b.get("status", "")
        rating = float(b.get("rating", 0))
        has_review = bool(b.get("review"))
        if status == "in_corso":
            return (0, 0)
        elif has_review:
            return (1, -rating)
        elif rating > 0:
            return (2, -rating)
        return (3, 0)

    sorted_books = sorted(books, key=biblio_sort_key)

    books_cards_html = ""
    for b in sorted_books:
        title = b.get("title", "")
        subtitle = b.get("subtitle", "")
        author = b.get("author", "")
        publisher = b.get("publisher", "")
        isbn = b.get("isbn", "")
        status = b.get("status", "letto")
        rating = float(b.get("rating", 0))
        review = b.get("review", "")
        cover = b.get("cover", "")
        anobii_url = b.get("anobii_url") or profile.get("contacts", {}).get("anobii", "https://www.anobii.com/it/01d6d75099d9c1d4bb/profile")

        is_reading = (status == "in_corso")
        card_cls = "book-card in-progress" if is_reading else "book-card"
        badge_cls = "in-progress" if is_reading else "finished"
        
        if is_reading:
            badge_text = "&bull; IN LETTURA"
        elif rating > 0:
            stars = f" &bull; {'★' * int(rating)}{'½' if rating % 1 >= 0.5 else ''} {rating}/5"
            badge_text = f"LETTO{stars}"
        else:
            badge_text = "LETTO"

        # Markup copertina
        cover_path = os.path.join(BASE_DIR, cover) if cover and not cover.startswith("http") else None
        if cover and (cover.startswith("http") or (cover_path and os.path.exists(cover_path))):
            cover_markup = f'<img src="{cover}" alt="{title}" loading="lazy" />'
        else:
            pub_span = f'<span class="book-cover-pub">{publisher}</span>' if publisher else ''
            cover_markup = f'''
            <div class="book-cover-placeholder">
              <span class="book-cover-title">{title}</span>
              <span class="book-cover-author">{author}</span>
              {pub_span}
            </div>
            '''

        # Markup recensione integrale / estratto
        review_markup = ""
        if review:
            if len(review) > 160:
                short_text = review[:155] + "..."
                review_markup = f'''
                <div class="book-review-box">
                  <p class="book-quote">"{short_text}"</p>
                  <details class="book-review-details">
                    <summary>Leggi nota completa</summary>
                    <div class="book-full-review">{review}</div>
                  </details>
                </div>
                '''
            else:
                review_markup = f'''
                <div class="book-review-box">
                  <p class="book-quote">"{review}"</p>
                </div>
                '''

        meta_parts = []
        if author:
            meta_parts.append(f'<span class="b-author">{author}</span>')
        if publisher:
            meta_parts.append(f'<span class="b-pub">{publisher}</span>')

        meta_line = " &bull; ".join(meta_parts)
        subtitle_markup = f'<div class="book-subtitle">{subtitle}</div>' if subtitle else ''

        # Attributi di filtraggio per Vanilla JS
        search_blob = f"{title} {subtitle} {author} {publisher} {isbn}".lower()
        filter_status = "in_corso" if is_reading else "letto"
        has_rev_attr = "1" if bool(review) else "0"
        has_rating_attr = "1" if rating > 0 else "0"

        books_cards_html += f"""
        <article class="{card_cls}" 
                 data-status="{filter_status}" 
                 data-review="{has_rev_attr}" 
                 data-rating="{has_rating_attr}" 
                 data-search="{search_blob}">
          <div class="book-card-top">
            <span class="book-status-badge {badge_cls}">{badge_text}</span>
            <a href="{anobii_url}" class="anobii-link-btn" target="_blank" rel="noopener noreferrer" title="Vedi scheda '{title}' su Anobii">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              <span>Anobii &nearr;</span>
            </a>
          </div>
          <a href="{anobii_url}" target="_blank" rel="noopener noreferrer" class="book-cover-wrap" style="display:block; text-decoration:none;" title="Vedi '{title}' su Anobii">
            {cover_markup}
          </a>
          <h3 class="book-title"><a href="{anobii_url}" target="_blank" rel="noopener noreferrer" style="color:inherit; text-decoration:none;" title="Vedi scheda su Anobii">{title}</a></h3>
          {subtitle_markup}
          <div class="book-meta">{meta_line}</div>
          {review_markup}
        </article>
        """

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>La Mia Biblioteca — {profile.get('name', 'Christian Bazzucchi')} | geobasi.com</title>
  <meta name="description" content="Catalogo completo della biblioteca personale di Christian Bazzucchi: letture in corso, recensioni critiche e archivio sincronizzato con Anobii.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-paper: #FBF9F4;
      --bg-surface: #F3ECE1;
      --bg-surface-elevated: #FFFFFF;
      --border-carto: #DDD5C7;
      --border-subtle: #EBE4D8;
      
      --ink-primary: #12222E;
      --ink-secondary: #3D505D;
      --ink-muted: #6B7C87;
      
      --accent-copper: #C25928;
      --accent-copper-hover: #A8481A;
      --accent-copper-soft: rgba(194, 89, 40, 0.08);
      
      --font-serif: "Newsreader", Georgia, serif;
      --font-sans: "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
      --font-mono: "Fira Code", monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg-paper);
      color: var(--ink-primary);
      font-family: var(--font-sans);
      font-size: 16px;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      position: relative;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    .carto-topo-bg {{
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      pointer-events: none;
      z-index: 0;
      background-image: url('assets/img/valtopina_contours.svg');
      background-size: cover;
      background-position: center center;
      background-repeat: no-repeat;
      opacity: 0.38;
    }}

    .carto-graticule {{
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      pointer-events: none;
      z-index: 0;
      opacity: 0.20;
      background-image: 
        linear-gradient(to right, var(--border-subtle) 1px, transparent 1px),
        linear-gradient(to bottom, var(--border-subtle) 1px, transparent 1px);
      background-size: 80px 80px;
    }}

    .wrapper {{
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 0 clamp(20px, 3.5vw, 48px);
      position: relative;
      z-index: 1;
    }}

    /* Header Nav */
    header.site-header {{
      background: rgba(251, 249, 244, 0.92);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border-carto);
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .nav-inner {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      height: 64px;
    }}

    .nav-logo {{
      font-family: var(--font-serif);
      font-size: 20px;
      font-weight: 600;
      color: var(--ink-primary);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .nav-logo:hover {{ color: var(--accent-copper); }}

    .nav-links {{
      display: flex;
      align-items: center;
      gap: 20px;
      list-style: none;
    }}

    .nav-link {{
      font-family: var(--font-mono);
      font-size: 13px;
      color: var(--ink-secondary);
      text-decoration: none;
      transition: color 0.2s;
    }}

    .nav-link:hover {{ color: var(--accent-copper); }}

    .btn-outline {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--accent-copper);
      background: transparent;
      border: 1px solid var(--accent-copper);
      padding: 6px 14px;
      text-decoration: none;
      transition: all 0.2s;
      border-radius: 2px;
    }}

    .btn-outline:hover {{
      background: var(--accent-copper);
      color: #FFF;
    }}

    /* Main Page Content */
    main {{
      flex: 1;
      padding: 48px 0 80px;
    }}

    .biblio-hero {{
      margin-bottom: 36px;
      padding-bottom: 32px;
      border-bottom: 1px solid var(--border-carto);
    }}

    .biblio-tag {{
      font-family: var(--font-mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--accent-copper);
      display: inline-block;
      margin-bottom: 8px;
    }}

    .biblio-title {{
      font-family: var(--font-serif);
      font-size: clamp(32px, 4.5vw, 48px);
      font-weight: 600;
      color: var(--ink-primary);
      line-height: 1.15;
      margin-bottom: 12px;
    }}

    .biblio-desc {{
      font-size: 17px;
      color: var(--ink-secondary);
      max-width: 820px;
      line-height: 1.6;
      margin-bottom: 24px;
    }}

    /* Stats Bar */
    .stats-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-carto);
      padding: 16px 20px;
      border-radius: 2px;
      margin-bottom: 32px;
    }}

    .stat-box {{
      display: flex;
      flex-direction: column;
    }}

    .stat-num {{
      font-family: var(--font-serif);
      font-size: 28px;
      font-weight: 600;
      color: var(--ink-primary);
      line-height: 1;
    }}

    .stat-label {{
      font-family: var(--font-mono);
      font-size: 11px;
      text-transform: uppercase;
      color: var(--ink-muted);
      letter-spacing: 0.05em;
      margin-top: 4px;
    }}

    /* Filter & Search Bar */
    .filter-panel {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-carto);
      padding: 18px 24px;
      margin-bottom: 32px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .filter-row {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}

    .filter-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .filter-chip {{
      background: var(--bg-surface);
      border: 1px solid var(--border-carto);
      color: var(--ink-secondary);
      font-family: var(--font-mono);
      font-size: 12px;
      padding: 6px 14px;
      cursor: pointer;
      transition: all 0.2s;
      border-radius: 2px;
    }}

    .filter-chip:hover {{
      border-color: var(--accent-copper);
      color: var(--accent-copper);
    }}

    .filter-chip.active {{
      background: var(--accent-copper);
      border-color: var(--accent-copper);
      color: #FFF;
      font-weight: 600;
    }}

    .search-wrap {{
      flex: 1;
      max-width: 420px;
      min-width: 240px;
      position: relative;
    }}

    .search-input {{
      width: 100%;
      background: var(--bg-paper);
      border: 1px solid var(--border-carto);
      color: var(--ink-primary);
      font-family: var(--font-sans);
      font-size: 14px;
      padding: 8px 12px 8px 34px;
      border-radius: 2px;
      transition: border-color 0.2s;
    }}

    .search-input:focus {{
      outline: none;
      border-color: var(--accent-copper);
    }}

    .search-icon {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--ink-muted);
      pointer-events: none;
      font-size: 14px;
    }}

    .results-info {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--ink-muted);
    }}

    /* Library Grid */
    .library-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 24px;
    }}

    @media (max-width: 1200px) {{
      .library-grid {{ grid-template-columns: repeat(3, 1fr); gap: 20px; }}
    }}
    @media (max-width: 860px) {{
      .library-grid {{ grid-template-columns: repeat(2, 1fr); gap: 16px; }}
    }}
    @media (max-width: 520px) {{
      .library-grid {{ grid-template-columns: 1fr; }}
    }}

    .book-card {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-carto);
      padding: 16px;
      display: flex;
      flex-direction: column;
      position: relative;
      transition: transform 0.2s, box-shadow 0.2s;
    }}

    .book-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(18, 34, 46, 0.06);
    }}

    .book-card.in-progress {{
      border: 1px solid var(--accent-copper);
      background: #FFFDF9;
    }}

    .book-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}

    .anobii-link-btn {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--accent-copper);
      text-decoration: none;
      padding: 2px 6px;
      border: 1px solid rgba(194, 89, 40, 0.3);
      border-radius: 2px;
      transition: all 0.15s ease;
      background: var(--bg-paper);
    }}
    .anobii-link-btn:hover {{
      background: var(--accent-copper);
      color: #FFFFFF;
      border-color: var(--accent-copper);
    }}

    .book-status-badge {{
      font-family: var(--font-mono);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 3px 6px;
      border-radius: 2px;
      display: inline-block;
    }}

    .book-status-badge.in-progress {{
      background: var(--accent-copper-soft);
      color: var(--accent-copper);
      font-weight: 600;
      border: 1px solid rgba(194, 89, 40, 0.3);
    }}

    .book-status-badge.finished {{
      background: var(--bg-surface);
      color: var(--ink-muted);
      border: 1px solid var(--border-carto);
    }}

    .book-cover-wrap {{
      width: 100%;
      height: 220px;
      background: var(--bg-surface);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 14px;
      border: 1px solid var(--border-subtle);
      overflow: hidden;
    }}

    .book-cover-wrap img {{
      max-height: 100%;
      max-width: 100%;
      object-fit: contain;
    }}

    .book-cover-placeholder {{
      padding: 16px 12px;
      text-align: center;
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 6px;
      height: 100%;
      width: 100%;
      background: #ECE5D8;
      border: 1px dashed var(--border-carto);
    }}

    .book-cover-placeholder .book-cover-title {{
      font-family: var(--font-serif);
      font-size: 14px;
      font-weight: 600;
      color: var(--ink-primary);
      line-height: 1.25;
    }}

    .book-cover-placeholder .book-cover-author {{
      font-family: var(--font-sans);
      font-size: 12px;
      color: var(--ink-secondary);
    }}

    .book-cover-placeholder .book-cover-pub {{
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--ink-muted);
      text-transform: uppercase;
    }}

    .book-title {{
      font-family: var(--font-serif);
      font-size: 16px;
      font-weight: 600;
      color: var(--ink-primary);
      line-height: 1.3;
      margin-bottom: 4px;
    }}

    .book-subtitle {{
      font-size: 12px;
      color: var(--ink-muted);
      margin-bottom: 6px;
      line-height: 1.35;
    }}

    .book-meta {{
      font-size: 13px;
      color: var(--ink-secondary);
      margin-bottom: 12px;
      line-height: 1.4;
    }}

    .book-review-box {{
      margin-top: auto;
      padding-top: 10px;
      border-top: 1px dashed var(--border-carto);
    }}

    .book-quote {{
      font-family: var(--font-serif);
      font-style: italic;
      font-size: 13px;
      color: var(--ink-secondary);
      line-height: 1.45;
    }}

    .book-review-details {{
      margin-top: 6px;
    }}

    .book-review-details summary {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--accent-copper);
      cursor: pointer;
      user-select: none;
    }}

    .book-review-details summary:hover {{
      text-decoration: underline;
    }}

    .book-full-review {{
      margin-top: 8px;
      padding: 10px;
      background: var(--bg-paper);
      border-left: 2px solid var(--accent-copper);
      font-size: 12px;
      line-height: 1.5;
      color: var(--ink-primary);
      white-space: pre-line;
    }}

    .empty-state {{
      grid-column: 1 / -1;
      padding: 60px 20px;
      text-align: center;
      background: var(--bg-surface-elevated);
      border: 1px dashed var(--border-carto);
      color: var(--ink-muted);
      display: none;
    }}

    /* Footer */
    footer.site-footer {{
      background: var(--bg-surface);
      border-top: 1px solid var(--border-carto);
      padding: 32px 0;
      margin-top: auto;
    }}

    .footer-inner {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--ink-muted);
    }}

    .footer-inner a {{
      color: var(--ink-secondary);
      text-decoration: none;
    }}

    .footer-inner a:hover {{
      color: var(--accent-copper);
    }}
  </style>
</head>
<body>
  <div class="carto-topo-bg" aria-hidden="true"></div>
  <div class="carto-graticule" aria-hidden="true"></div>

  <!-- Header -->
  <header class="site-header">
    <div class="wrapper">
      <div class="nav-inner">
        <a href="/" class="nav-logo">
          <span>&larr;</span>
          <span>{profile.get('name', 'Christian Bazzucchi')}</span>
          <span style="font-family: var(--font-mono); font-size: 12px; color: var(--ink-muted); font-weight: 400;">geobasi.com</span>
        </a>
        <ul class="nav-links">
          <li><a href="/" class="nav-link">&larr; Home</a></li>
          <li><a href="/#articoli" class="nav-link">Articoli</a></li>
          <li><a href="/#progetti" class="nav-link">Progetti</a></li>
          <li><a href="{profile.get('contacts', {}).get('anobii', 'https://www.anobii.com/it/01d6d75099d9c1d4bb/profile')}" class="btn-outline" target="_blank" rel="noopener">Profilo su Anobii &nearr;</a></li>
        </ul>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main>
    <div class="wrapper">
      <!-- Hero -->
      <section class="biblio-hero">
        <span class="biblio-tag">SEZIONE 04 &bull; ARCHIVIO LETTURE &bull; BIBLIOTECA PERSONALE</span>
        <h1 class="biblio-title">La Mia Biblioteca</h1>
        <p class="biblio-desc">
          Catalogo integrale delle letture sincronizzato con Anobii: volumi attualmente in lettura, note critiche, recensioni e archivio storico. Le copertine sono verificate tramite Amazon CDN e Open Library.
        </p>

        <!-- Stats Bar -->
        <div class="stats-bar">
          <div class="stat-box">
            <span class="stat-num">{total_books}</span>
            <span class="stat-label">Libri Censiti</span>
          </div>
          <div class="stat-box">
            <span class="stat-num">{len(in_progress_books)}</span>
            <span class="stat-label">In Lettura</span>
          </div>
          <div class="stat-box">
            <span class="stat-num">{len(reviewed_books)}</span>
            <span class="stat-label">Recensioni Scritte</span>
          </div>
          <div class="stat-box">
            <span class="stat-num">{len(rated_books)}</span>
            <span class="stat-label">Valutati con Voto</span>
          </div>
        </div>

        <!-- Filter Panel -->
        <div class="filter-panel">
          <div class="filter-row">
            <div class="filter-chips">
              <button class="filter-chip active" data-filter="all">Tutti ({total_books})</button>
              <button class="filter-chip" data-filter="in_corso">In Lettura ({len(in_progress_books)})</button>
              <button class="filter-chip" data-filter="reviewed">Con Recensione ({len(reviewed_books)})</button>
              <button class="filter-chip" data-filter="rated">Valutati ★ ({len(rated_books)})</button>
              <button class="filter-chip" data-filter="letto">Letti ({len(finished_books)})</button>
            </div>
            <div class="search-wrap">
              <span class="search-icon">&telrec;</span>
              <input type="text" id="library-search" class="search-input" placeholder="Cerca titolo, autore, editore o parola chiave..." autocomplete="off">
            </div>
          </div>
          <div class="results-info">
            Mostrati <strong id="visible-count">{total_books}</strong> libri su {total_books}
          </div>
        </div>
      </section>

      <!-- Grid -->
      <section class="library-grid" id="books-container">
        {books_cards_html}
        <div class="empty-state" id="empty-state">
          <h3>Nessun libro trovato</h3>
          <p style="margin-top: 8px;">Nessun volume corrisponde ai filtri o al termine di ricerca inserito.</p>
        </div>
      </section>
    </div>
  </main>

  <!-- Footer -->
  <footer class="site-footer">
    <div class="wrapper">
      <div class="footer-inner">
        <div>
          &copy; 2026 {profile.get('name', 'Christian Bazzucchi')} &bull; <a href="/">geobasi.com</a>
        </div>
        <div>
          Biblioteca sincronizzata da Anobii &bull; Ultima sincronizzazione: {last_sync_text}
        </div>
      </div>
    </div>
  </footer>

  <!-- Vanilla JS Filtering & Search -->
  <script>
    (function() {{
      const searchInput = document.getElementById('library-search');
      const filterChips = document.querySelectorAll('.filter-chip');
      const container = document.getElementById('books-container');
      const cards = container.querySelectorAll('.book-card');
      const visibleCountElem = document.getElementById('visible-count');
      const emptyState = document.getElementById('empty-state');

      let currentFilter = 'all';
      let currentQuery = '';

      function applyFilters() {{
        let visibleCount = 0;
        const q = currentQuery.trim().toLowerCase();

        cards.forEach(card => {{
          const cardStatus = card.dataset.status;
          const cardHasReview = card.dataset.review === '1';
          const cardHasRating = card.dataset.rating === '1';
          const cardSearch = card.dataset.search || '';

          // Filtro categoria
          let matchCategory = true;
          if (currentFilter === 'in_corso') {{
            matchCategory = (cardStatus === 'in_corso');
          }} else if (currentFilter === 'reviewed') {{
            matchCategory = cardHasReview;
          }} else if (currentFilter === 'rated') {{
            matchCategory = cardHasRating;
          }} else if (currentFilter === 'letto') {{
            matchCategory = (cardStatus === 'letto');
          }}

          // Filtro ricerca testuale
          let matchSearch = true;
          if (q.length > 0) {{
            matchSearch = cardSearch.includes(q);
          }}

          if (matchCategory && matchSearch) {{
            card.style.display = '';
            visibleCount++;
          }} else {{
            card.style.display = 'none';
          }}
        }});

        visibleCountElem.textContent = visibleCount;
        if (visibleCount === 0) {{
          emptyState.style.display = 'block';
        }} else {{
          emptyState.style.display = 'none';
        }}
      }}

      filterChips.forEach(chip => {{
        chip.addEventListener('click', () => {{
          filterChips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          currentFilter = chip.dataset.filter;
          applyFilters();
        }});
      }});

      searchInput.addEventListener('input', (e) => {{
        currentQuery = e.target.value;
        applyFilters();
      }});
    }})();
  </script>
</body>
</html>
"""

    os.makedirs(os.path.dirname(OUTPUT_LIBRI), exist_ok=True)
    with open(OUTPUT_BIBLIO, "w", encoding="utf-8") as f:
        f.write(html)
    with open(OUTPUT_LIBRI, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Compilate con successo le pagine della biblioteca: {OUTPUT_BIBLIO} e {OUTPUT_LIBRI} ({total_books} libri).")
    return True

if __name__ == "__main__":
    render_biblioteca_page()
