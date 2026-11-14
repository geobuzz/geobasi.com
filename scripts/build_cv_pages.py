#!/usr/bin/env python3
"""
Compila site/data/cv_it.json e site/data/cv_en.json nelle pagine statiche consultabili e stampabili in PDF:
- site/cv-it.html
- site/cv-en.html
Include stili CSS dedicati per la visualizzazione a schermo e per la stampa/esportazione PDF.
"""
import json
import os

SITE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(SITE_DIR, "data")

def render_cv(lang="it"):
    json_path = os.path.join(DATA_DIR, f"cv_{lang}.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    is_it = (lang == "it")
    lang_switch = "cv-en.html" if is_it else "cv-it.html"
    lang_switch_label = "Switch to English Resume" if is_it else "Passa al CV in Italiano"
    print_label = "Stampa / Salva in PDF" if is_it else "Print / Save as PDF"
    back_label = "Torna a Geobasi.com" if is_it else "Back to Geobasi.com"
    skills_title = "Competenze Tecniche" if is_it else "Technical Skills"
    exp_title = "Esperienze Professionali" if is_it else "Professional Experience"
    edu_title = "Formazione & Perfezionamento" if is_it else "Education & Specializations"

    skills_html = ""
    for category, tools in data.get("skills", {}).items():
        tools_str = ", ".join(tools)
        skills_html += f"""
        <div class="cv-skill-group">
          <span class="cv-skill-name">{category}:</span>
          <span class="cv-skill-tools">{tools_str}</span>
        </div>
        """

    exp_html = ""
    for exp in data.get("experiences", []):
        hl_html = "".join([f"<li>{h}</li>" for h in exp.get("highlights", [])])
        hl_block = f'<ul class="cv-highlights">{hl_html}</ul>' if hl_html else ""
        exp_html += f"""
        <div class="cv-entry">
          <div class="cv-entry-header">
            <div>
              <h3 class="cv-entry-role">{exp.get('role')}</h3>
              <div class="cv-entry-company">{exp.get('company')} &bull; {exp.get('location')}</div>
            </div>
            <div class="cv-entry-period">{exp.get('period')}</div>
          </div>
          <p class="cv-entry-desc">{exp.get('description')}</p>
          {hl_block}
        </div>
        """

    edu_html = ""
    for edu in data.get("education", []):
        edu_html += f"""
        <div class="cv-entry">
          <div class="cv-entry-header">
            <div>
              <h3 class="cv-entry-role">{edu.get('degree')}</h3>
              <div class="cv-entry-company">{edu.get('institution')}</div>
            </div>
          </div>
          <p class="cv-entry-desc">{edu.get('details')}</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('name')} — Curriculum Vitae ({lang.upper()})</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #FBF9F4;
      --card-bg: #FFFFFF;
      --ink: #12222E;
      --ink-muted: #5A6D7C;
      --copper: #C25928;
      --border: #DDD5C7;
      --border-subtle: #EBE4D8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--ink);
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      line-height: 1.55;
      font-size: 14px;
      padding: 30px 16px;
    }}
    .cv-container {{
      max-width: 860px;
      margin: 0 auto;
      background: var(--card-bg);
      border: 1px solid var(--border);
      padding: 48px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.03);
      position: relative;
    }}
    .no-print-bar {{
      max-width: 860px;
      margin: 0 auto 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
    }}
    .no-print-bar a {{
      color: var(--ink);
      text-decoration: none;
      border: 1px solid var(--border);
      padding: 6px 12px;
      background: #FFF;
      border-radius: 2px;
    }}
    .no-print-bar a:hover {{
      border-color: var(--copper);
      color: var(--copper);
    }}
    .cv-header {{
      border-bottom: 2px solid var(--copper);
      padding-bottom: 24px;
      margin-bottom: 28px;
    }}
    .cv-name {{
      font-family: 'Newsreader', serif;
      font-size: 34px;
      font-weight: 600;
      color: var(--ink);
      margin-bottom: 4px;
    }}
    .cv-title {{
      font-family: 'Fira Code', monospace;
      font-size: 13px;
      color: var(--copper);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 14px;
    }}
    .cv-meta {{
      font-family: 'Fira Code', monospace;
      font-size: 11px;
      color: var(--ink-muted);
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .cv-meta a {{ color: inherit; text-decoration: none; }}
    .cv-section {{
      margin-bottom: 28px;
    }}
    .cv-section-title {{
      font-family: 'Newsreader', serif;
      font-size: 20px;
      font-weight: 600;
      color: var(--ink);
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 6px;
      margin-bottom: 16px;
    }}
    .cv-summary {{
      font-size: 14px;
      color: var(--ink-muted);
      line-height: 1.65;
    }}
    .cv-skill-group {{
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .cv-skill-name {{
      font-weight: 600;
      color: var(--ink);
      display: inline-block;
      min-width: 180px;
    }}
    .cv-skill-tools {{
      color: var(--ink-muted);
    }}
    .cv-entry {{
      margin-bottom: 20px;
    }}
    .cv-entry-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 4px;
    }}
    .cv-entry-role {{
      font-size: 15px;
      font-weight: 600;
      color: var(--ink);
    }}
    .cv-entry-company {{
      font-size: 13px;
      color: var(--copper);
      font-weight: 500;
    }}
    .cv-entry-period {{
      font-family: 'Fira Code', monospace;
      font-size: 11px;
      color: var(--ink-muted);
    }}
    .cv-entry-desc {{
      font-size: 13px;
      color: var(--ink-muted);
      line-height: 1.55;
      margin-bottom: 6px;
    }}
    .cv-highlights {{
      padding-left: 20px;
      font-size: 12px;
      color: var(--ink-muted);
    }}
    .cv-highlights li {{ margin-bottom: 3px; }}

    @media print {{
      body {{ background: #FFF; padding: 0; font-size: 12px; }}
      .no-print-bar {{ display: none; }}
      .cv-container {{ border: none; box-shadow: none; padding: 0; }}
      .cv-entry {{ page-break-inside: avoid; }}
      a {{ text-decoration: none; color: inherit; }}
    }}
  </style>
</head>
<body>

  <div class="no-print-bar">
    <a href="index.html">&larr; {back_label}</a>
    <div style="display: flex; gap: 10px;">
      <a href="{lang_switch}">{lang_switch_label}</a>
      <a href="javascript:window.print()">&darr; {print_label}</a>
    </div>
  </div>

  <div class="cv-container">
    <header class="cv-header">
      <h1 class="cv-name">{data.get('name')}</h1>
      <div class="cv-title">{data.get('title')}</div>
      <div class="cv-meta">
        <span>{data.get('location')}</span>
        <span>&bull;</span>
        <a href="mailto:{data.get('email')}">{data.get('email')}</a>
        <span>&bull;</span>
        <a href="{data.get('linkedin')}" target="_blank">LinkedIn</a>
        <span>&bull;</span>
        <a href="{data.get('github')}" target="_blank">GitHub: @geobuzz</a>
        <span>&bull;</span>
        <span>geobasi.com</span>
      </div>
    </header>

    <section class="cv-section">
      <p class="cv-summary">{data.get('summary')}</p>
    </section>

    <section class="cv-section">
      <h2 class="cv-section-title">{skills_title}</h2>
      {skills_html}
    </section>

    <section class="cv-section">
      <h2 class="cv-section-title">{exp_title}</h2>
      {exp_html}
    </section>

    <section class="cv-section">
      <h2 class="cv-section-title">{edu_title}</h2>
      {edu_html}
    </section>
  </div>

</body>
</html>
"""
    out_file = os.path.join(SITE_DIR, f"cv-{lang}.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generato {out_file}")

if __name__ == "__main__":
    render_cv("it")
    render_cv("en")
