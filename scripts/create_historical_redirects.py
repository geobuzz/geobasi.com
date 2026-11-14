#!/usr/bin/env python3
"""
Crea le pagine statiche di redirect e preservazione per tutti gli URL storici di geobasi.com:
- /lavori/agrinex/index.html -> /#agrinex
- /lavori/brunello_app/index.html -> /#brunello
- /lavori/environ/index.html -> /#environ
- /lavori/index.html -> /#progetti
- /CVga/index.html -> /cv-it.html
- /CVga/CV_En/index.html -> /cv-en.html
- /libri/index.html -> /#biblioteca
- /blog/index.html -> /#appunti
- /home/index.html -> /
"""
import os

SITE_DIR = os.path.join(os.path.dirname(__file__), "..")

REDIRECTS = {
    "lavori/agrinex": ("/#agrinex", "Agrinex — WebGIS per la Viticoltura di Precisione"),
    "lavori/brunello_app": ("/#brunello", "Brunello App — Cartografia e Geodati"),
    "lavori/environ": ("/#environ", "Environ — WebGIS Monitoraggio Ambientale"),
    "lavori": ("/#progetti", "Progetti e Casi di Studio"),
    "CVga": ("/cv-it.html", "Curriculum Vitae — Christian Bazzucchi"),
    "CVga/CV_En": ("/cv-en.html", "Curriculum Vitae (English) — Christian Bazzucchi"),
    "libri": ("/#biblioteca", "La Mia Biblioteca"),
    "blog": ("/#appunti", "Appunti & Substack"),
    "home": ("/", "Geobasi.com — Christian Bazzucchi")
}

for path, (target, title) in REDIRECTS.items():
    folder = os.path.join(SITE_DIR, path)
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, "index.html")
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url={target}">
  <link rel="canonical" href="https://geobasi.com{target}">
  <title>Reindirizzamento: {title}</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      background: #FBF9F4;
      color: #12222E;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
      text-align: center;
    }}
    a {{ color: #C25928; font-weight: 600; text-decoration: none; }}
  </style>
</head>
<body>
  <div>
    <p>Reindirizzamento a <strong>{title}</strong> in corso...</p>
    <p><a href="{target}">Clicca qui se non vieni reindirizzato automaticamente</a></p>
  </div>
</body>
</html>
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Creato redirect storico: {path}/index.html -> {target}")

