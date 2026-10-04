#!/usr/bin/env python3
"""
Applies the NXB red/black theme to a RUNNING CTFd by writing theme/ctfd-theme.css
into CTFd's "Theme Header" setting via the admin API. It does not create or touch
challenges, flags, hints or scores, so it is safe to re-run any time.

Existing Theme Header content is PRESERVED: the theme lives between
<!-- NXB-THEME-START --> and <!-- NXB-THEME-END --> markers, and only that block is
replaced on re-runs. The previous header is saved to theme_header_backup.html first.

Usage:
    python3 ctfd-setup/apply_theme.py --url http://192.168.56.10:8000 --token <ADMIN_TOKEN>

Manual alternative: Admin Panel -> Config -> Theme -> Theme Header, paste
    <style> ...contents of theme/ctfd-theme.css... </style>
"""
import argparse
import os
import sys

import requests

CSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "theme", "ctfd-theme.css")

p = argparse.ArgumentParser()
p.add_argument("--url", required=True)
p.add_argument("--token", required=True)
a = p.parse_args()

import re

START, END = "<!-- NXB-THEME-START -->", "<!-- NXB-THEME-END -->"
with open(CSS) as f:
    block = f"{START}\n<style>\n{f.read()}\n</style>\n{END}"

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

pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
new = pattern.sub(lambda _m: block, current) if pattern.search(current) else (current + "\n" + block).strip()

r = requests.patch(api, json={"theme_header": new}, headers=hdr, timeout=15)
if r.status_code != 200 or not r.json().get("success"):
    sys.exit(f"[!] Failed ({r.status_code}): {r.text[:300]}")
print("[+] Theme applied (existing header content kept). Hard-refresh CTFd (Ctrl+Shift+R).")
