#!/usr/bin/env python3
"""
Applies the NXB red/black theme to a RUNNING CTFd by writing theme/ctfd-theme.css
into CTFd's "Theme Header" setting via the admin API, plus the red code-rain
effect (theme/nxb-fx.js, same as the broker board). It does not create or touch
challenges, flags, hints or scores, so it is safe to re-run any time.

Existing Theme Header content is PRESERVED: the theme lives between
<!-- NXB-THEME-START --> and <!-- NXB-THEME-END --> markers, the rain script
between <!-- NXB-RAIN-START --> and <!-- NXB-RAIN-END --> markers, and only
those blocks are replaced on re-runs. The previous header is saved to
theme_header_backup.html first.

Usage:
    python3 ctfd-setup/apply_theme.py --url http://192.168.56.10:8000 --token <ADMIN_TOKEN>
"""
import argparse
import os
import re
import sys

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, "theme", "ctfd-theme.css")
RAIN_JS = os.path.join(BASE, "theme", "nxb-fx.js")

p = argparse.ArgumentParser()
p.add_argument("--url", required=True)
p.add_argument("--token", required=True)
a = p.parse_args()

START, END = "<!-- NXB-THEME-START -->", "<!-- NXB-THEME-END -->"
with open(CSS) as f:
    theme_block = f"{START}\n<style>\n{f.read()}\n</style>\n{END}"

RSTART, REND = "<!-- NXB-RAIN-START -->", "<!-- NXB-RAIN-END -->"
with open(RAIN_JS) as f:
    rain_src = f.read()
if "</script" in rain_src.lower():
    sys.exit("[!] nxb-fx.js contains a closing script tag; refusing to inline.")
rain_block = (
    f"{RSTART}\n<script>\n"
    "document.addEventListener('DOMContentLoaded',function(){\n"
    "if(!document.getElementById('rain')){"
    "var c=document.createElement('canvas');c.id='rain';"
    "document.body.insertBefore(c,document.body.firstChild);}\n"
    + rain_src +
    "\n});\n</script>\n" + REND
)

def upsert(text, start, end, block):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(lambda _m: block, text)
    return (text + "\n" + block).strip()


api = a.url.rstrip("/") + "/api/v1/configs"
hdr = {"Authorization": f"Token {a.token}", "Content-Type": "application/json"}

r = requests.get(api, headers=hdr, timeout=15)
if r.status_code != 200:
    sys.exit(f"[!] Could not read current settings ({r.status_code}): {r.text[:200]}")
current = next((c.get("value") or "" for c in r.json()["data"] if c["key"] == "theme_header"), "")
if current:
    with open("theme_header_backup.html", "w") as f:
        f.write(current)
    print("[=] Existing Theme Header backed up to theme_header_backup.html")

new = upsert(current, START, END, theme_block)
new = upsert(new, RSTART, REND, rain_block)

r = requests.patch(api, json={"theme_header": new}, headers=hdr, timeout=15)
if r.status_code != 200 or not r.json().get("success"):
    sys.exit(f"[!] Failed ({r.status_code}): {r.text[:300]}")
print("[+] Theme + code-rain applied (existing header content kept). Hard-refresh CTFd (Ctrl+Shift+R).")
