#!/usr/bin/env python3
"""
Compilatore e generatore statico per Geobasi.com:
- Legge i file JSON in data/ (profile, skills, projects, articles, books, photos, sync_log).
- Compila index.html assicurando che ogni modifica ai file JSON si rifletta immediatamente nell'HTML.
- Compila cv-it.html e cv-en.html richiamando build_cv_pages.
- Elimina qualsiasi discrepanza tra dati e interfaccia.
"""
import json
import os
import sys

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_INDEX = os.path.join(BASE_DIR, "index.html")

def load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or []

def build():
    profile = load_json("profile.json", {})
    skills = load_json("skills.json", [])
    projects = load_json("projects.json", [])
    articles = load_json("articles.json", [])
    books = load_json("books.json", [])
    photos = load_json("photos.json", [])
    sync_logs = load_json("sync_log.json", [])

    last_sync_text = "N/D"
    if sync_logs and isinstance(sync_logs, list):
        last_sync_text = sync_logs[0].get("timestamp", "N/D")[:16].replace("T", " ") + " UTC"

    # Skills HTML
    skills_html = ""
    for s in skills:
        tools_li = "".join([f"<li>{t}</li>" for t in s.get("tools", [])])
        skills_html += f"""
        <div class="skill-card">
          <h4>{s.get('category')}</h4>
          <p>{s.get('description')}</p>
          <ul>{tools_li}</ul>
        </div>
        """

    # Projects HTML
    projects_html = ""
    for p in projects:
        pid = p.get("id")
        tags_spans = "".join([f'<span class="project-tag">{t}</span>' for t in p.get("tags", [])])
        
        # Specific historical assets
        assets_preview = ""
        action_btn = ""
        if pid == "agrinex":
            assets_preview = """
            <div class="project-assets-preview">
              <a href="assets/img/projects/agrinex_enologo_p1.jpg" target="_blank" title="Scansione articolo L'Enologo - Copertina">
                <img src="assets/img/projects/agrinex_enologo_p1.jpg" alt="Articolo L'Enologo" class="project-thumb">
              </a>
              <a href="assets/img/projects/agrinex_enologo_p2.jpg" target="_blank" title="Scansione articolo L'Enologo - Tavole WebGIS">
                <img src="assets/img/projects/agrinex_enologo_p2.jpg" alt="Tavole Agrinex" class="project-thumb">
              </a>
              <a href="assets/img/projects/agrinex_enologo_p3.jpg" target="_blank" title="Scansione articolo L'Enologo - Zonazione">
                <img src="assets/img/projects/agrinex_enologo_p3.jpg" alt="Zonazione Agrinex" class="project-thumb">
              </a>
            </div>
            """
            action_btn = '<a href="assets/img/projects/agrinex_enologo_p1.jpg" class="project-link" target="_blank">Visualizza l\'articolo su L\'Enologo &rarr;</a>'
        elif pid == "brunello":
            assets_preview = """
            <div class="project-assets-preview">
              <a href="assets/img/projects/brunello_app_screens.jpg" target="_blank">
                <img src="assets/img/projects/brunello_app_screens.jpg" alt="Schermate Brunello App" class="project-thumb">
              </a>
              <img src="assets/img/projects/Download_on_the_App_Store_Badge_US-UK_135x40.svg" alt="App Store" style="height: 32px; align-self: center;">
              <img src="assets/img/projects/google-play-badge.png" alt="Google Play" style="height: 32px; align-self: center;">
            </div>
            """
            action_btn = '<span class="project-link" style="color: var(--ink-muted);">Progetto Consorzio del Brunello</span>'
        elif pid == "environ":
            action_btn = '<a href="share/ENVIRON_webgis.pdf" class="project-link" target="_blank">Scarica Paper Scientifico Consoil 2008 (PDF) &rarr;</a>'
        elif pid == "gisfo":
            action_btn = f'<a href="{p.get("link_url", "#")}" class="project-link" target="_blank">{p.get("link_label", "Approfondimento")} &rarr;</a>'

        projects_html += f"""
        <article class="project-card" id="{pid}">
          <div>
            <div class="project-card-header">
              <span class="project-id">PROJ &bull; {p.get('title').upper()}</span>
              <span class="project-context">{p.get('period')}</span>
            </div>
            <h3 class="project-title">{p.get('title')}</h3>
            <p class="project-subtitle">{p.get('subtitle')}</p>
            <p class="project-desc">{p.get('summary')}</p>
            {assets_preview}
            <div class="project-tags">{tags_spans}</div>
          </div>
          <div class="project-actions">{action_btn}</div>
        </article>
        """

    # Books HTML (In corso first, then Letto)
    books_sorted = sorted(books, key=lambda b: (0 if b.get("status") == "in_corso" else 1))
    books_html = ""
    for b in books_sorted[:8]:
        is_reading = (b.get("status") == "in_corso")
        badge_cls = "in-progress" if is_reading else "finished"
        badge_text = "&bull; IN LETTURA" if is_reading else f"TERMINATO &bull; {b.get('rating', 5)}/5"
        card_cls = "book-card in-progress" if is_reading else "book-card"
        
        cover_img = b.get("cover")
        if cover_img:
            cover_markup = f'<img src="{cover_img}" alt="{b.get("title")}" />'
        else:
            cover_markup = f'<div style="font-family: var(--font-serif); font-size: 13px; text-align: center; padding: 12px; color: var(--ink-muted);">{b.get("title")}<br><small>{b.get("author")}</small></div>'

        quote_markup = ""
        if b.get("quote"):
            quote_markup = f'<p class="book-quote">"{b.get("quote")}"</p>'
        elif b.get("note"):
            quote_markup = f'<p class="book-quote">{b.get("note")}</p>'

        books_html += f"""
        <div class="{card_cls}">
          <span class="book-status-badge {badge_cls}">{badge_text}</span>
          <div class="book-cover-wrap">{cover_markup}</div>
          <h4 class="book-title">{b.get('title')}</h4>
          <p class="book-author">{b.get('author')}</p>
          {quote_markup}
        </div>
        """

    # Substack Articles HTML
    articles_html = ""
    for a in articles[:6]:
        articles_html += f"""
        <a href="{a.get('link')}" class="article-card" target="_blank">
          <div>
            <div class="article-meta">{a.get('date')} &bull; SUBSTACK</div>
            <h3 class="article-title">{a.get('title')}</h3>
            <p class="article-excerpt">{a.get('excerpt')}</p>
          </div>
          <span class="article-read-more">Leggi su Substack &rarr;</span>
        </a>
        """

    # Photos HTML (Strictly authentic, NO stock photos)
    photos_html = ""
    valid_photos = [p for p in photos if p.get("permalink")]
    if valid_photos:
        for ph in valid_photos:
            img_url = ph.get("image_url", "").strip()
            if img_url:
                img_block = f'<img src="{img_url}" alt="{ph.get("caption", "Fotografia")}" loading="lazy">'
            else:
                img_block = f"""
                <div style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--bg-surface); padding: 20px; text-align: center;">
                  <span style="font-family: var(--font-mono); font-size: 24px; color: var(--accent-copper); margin-bottom: 8px;">📷</span>
                  <span style="font-family: var(--font-mono); font-size: 11px; color: var(--ink-muted);">POST INSTAGRAM UFFICIALE</span>
                </div>
                """
            
            photos_html += f"""
            <a href="{ph.get('permalink')}" class="photo-card" target="_blank" rel="noopener">
              <div class="photo-img-wrap">
                {img_block}
              </div>
              <div class="photo-info">
                <div class="photo-location">{ph.get('location', 'Territorio')}</div>
                <div class="photo-coords">{ph.get('coordinates', '')}</div>
                <p class="photo-caption">{ph.get('caption', '')}</p>
              </div>
            </a>
            """
    else:
        # Authentic fallback without stock images
        photos_html = f"""
        <div style="grid-column: 1 / -1; background: var(--bg-surface); border: 1px dashed var(--border-carto); padding: 40px; text-align: center;">
          <h4 style="font-family: var(--font-serif); font-size: 20px; color: var(--ink-primary); margin-bottom: 8px;">Raccolta Fotografica del Territorio</h4>
          <p style="font-size: 14px; color: var(--ink-muted); max-width: 580px; margin: 0 auto 20px;">
            Le fotografie pubblicate provengono esclusivamente dal profilo Instagram ufficiale di Christian Bazzucchi, senza ricorso a immagini stock.
          </p>
          <a href="{profile.get('contacts', {}).get('instagram', 'https://www.instagram.com/christian.bazzucchi/')}" class="btn-copper" target="_blank">
            Esplora il profilo @christian.bazzucchi su Instagram &nearr;
          </a>
        </div>
        """

    # Full HTML Document
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{profile.get('name', 'Christian Bazzucchi')} — {profile.get('role', 'Geologo & Spatial Data Engineer')} | geobasi.com</title>
  <meta name="description" content="Sito professionale di {profile.get('name')}. {profile.get('bio_short')}">
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
    }}

    .carto-graticule {{
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      pointer-events: none;
      z-index: 0;
      opacity: 0.35;
      background-image: 
        linear-gradient(to right, var(--border-subtle) 1px, transparent 1px),
        linear-gradient(to bottom, var(--border-subtle) 1px, transparent 1px);
      background-size: 80px 80px;
    }}

    .wrapper {{
      position: relative;
      z-index: 1;
      max-width: 1140px;
      margin: 0 auto;
      padding: 0 24px;
    }}

    /* Top Technical Header */
    .tech-header {{
      border-bottom: 1px solid var(--border-carto);
      background: rgba(251, 249, 244, 0.95);
      backdrop-filter: blur(8px);
      position: sticky;
      top: 0;
      z-index: 50;
    }}

    .tech-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 0;
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.05em;
      color: var(--ink-muted);
      border-bottom: 1px dashed var(--border-subtle);
    }}

    .tech-bar .coords {{
      color: var(--accent-copper);
      font-weight: 500;
    }}

    .nav-main {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 18px 0;
    }}

    .brand {{
      display: flex;
      align-items: baseline;
      gap: 12px;
      text-decoration: none;
      color: var(--ink-primary);
    }}

    .brand-title {{
      font-family: var(--font-serif);
      font-size: 24px;
      font-weight: 600;
      letter-spacing: -0.02em;
    }}

    .brand-tag {{
      font-family: var(--font-mono);
      font-size: 11px;
      text-transform: uppercase;
      color: var(--ink-muted);
      border-left: 1px solid var(--border-carto);
      padding-left: 12px;
    }}

    .nav-links {{
      display: flex;
      gap: 24px;
      list-style: none;
    }}

    .nav-links a {{
      text-decoration: none;
      color: var(--ink-secondary);
      font-size: 14px;
      font-weight: 500;
      transition: color 0.15s ease;
    }}

    .nav-links a:hover {{ color: var(--accent-copper); }}

    /* Hero Section */
    .hero {{
      padding: 80px 0 60px;
      position: relative;
      overflow: hidden;
      border-bottom: 1px solid var(--border-carto);
    }}

    .hero-contour-svg {{
      position: absolute;
      right: -80px;
      top: 10px;
      width: 520px;
      height: 520px;
      opacity: 0.35;
      pointer-events: none;
    }}

    .hero-meta {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--accent-copper);
      background: var(--accent-copper-soft);
      border: 1px solid rgba(194, 89, 40, 0.2);
      padding: 4px 12px;
      border-radius: 2px;
      margin-bottom: 24px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .hero-title {{
      font-family: var(--font-serif);
      font-size: 52px;
      line-height: 1.15;
      font-weight: 600;
      color: var(--ink-primary);
      max-width: 820px;
      margin-bottom: 20px;
      letter-spacing: -0.02em;
    }}

    .hero-payoff {{
      font-family: var(--font-serif);
      font-style: italic;
      font-size: 24px;
      line-height: 1.4;
      color: var(--accent-copper);
      margin-bottom: 28px;
      max-width: 780px;
    }}

    .hero-intro {{
      font-size: 18px;
      line-height: 1.65;
      color: var(--ink-secondary);
      max-width: 720px;
      margin-bottom: 36px;
    }}

    .hero-actions {{
      display: flex;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .btn-copper {{
      background: var(--accent-copper);
      color: #FFF;
      padding: 12px 24px;
      font-size: 14px;
      font-weight: 600;
      text-decoration: none;
      border-radius: 2px;
      transition: background 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .btn-copper:hover {{ background: var(--accent-copper-hover); }}

    .btn-outline {{
      border: 1px solid var(--border-carto);
      background: #FFF;
      color: var(--ink-primary);
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 500;
      text-decoration: none;
      border-radius: 2px;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .btn-outline:hover {{
      background: var(--bg-surface);
      border-color: var(--ink-muted);
      color: var(--accent-copper);
    }}

    /* Section Styling */
    .section {{
      padding: 70px 0;
      border-bottom: 1px solid var(--border-carto);
    }}

    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 36px;
    }}

    .section-num {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--accent-copper);
      letter-spacing: 0.05em;
      margin-bottom: 6px;
      display: block;
    }}

    .section-title {{
      font-family: var(--font-serif);
      font-size: 32px;
      font-weight: 600;
      color: var(--ink-primary);
      letter-spacing: -0.01em;
    }}

    .section-subtitle {{
      font-size: 14px;
      color: var(--ink-muted);
      max-width: 500px;
    }}

    /* Approach / Identity Cards */
    .approach-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 28px;
    }}

    .approach-box {{
      background: var(--bg-surface);
      border: 1px solid var(--border-carto);
      padding: 32px;
      position: relative;
    }}

    .approach-box::before {{
      content: "";
      position: absolute;
      top: 0; left: 0; width: 4px; height: 100%;
      background: var(--accent-copper);
    }}

    .approach-box h3 {{
      font-family: var(--font-serif);
      font-size: 22px;
      margin-bottom: 14px;
      color: var(--ink-primary);
    }}

    .approach-box p {{
      font-size: 15px;
      color: var(--ink-secondary);
      line-height: 1.65;
      margin-bottom: 14px;
    }}
    .approach-box p:last-child {{ margin-bottom: 0; }}

    /* Skills Domains */
    .skills-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
    }}

    .skill-card {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-carto);
      padding: 24px;
    }}

    .skill-card h4 {{
      font-family: var(--font-serif);
      font-size: 18px;
      color: var(--ink-primary);
      margin-bottom: 8px;
    }}

    .skill-card p {{
      font-size: 13px;
      color: var(--ink-muted);
      line-height: 1.5;
      margin-bottom: 14px;
    }}

    .skill-card ul {{
      list-style: none;
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--ink-secondary);
    }}

    .skill-card ul li {{
      padding: 4px 0;
      border-bottom: 1px dashed var(--border-subtle);
    }}

    /* Project Cards Grid */
    .project-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 28px;
    }}

    .project-card {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-carto);
      padding: 28px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }}

    .project-card:hover {{
      border-color: var(--accent-copper);
    }}

    .project-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 12px;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 10px;
    }}

    .project-id {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--accent-copper);
      font-weight: 600;
    }}

    .project-context {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--ink-muted);
    }}

    .project-title {{
      font-family: var(--font-serif);
      font-size: 24px;
      font-weight: 600;
      color: var(--ink-primary);
      margin-bottom: 4px;
    }}

    .project-subtitle {{
      font-size: 13px;
      font-weight: 600;
      color: var(--accent-copper);
      margin-bottom: 14px;
    }}

    .project-desc {{
      font-size: 14px;
      color: var(--ink-secondary);
      line-height: 1.6;
      margin-bottom: 16px;
    }}

    .project-assets-preview {{
      margin: 14px 0 18px;
      display: flex;
      gap: 10px;
      overflow-x: auto;
    }}

    .project-thumb {{
      height: 70px;
      border: 1px solid var(--border-carto);
      border-radius: 2px;
      object-fit: cover;
    }}

    .project-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 20px;
    }}

    .project-tag {{
      font-family: var(--font-mono);
      font-size: 11px;
      background: var(--bg-surface);
      color: var(--ink-secondary);
      border: 1px solid var(--border-carto);
      padding: 2px 8px;
      border-radius: 2px;
    }}

    .project-actions {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: auto;
      padding-top: 14px;
      border-top: 1px solid var(--border-subtle);
    }}

    .project-link {{
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 600;
      color: var(--ink-primary);
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .project-link:hover {{ color: var(--accent-copper); }}

    /* Books / Library Shelf */
    .library-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
    }}

    .book-card {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-carto);
      padding: 16px;
      display: flex;
      flex-direction: column;
      position: relative;
    }}

    .book-card.in-progress {{
      border: 1px solid var(--accent-copper);
      background: #FFFDF9;
    }}

    .book-status-badge {{
      font-family: var(--font-mono);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 2px 6px;
      margin-bottom: 12px;
      align-self: flex-start;
      border-radius: 2px;
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
      height: 180px;
      background: var(--bg-surface);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 12px;
      border: 1px solid var(--border-subtle);
      overflow: hidden;
    }}

    .book-cover-wrap img {{
      max-height: 100%;
      max-width: 100%;
      object-fit: cover;
    }}

    .book-title {{
      font-family: var(--font-serif);
      font-size: 16px;
      font-weight: 600;
      color: var(--ink-primary);
      line-height: 1.3;
      margin-bottom: 4px;
    }}

    .book-author {{
      font-size: 13px;
      color: var(--ink-muted);
      margin-bottom: 10px;
    }}

    .book-quote {{
      font-family: var(--font-serif);
      font-style: italic;
      font-size: 12px;
      line-height: 1.45;
      color: var(--ink-secondary);
      border-left: 2px solid var(--accent-copper);
      padding-left: 8px;
      margin-top: auto;
    }}

    /* Substack Articles */
    .article-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}

    .article-card {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-carto);
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      text-decoration: none;
      color: inherit;
      transition: all 0.15s ease;
    }}
    .article-card:hover {{
      border-color: var(--accent-copper);
      transform: translateY(-2px);
    }}

    .article-meta {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--ink-muted);
      margin-bottom: 8px;
    }}

    .article-title {{
      font-family: var(--font-serif);
      font-size: 18px;
      font-weight: 600;
      line-height: 1.35;
      color: var(--ink-primary);
      margin-bottom: 10px;
    }}

    .article-excerpt {{
      font-size: 13px;
      color: var(--ink-secondary);
      line-height: 1.55;
      margin-bottom: 16px;
    }}

    .article-read-more {{
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 600;
      color: var(--accent-copper);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}

    /* Photos Section (Instagram) */
    .photo-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }}

    .photo-card {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-carto);
      text-decoration: none;
      color: inherit;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transition: all 0.15s ease;
    }}
    .photo-card:hover {{
      border-color: var(--accent-copper);
      transform: translateY(-2px);
    }}

    .photo-img-wrap {{
      width: 100%;
      height: 190px;
      overflow: hidden;
      background: var(--bg-surface);
    }}

    .photo-img-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease;
    }}
    .photo-card:hover .photo-img-wrap img {{ transform: scale(1.04); }}

    .photo-info {{
      padding: 12px;
    }}

    .photo-location {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--accent-copper);
      font-weight: 600;
      margin-bottom: 2px;
    }}

    .photo-coords {{
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--ink-muted);
      margin-bottom: 6px;
    }}

    .photo-caption {{
      font-size: 12px;
      color: var(--ink-secondary);
      line-height: 1.45;
    }}

    /* CV Section Banner */
    .cv-banner {{
      background: var(--bg-surface);
      border: 1px solid var(--border-carto);
      padding: 36px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 24px;
    }}

    .cv-banner-info h3 {{
      font-family: var(--font-serif);
      font-size: 26px;
      margin-bottom: 6px;
    }}

    .cv-banner-info p {{
      font-size: 14px;
      color: var(--ink-muted);
      max-width: 580px;
    }}

    .cv-banner-actions {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }}

    /* Footer */
    .footer {{
      padding: 60px 0 40px;
      background: var(--bg-surface);
      border-top: 2px solid var(--border-carto);
    }}

    .footer-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 40px;
      margin-bottom: 40px;
    }}

    .footer-title {{
      font-family: var(--font-serif);
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 12px;
    }}

    .footer-desc {{
      font-size: 14px;
      color: var(--ink-secondary);
      line-height: 1.6;
      max-width: 440px;
    }}

    .footer-col h4 {{
      font-family: var(--font-mono);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--ink-muted);
      margin-bottom: 14px;
    }}

    .footer-col ul {{ list-style: none; }}
    .footer-col ul li {{ margin-bottom: 8px; }}
    .footer-col ul a {{
      text-decoration: none;
      color: var(--ink-secondary);
      font-size: 14px;
      transition: color 0.15s ease;
    }}
    .footer-col ul a:hover {{ color: var(--accent-copper); }}

    .footer-bottom {{
      border-top: 1px solid var(--border-carto);
      padding-top: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--ink-muted);
      flex-wrap: wrap;
      gap: 10px;
    }}

    @media (max-width: 900px) {{
      .hero-title {{ font-size: 38px; }}
      .hero-payoff {{ font-size: 20px; }}
      .approach-grid, .project-grid, .library-grid, .article-grid, .photo-grid, .skills-grid, .footer-grid {{
        grid-template-columns: 1fr;
      }}
      .cv-banner {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>

  <div class="carto-graticule"></div>

  <!-- Technical Header -->
  <header class="tech-header">
    <div class="wrapper">
      <div class="tech-bar">
        <span>PROIEZIONE: WGS84 / EPSG:4326</span>
        <span class="coords">{profile.get('coordinates', '43°43\'02" N • 10°56\'51" E')} &bull; QUOTA: 48m s.l.m.</span>
        <span>ORIGINE: {profile.get('location', 'EMPOLI (FI), TOSCANA').upper()}</span>
      </div>
      <nav class="nav-main">
        <a href="#home" class="brand">
          <span class="brand-title">{profile.get('name', 'Christian Bazzucchi')}</span>
          <span class="brand-tag">{profile.get('role', 'Geologo • Spatial Data Engineer')}</span>
        </a>
        <ul class="nav-links">
          <li><a href="#profilo">Profilo</a></li>
          <li><a href="#competenze">Competenze</a></li>
          <li><a href="#progetti">Progetti</a></li>
          <li><a href="#biblioteca">Biblioteca</a></li>
          <li><a href="#fotografie">Fotografie</a></li>
          <li><a href="#appunti">Appunti</a></li>
          <li><a href="#cv">Curriculum</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="hero" id="home">
    <div class="wrapper" style="position: relative;">
      <svg class="hero-contour-svg" viewBox="0 0 500 500" fill="none" stroke="#C25928" stroke-width="1.2">
        <path d="M 50,250 C 70,180 140,120 250,110 C 360,100 430,160 450,250 C 470,340 380,420 260,430 C 140,440 30,320 50,250 Z" />
        <path d="M 90,250 C 110,195 160,150 250,140 C 340,130 395,180 410,250 C 425,320 350,380 260,390 C 170,400 70,305 90,250 Z" stroke-dasharray="6 3" />
        <path d="M 130,250 C 150,210 185,180 250,170 C 315,160 360,200 370,250 C 380,300 320,340 260,350 C 200,360 110,290 130,250 Z" />
        <path d="M 170,250 C 185,225 210,205 250,200 C 290,195 325,220 330,250 C 335,280 290,305 250,310 C 210,315 155,275 170,250 Z" stroke-width="1.8" />
        <path d="M 210,250 C 220,235 235,225 250,225 C 265,225 285,235 290,250 C 295,265 270,275 250,275 C 230,275 200,265 210,250 Z" />
        <circle cx="250" cy="250" r="3" fill="#C25928" />
        <text x="258" y="248" font-family="'Fira Code', monospace" font-size="10" fill="#C25928">Quota 488m</text>
      </svg>

      <div class="hero-meta">
        <span>Rilievo Tecnico &bull; Geospatial Data Architecture</span>
      </div>

      <h1 class="hero-title">{profile.get('name', 'Christian Bazzucchi')}</h1>
      
      <p class="hero-payoff">
        "{profile.get('payoff', 'Il territorio è fatto di dati. Il valore sta nel saperli connettere.')}"
      </p>

      <p class="hero-intro">
        {profile.get('bio_short')}
      </p>

      <div class="hero-actions">
        <a href="#progetti" class="btn-copper">
          Esplora i Casi di Studio
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </a>
        <a href="cv-it.html" class="btn-outline">Curriculum Vitae (Web & PDF)</a>
        <a href="{profile.get('contacts', {}).get('substack', 'https://geobuzz.substack.com/')}" class="btn-outline" target="_blank">Blog su Substack &nearr;</a>
      </div>
    </div>
  </section>

  <!-- Approach Section -->
  <section class="section" id="profilo">
    <div class="wrapper">
      <div class="section-header">
        <div>
          <span class="section-num">SEZIONE 01 &bull; IDENTITÀ & METODO</span>
          <h2 class="section-title">L'Approccio ai Dati Territoriali</h2>
        </div>
        <p class="section-subtitle">
          Progettazione architetturale a partire dai problemi, integrando tecnologie mature open source e automatizzando ciò che serve.
        </p>
      </div>

      <div class="approach-grid">
        <div class="approach-box">
          <h3>Dalla Complessità Geologica all'Ingegneria del Dato</h3>
          <p>
            Non mi limito a utilizzare software GIS commerciali o a sviluppare script isolati: il mio percorso parte dalla comprensione fisica e strutturale dei fenomeni geologici e ambientali, per tradurla in modelli di dati coerenti, robusti e normalizzati.
          </p>
          <p>
            Dalla caratterizzazione idrogeologica alla viticoltura di precisione, ogni rilievo strumentale e ogni raster multispettrale acquista significato decisionale solo quando è integrato in flussi topologici controllati e privi di ridondanza.
          </p>
        </div>

        <div class="approach-box">
          <h3>Ecosistema Maturo, Standard OGC e Automazione</h3>
          <p>
            Privilegio l'ecosistema open source consolidato (PostgreSQL/PostGIS, QGIS, GeoServer, GDAL/OGR) combinato con librerie di automazione Python (GeoPandas, Shapely) e SQL avanzato, integrandoli all'occorrenza con suite proprietarie enterprise quando il contesto operativo lo richiede.
          </p>
          <p>
            La gestione di progetti complessi e il coordinamento di gruppi di lavoro tecnici mi hanno insegnato che l'efficienza non risiede nella complessità fine a se stessa, ma nella capacità di collegare sistemi eterogenei senza attriti.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Skills Matrix Section -->
  <section class="section" id="competenze">
    <div class="wrapper">
      <div class="section-header">
        <div>
          <span class="section-num">SEZIONE 02 &bull; QUADRO DELLE COMPETENZE</span>
          <h2 class="section-title">Domini e Tecnologie</h2>
        </div>
        <p class="section-subtitle">
          Competenze verticali maturate sul campo tra grandi reti infrastrutturali, ambiente e innovazione digitale.
        </p>
      </div>

      <div class="skills-grid">
        {skills_html}
      </div>
    </div>
  </section>

  <!-- Projects Section -->
  <section class="section" id="progetti">
    <div class="wrapper">
      <div class="section-header">
        <div>
          <span class="section-num">SEZIONE 03 &bull; QUADRO D'UNIONE</span>
          <h2 class="section-title">Casi di Studio e Progetti</h2>
        </div>
        <p class="section-subtitle">
          Problemi affrontati, architetture geospaziali adottate, risultati documentati e materiali storici conservati.
        </p>
      </div>

      <div class="project-grid">
        {projects_html}
      </div>
    </div>
  </section>

  <!-- Library Section (Anobii) -->
  <section class="section" id="biblioteca">
    <div class="wrapper">
      <div class="section-header">
        <div>
          <span class="section-num">SEZIONE 04 &bull; BIBLIOTECA PERSONALE</span>
          <h2 class="section-title">La Mia Biblioteca</h2>
        </div>
        <div>
          <a href="{profile.get('contacts', {}).get('anobii', 'https://www.anobii.com/it/01d6d75099d9c1d4bb/profile')}" class="btn-outline" target="_blank" style="font-family: var(--font-mono); font-size: 12px;">
            Profilo completo su Anobii &nearr;
          </a>
        </div>
      </div>

      <div class="library-grid">
        {books_html}
      </div>
    </div>
  </section>

  <!-- Photo Gallery Section (Instagram) -->
  <section class="section" id="fotografie">
    <div class="wrapper">
      <div class="section-header">
        <div>
          <span class="section-num">SEZIONE 05 &bull; OSSERVAZIONE DEL TERRITORIO</span>
          <h2 class="section-title">Fotografie & Paesaggi</h2>
        </div>
        <div>
          <a href="{profile.get('contacts', {}).get('instagram', 'https://www.instagram.com/christian.bazzucchi/')}" class="btn-outline" target="_blank" style="font-family: var(--font-mono); font-size: 12px;">
            Galleria su Instagram &nearr;
          </a>
        </div>
      </div>

      <div class="photo-grid">
        {photos_html}
      </div>
    </div>
  </section>

  <!-- Substack Articles Section -->
  <section class="section" id="appunti">
    <div class="wrapper">
      <div class="section-header">
        <div>
          <span class="section-num">SEZIONE 06 &bull; NOTE EDITORIALI</span>
          <h2 class="section-title">Appunti da Substack</h2>
        </div>
        <div>
          <a href="{profile.get('contacts', {}).get('substack', 'https://geobuzz.substack.com/')}" class="btn-outline" target="_blank" style="font-family: var(--font-mono); font-size: 12px;">
            Iscriviti su geobuzz.substack.com &nearr;
          </a>
        </div>
      </div>

      <div class="article-grid">
        {articles_html}
      </div>
    </div>
  </section>

  <!-- CV Section Banner -->
  <section class="section" id="cv">
    <div class="wrapper">
      <div class="cv-banner">
        <div class="cv-banner-info">
          <span class="section-num">SEZIONE 07 &bull; PERCORSO PROFESSIONALE</span>
          <h3>Curriculum Vitae Ufficiale</h3>
          <p>
            Oltre 18 anni di esperienza professionale documentata tra geologia applicata, ingegneria dei dati territoriali, grandi infrastrutture di rete e sviluppo software.
          </p>
        </div>
        <div class="cv-banner-actions">
          <a href="cv-it.html" class="btn-copper">Visualizza CV Italiano</a>
          <a href="cv-en.html" class="btn-outline">English Resume</a>
          <a href="archive/documents/cv_italiano_originale.pdf" class="btn-outline" target="_blank">PDF Storico &darr;</a>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <div class="wrapper">
      <div class="footer-grid">
        <div>
          <h3 class="footer-title">{profile.get('name', 'Christian Bazzucchi')}</h3>
          <p class="footer-desc">
            {profile.get('role', 'Geologo • Spatial Data Engineer')}. {profile.get('location', 'Empoli (FI), Toscana, Italia')}.<br>
            Progettazione di sistemi informativi geografici, gestione basi dati spaziali e automazione dei processi territoriali.
          </p>
        </div>
        <div class="footer-col">
          <h4>Canali</h4>
          <ul>
            <li><a href="{profile.get('contacts', {}).get('linkedin', 'https://www.linkedin.com/in/christianbazzucchi/')}" target="_blank">LinkedIn &nearr;</a></li>
            <li><a href="{profile.get('contacts', {}).get('github', 'https://github.com/geobuzz')}" target="_blank">GitHub (@geobuzz) &nearr;</a></li>
            <li><a href="{profile.get('contacts', {}).get('substack', 'https://geobuzz.substack.com/')}" target="_blank">Substack Blog &nearr;</a></li>
            <li><a href="{profile.get('contacts', {}).get('instagram', 'https://www.instagram.com/christian.bazzucchi/')}" target="_blank">Instagram (@christian.bazzucchi) &nearr;</a></li>
            <li><a href="{profile.get('contacts', {}).get('anobii', 'https://www.anobii.com/it/01d6d75099d9c1d4bb/profile')}" target="_blank">Anobii Biblioteca &nearr;</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Contatto Diretto</h4>
          <ul>
            <li><a href="mailto:{profile.get('contacts', {}).get('email', 'christian@geobasi.com')}">{profile.get('contacts', {}).get('email', 'christian@geobasi.com')}</a></li>
            <li><span style="font-family: var(--font-mono); font-size: 13px; color: var(--ink-muted);">PGP &bull; WGS84</span></li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom">
        <span>&copy; 2026 {profile.get('name', 'Christian Bazzucchi')} &bull; geobasi.com</span>
        <span>Ultima sincronizzazione dati: {last_sync_text} &bull; GitHub Pages</span>
      </div>
    </div>
  </footer>

</body>
</html>
"""

    with open(OUTPUT_INDEX, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Compilato con successo {OUTPUT_INDEX} dai file JSON.")

    # Re-render CV pages
    try:
        from build_cv_pages import render_cv
        render_cv("it")
        render_cv("en")
        print("Pagine cv-it.html e cv-en.html ricompilate.")
    except Exception as e:
        print(f"Errore render CV: {e}")

if __name__ == "__main__":
    build()
