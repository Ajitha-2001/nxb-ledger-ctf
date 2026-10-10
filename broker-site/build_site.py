#!/usr/bin/env python3
"""
Builds the static broker-site HTML (index, ads, profile pages) from
evidence-generation/output/stage1/broker_ads_source.json, using the shared
red/black theme in ../theme/.

Run AFTER generate_evidence.py:
    python3 broker-site/build_site.py
Then:  docker compose up -d --build broker-site

Edit THIS file for layout/copy changes (files in html/ are regenerated).
Edit ../theme/nxb-theme.css for colours/styling, then re-run this script.
"""
import json
import os
import shutil
from html import escape

BASE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(BASE, "..", "evidence-generation", "output", "stage1", "broker_ads_source.json")
THEME_DIR = os.path.join(BASE, "..", "theme")
HTML_DIR = os.path.join(BASE, "html")
ADS_DIR = os.path.join(HTML_DIR, "ads")
PROFILES_DIR = os.path.join(HTML_DIR, "profiles")
ASSETS_DIR = os.path.join(HTML_DIR, "assets")

for d in (ADS_DIR, PROFILES_DIR, ASSETS_DIR):
    os.makedirs(d, exist_ok=True)
for f in ("nxb-theme.css", "nxb-fx.js"):
    shutil.copy(os.path.join(THEME_DIR, f), os.path.join(ASSETS_DIR, f))

with open(EVIDENCE) as f:
    ads = json.load(f)


def cap(s):
    return s[0].upper() + s[1:]


def page(title, body, depth=0):
    """Wrap body in the themed shell. depth=0 for html/, 1 for html/ads|profiles/."""
    root = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | Loan Broker Classifieds (training)</title>
<link rel="stylesheet" href="{root}assets/nxb-theme.css">
</head>
<body>
<canvas id="rain" aria-hidden="true"></canvas>
<div class="wrap">
<header class="topbar">
  <a class="brand" href="{root}index.html"><b>BROKER</b>.BOARD</a>
  <nav class="nav"><a href="{root}index.html">Posts</a><a href="{root}profiles/index.html">Brokers</a>
  <span class="pill">TRAINING SIMULATION</span></nav>
</header>
<main>
{body}
</main>
<footer>NXB Ledger CTF &mdash; synthetic training content only. Nothing on this board is real.</footer>
</div>
<script src="{root}assets/nxb-fx.js"></script>
</body></html>
"""


def write(path, html):
    with open(path, "w") as f:
        f.write(html)


# unique broker codes, in first-seen order
codes = []
for ad in ads:
    if ad["contact_code"] not in codes:
        codes.append(ad["contact_code"])

# ---------------- Index ----------------
cards = "".join(
    f"""<a class="card" href="ads/{ad['post_id']}.html">
  <div class="id">{ad['post_id']}</div>
  <div class="meta">General Loan Assistance Board</div>
  <p>{escape(cap(ad['phrase']))}&hellip;</p>
  <span class="btn">Open post</span>
</a>
"""
    for ad in ads
)
write(os.path.join(HTML_DIR, "index.html"), page("Public posts", f"""
<section class="hero">
  <h1 class="glitch" data-text="BROKER BOARD">BROKER BOARD</h1>
  <p class="typed" data-type="indexing public loan-broker posts for the NXB investigation..."></p>
  <div class="stats">
    <div class="stat"><b>{len(ads)}</b><span>public posts</span></div>
    <div class="stat"><b>{len(codes)}</b><span>broker profiles</span></div>
    <div class="stat"><b>0</b><span>real people</span></div>
  </div>
</section>
<p class="lead">A synthetic, locally hosted classifieds board for an OSINT training exercise.
All posts, brokers and contact codes are fictional. Compare the posts against the leaked screenshot you were given.</p>
<h2>Recent public posts</h2>
<div class="grid">{cards}</div>
"""))

# ---------------- Ad pages ----------------
for ad in ads:
    write(os.path.join(ADS_DIR, f"{ad['post_id']}.html"), page(ad["post_id"], f"""
<p class="crumbs"><a href="../index.html">posts</a> / {ad['post_id']}</p>
<div class="card">
  <div class="id">POST {ad['post_id']}</div>
  <div class="meta">General Loan Assistance Board</div>
  <span class="tag">Loan Assistance</span><span class="tag">Fast Processing</span>
  <div class="quote">&ldquo;Need your loan file expedited? Our team can help move things along quickly.
  {escape(cap(ad['phrase']))}. Serious inquiries only.&rdquo;</div>
  <dl class="kv"><dt>Contact code</dt><dd><span class="code">{ad['contact_code']}</span></dd></dl>
  <a class="btn" href="../profiles/{ad['contact_code']}.html">View broker profile</a>
</div>
""", 1))

# ---------------- Profiles ----------------
pcards = "".join(
    f"""<a class="card" href="{c}.html">
  <div class="id">{c}</div>
  <div class="meta">{sum(1 for a in ads if a['contact_code'] == c)} active post(s)</div>
  <span class="btn">Open profile</span>
</a>
"""
    for c in codes
)
write(os.path.join(PROFILES_DIR, "index.html"), page("Broker profiles", f"""
<p class="crumbs"><a href="../index.html">posts</a> / brokers</p>
<h2>Broker profiles</h2>
<div class="grid">{pcards}</div>
""", 1))

for code in codes:
    posts = [a["post_id"] for a in ads if a["contact_code"] == code]
    links = ", ".join(f'<a href="../ads/{p}.html">{p}</a>' for p in posts)
    write(os.path.join(PROFILES_DIR, f"{code}.html"), page(code, f"""
<p class="crumbs"><a href="../index.html">posts</a> / <a href="index.html">brokers</a> / {code}</p>
<div class="card">
  <div class="id">BROKER {code}</div>
  <div class="meta">Profile (training simulation)</div>
  <dl class="kv">
    <dt>Member since</dt><dd>synthetic training data</dd>
    <dt>Active posts</dt><dd>{links}</dd>
    <dt>Rating</dt><dd>N/A (training simulation)</dd>
  </dl>
</div>
""", 1))

print(f"[+] Broker site built: {len(ads)} ads, {len(codes)} broker profiles -> {HTML_DIR}")
