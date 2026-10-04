#!/usr/bin/env python3
"""
NXB Ledger - CTFd Challenge Importer
======================================
Creates all six stages in a running CTFd instance via the admin REST API:
  - challenge metadata (name, category, description, value)
  - flags (static, case-sensitive)
  - file attachments (evidence bundles)
  - hints (with cost)
  - prerequisites, so Stage N+1 is hidden until Stage N is solved

Usage:
    1. Complete the CTFd setup wizard in the browser (http://<HOST_IP>:8000)
       and create an admin account.
    2. Generate an API token: Admin Panel -> Settings -> Access Tokens.
    3. Run:
         python3 import_challenges.py --url http://192.168.56.10:8000 --token <TOKEN>

Safe to re-run. Challenges are matched by name:
  - missing ones are created (flag, hints, files, prerequisites);
  - existing ones are NOT duplicated (add --replace-files to swap changed evidence
    attachments); instead they are synced: state set to
    "visible", flag re-synced to flags.json, hint costs corrected, and
    prerequisites (re)applied.
Hint cost in CHALLENGES below is a PERCENT of the stage value (design report 4.4:
hint 1 = 10 %, hint 2 = 20 %), converted to points at import time.
Stages 2-6 are "visible" but locked behind prerequisites (anonymized), which is how
CTFd implements "hidden until the earlier stage is solved". A "hidden" state would
make them invisible to everyone, including after the prerequisite is solved.
"""
import argparse
import json
import os
import sys

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(BASE, "evidence-generation", "output")
FLAGS_PATH = os.path.join(EVIDENCE_DIR, "secrets", "flags.json")


def load_flags():
    with open(FLAGS_PATH) as f:
        return json.load(f)


CHALLENGES = [
    {
        "key": "stage1",
        "name": "Stage 1 - The Broker's Promise",
        "category": "OSINT",
        "value": 100,
        "description": (
            "A private loan-application post has leaked into a broker group. You are given "
            "the leaked post and access to a locally hosted broker classifieds site "
            "(http://192.168.56.10:8081). Correlate the leaked post's wording against the "
            "public advertisements to identify the matching post ID and broker contact code.\n\n"
            "Submit your answer at http://192.168.56.10:8082/check/stage1 as JSON:\n"
            '{"post_id": "...", "contact_code": "...", "feature1": "...", "feature2": "..."}\n\n'
            "feature1/feature2 should briefly name the two distinctive features that justify your match."
        ),
        "attachments": ["stage1/leaked_post.png"],
        "hints": [
            ("Compare contact identifiers as well as advertisement wording, not just the fee phrase alone.", 10),
            ("Check the public post index for a reference ending in 17.", 20),
        ],
    },
    {
        "key": "stage2",
        "name": "Stage 2 - The Hidden Conversation",
        "category": "Encoding / Scripting",
        "value": 100,
        "description": (
            "A fragment of a shared-drive chat export is attached. The message body has been "
            "encoded as part of the export format. Verify the SHA-256 hash, identify the "
            "encoding method, and decode the message. Base64 is an encoding, not encryption - "
            "no secret key is required.\n\n"
            "The decoded message contains the Stage 2 flag directly - submit it below as usual."
        ),
        "attachments": ["stage2/chat_fragment.json", "stage2/manifest_sha256.txt"],
        "hints": [
            ("Read the export_note field in the JSON - it names the encoding method.", 10),
            ("Try Python's base64.b64decode() on the body field, then decode the bytes as UTF-8.", 20),
        ],
    },
    {
        "key": "stage3",
        "name": "Stage 3 - Beyond the Branch",
        "category": "Web Security",
        "value": 200,
        "description": (
            "The NXB loan portal is running at http://192.168.56.10:8080. Log in with the "
            "supplied BR03 test account (username: br03_officer / password: Training#2026) and "
            "use the application reference recovered in Stage 2 to request "
            "/application/<reference>. Document the route, the owning branch and the missing "
            "authorization check.\n\n"
            "The flag is displayed directly on the application page once the cross-branch "
            "request succeeds."
        ),
        "attachments": [],
        "hints": [
            ("Compare the branch on your own account with the branch that owns the application you're requesting.", 10),
            ("Use the application reference you decoded in Stage 2 directly in the /application/<id> route.", 20),
        ],
    },
    {
        "key": "stage4",
        "name": "Stage 4 - The Workstation Trace",
        "category": "Digital Forensics",
        "value": 200,
        "description": (
            "The original leaked screenshot is attached again at full resolution, together with "
            "the asset register and capture-event log. Verify the file hash, zoom into the "
            "watermark, and correlate it with the asset register and the capture event tied to "
            "the application from Stage 2/3.\n\n"
            "Submit your answer at http://192.168.56.10:8082/check/stage4 as JSON:\n"
            '{"workstation_id": "...", "capture_event": "..."}'
        ),
        "attachments": [
            "stage4/leaked_screenshot_master.png",
            "stage4/asset_register.csv",
            "stage4/capture_events.csv",
            "stage4/manifest_sha256.txt",
        ],
        "hints": [
            ("Zoom into the lower-right corner of the image carefully.", 10),
            ("Correlate the watermark with the asset register, then find the matching capture event for the application ID.", 20),
        ],
    },
    {
        "key": "stage5",
        "name": "Stage 5 - The False Trail",
        "category": "Digital Forensics / Log Analysis",
        "value": 300,
        "description": (
            "An evidence bundle of authentication, application-access, workstation-session and "
            "leave records is attached, along with an alert note about a failed-login event. "
            "Build a timeline for the application from Stage 3/4 and determine whether the "
            "highlighted failed-login event is actually part of the causal chain.\n\n"
            "Submit your answer at http://192.168.56.10:8082/check/stage5 as JSON:\n"
            '{"session_id": "...", "employee_id": "...", "unrelated_failed_event": "..."}'
        ),
        "attachments": [
            "stage5/auth.csv",
            "stage5/app_access.csv",
            "stage5/workstation_sessions.csv",
            "stage5/leave.csv",
            "stage5/alert_note.txt",
        ],
        "hints": [
            ("Start with the application-access record for the target application, not the failed-login alert.", 10),
            ("Follow the session_id across the authentication and workstation-session records, then compare against the failed event separately.", 20),
        ],
    },
    {
        "key": "stage6",
        "name": "Stage 6 - Reconstruct the Ledger",
        "category": "Programming / Scripting",
        "value": 400,
        "description": (
            "Final stage. A larger chat export, an employee directory and a broker ledger are "
            "attached. Write a Python script (correlate.py) that loads the evidence, decodes "
            "message bodies, filters records for the target application, joins the session "
            "information, maps the sender handle through the directory, and matches the payment "
            "reference in the broker ledger. Produce evidence.json with all six fields, then "
            "submit its contents to http://192.168.56.10:8082/check/stage6:\n"
            '{"employee_id":"...", "application_id":"...", "workstation_id":"...", '
            '"session_id":"...", "broker_transaction_ref":"...", "message_id":"..."}\n\n'
            "Be ready to explain at least one of the joins in your script during the viva."
        ),
        "attachments": [
            "stage6/messages.jsonl",
            "stage6/directory.csv",
            "stage6/broker_ledger.csv",
            "stage6/SCHEMA.md",
        ],
        "hints": [
            ("Start by joining on application_id and session_id.", 10),
            ("Map the sender handle through directory.csv, then match transaction_ref against the broker ledger.", 20),
        ],
    },
]


def api(session, base_url, method, path, **kwargs):
    resp = session.request(method, f"{base_url}{path}", **kwargs)
    if not resp.ok:
        print(f"[!] {method} {path} -> {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        resp.raise_for_status()
    return resp.json()


def hint_cost(chal, pct):
    return round(chal["value"] * pct / 100)


def upload(s, base_url, chal_id, rel_path):
    full_path = os.path.join(EVIDENCE_DIR, rel_path)
    if not os.path.exists(full_path):
        print(f"    [!] Missing attachment: {full_path}", file=sys.stderr)
        return
    with open(full_path, "rb") as fh:
        # multipart upload must not carry the JSON content-type header
        headers = {k: v for k, v in s.headers.items() if k.lower() != "content-type"}
        resp = requests.post(f"{base_url}/files", headers=headers, files={"file": (os.path.basename(full_path), fh)},
                             data={"challenge_id": str(chal_id), "type": "challenge"}, timeout=30)
        resp.raise_for_status()


def sync_existing(s, base_url, chal, chal_id, flags, replace_files=False):
    """Idempotent fix-up of an already-imported challenge (no duplicates created)."""
    api(s, base_url, "PATCH", f"/challenges/{chal_id}", data=json.dumps({"state": "visible", "value": chal["value"]}))
    # flag
    cur = api(s, base_url, "GET", f"/flags?challenge_id={chal_id}")["data"]
    if cur:
        if cur[0]["content"] != flags[chal["key"]]:
            api(s, base_url, "PATCH", f"/flags/{cur[0]['id']}", data=json.dumps({"content": flags[chal["key"]]}))
            print("    flag re-synced to flags.json")
    else:
        api(s, base_url, "POST", "/flags", data=json.dumps({"challenge_id": chal_id, "content": flags[chal["key"]],
                                                             "type": "static", "data": "case_sensitive"}))
    # hints: correct costs, create any missing
    hints = sorted(api(s, base_url, "GET", f"/hints?challenge_id={chal_id}")["data"], key=lambda h: h["id"])
    for n, (text, pct) in enumerate(chal["hints"]):
        cost = hint_cost(chal, pct)
        if n < len(hints):
            if hints[n].get("cost") != cost:
                api(s, base_url, "PATCH", f"/hints/{hints[n]['id']}", data=json.dumps({"cost": cost}))
                print(f"    hint {n+1} cost -> {cost}")
        else:
            api(s, base_url, "POST", "/hints", data=json.dumps({"challenge_id": chal_id, "content": text, "cost": cost}))
    # files: upload only attachments whose filename is not yet present
    have = {os.path.basename(f["location"]): f["id"] for f in api(s, base_url, "GET", f"/challenges/{chal_id}/files")["data"]}
    for rel in chal["attachments"]:
        name = os.path.basename(rel)
        if name in have and replace_files:
            api(s, base_url, "DELETE", f"/files/{have[name]}")
            have.pop(name)
            print(f"    removed old attachment {name}")
        if name not in have:
            upload(s, base_url, chal_id, rel)
            print(f"    attached {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="e.g. http://192.168.56.10:8000")
    ap.add_argument("--token", required=True, help="CTFd Admin API token")
    ap.add_argument("--replace-files", action="store_true",
                    help="for already-imported challenges, delete and re-upload every attachment "
                         "(use after regenerating evidence so participants get the new files)")
    args = ap.parse_args()

    base_url = args.url.rstrip("/") + "/api/v1"
    s = requests.Session()
    s.headers.update({"Authorization": f"Token {args.token}", "Content-Type": "application/json"})

    flags = load_flags()
    existing = {c["name"]: c["id"] for c in api(s, base_url, "GET", "/challenges?view=admin")["data"]}
    ids = {}

    for chal in CHALLENGES:
        if chal["name"] in existing:
            chal_id = ids[chal["key"]] = existing[chal["name"]]
            print(f"[=] Exists, syncing: {chal['name']} (id {chal_id})")
            sync_existing(s, base_url, chal, chal_id, flags, args.replace_files)
            continue
        print(f"[+] Creating challenge: {chal['name']}")
        payload = {"name": chal["name"], "category": chal["category"], "description": chal["description"],
                   "value": chal["value"], "state": "visible", "type": "standard"}
        chal_id = ids[chal["key"]] = api(s, base_url, "POST", "/challenges", data=json.dumps(payload))["data"]["id"]
        api(s, base_url, "POST", "/flags", data=json.dumps({"challenge_id": chal_id, "content": flags[chal["key"]],
                                                             "type": "static", "data": "case_sensitive"}))
        for text, pct in chal["hints"]:
            api(s, base_url, "POST", "/hints", data=json.dumps({"challenge_id": chal_id, "content": text,
                                                                 "cost": hint_cost(chal, pct)}))
        for rel in chal["attachments"]:
            upload(s, base_url, chal_id, rel)

    order = ["stage1", "stage2", "stage3", "stage4", "stage5", "stage6"]
    for prev_key, cur_key in zip(order, order[1:]):
        print(f"[+] Prerequisite: {cur_key} requires {prev_key}")
        api(s, base_url, "PATCH", f"/challenges/{ids[cur_key]}",
            data=json.dumps({"requirements": {"prerequisites": [ids[prev_key]], "anonymize": True}}))

    print("\n[+] Done. Stages 2-6 are visible-but-locked (anonymized) until the previous stage is solved.")
    print("    Test with a NORMAL participant account, not the admin account (admins bypass prerequisites).")


if __name__ == "__main__":
    main()
