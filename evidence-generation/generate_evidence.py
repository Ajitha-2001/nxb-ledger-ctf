#!/usr/bin/env python3
"""
NXB Ledger - Canonical Evidence Generator
==========================================
Generates ALL synthetic evidence for the 6-stage CTF from a single canonical
seed, so every stage stays internally consistent (same IDs, same timeline).

Run once during environment build:
    python3 generate_evidence.py

Outputs:
    output/secrets/flags.json          <- NEVER ship to participants or CTFd export bundles
    output/stage1/  (broker site data + leaked screenshot)
    output/stage2/  (chat_fragment.json + manifest)
    output/stage4/  (asset_register.csv, capture_events.csv, screenshot crop)
    output/stage5/  (auth.csv, app_access.csv, workstation_sessions.csv, leave.csv, alert_note.txt)
    output/stage6/  (messages.jsonl, directory.csv, broker_ledger.csv)
    output/manifest.json               <- SHA-256 of every distributed evidence file
"""
import base64
import csv
import hashlib
import json
import os
import random
import secrets
import string
import sys
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
SECRETS_DIR = os.path.join(OUT, "secrets")
os.makedirs(SECRETS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Canonical seed (matches the design report exactly)
# ---------------------------------------------------------------------------
SEED = {
    "employee_id": "EMP042",
    "employee_name": "Ruwan",
    "branch_owner": "BR03",
    "workstation_id": "NXB-BR03-WS07",
    "application_id": "APP-0842",
    "application_owner_branch": "BR08",
    "session_id": "SES-91A",
    "capture_event": "CAP-0312",
    "broker_account": "BRK17",
    "public_post": "PUB-017",
    "broker_tx_ref": "TX-118",
    "chat_message_id": "CHAT-77",
    "unrelated_failed_employee": "EMP019",
    "unrelated_failed_event": "FAIL-009",
    "customer_synthetic_id": "NXB-DEMO-0842",
    "message_fragment_id": "FRAG-12",
}


def rand_token():
    """128-bit random token (16 random bytes from the OS CSPRNG) as 32 upper-case hex characters."""
    return secrets.token_hex(16).upper()


def make_flag(stage_num):
    return f"NXB{{S0{stage_num}_{rand_token()}}}"


# Flags are PRESERVED across re-runs so they keep matching .env and CTFd.
# Pass --new-flags only for a full reset (then re-import into a fresh CTFd and delete .env).
FLAGS_PATH = os.path.join(SECRETS_DIR, "flags.json")
FLAGS = None
if "--new-flags" not in sys.argv and os.path.exists(FLAGS_PATH):
    with open(FLAGS_PATH) as f:
        existing = json.load(f)
    if all(f"stage{i}" in existing for i in range(1, 7)):
        FLAGS = existing
        weak = [k for k, v in existing.items() if len(v.split("_", 1)[-1].rstrip("}")) < 32]
        if weak:
            print(f"[!] WARNING: {weak} use a short (<128-bit) token from an older build. "
                  "For a final deployment run with --new-flags.")
        print("[+] Reusing existing flags from", FLAGS_PATH, "(use --new-flags to regenerate)")
if FLAGS is None:
    FLAGS = {f"stage{i}": make_flag(i) for i in range(1, 7)}
    with open(FLAGS_PATH, "w") as f:
        json.dump(FLAGS, f, indent=2)
    print("[+] Generated NEW flags ->", FLAGS_PATH)
print("    KEEP THIS FILE OUT OF ANY PARTICIPANT-FACING BUNDLE OR GIT REPO.")

# All non-flag randomness (noise records, row order) is seeded, so evidence is reproducible.
RNG = random.Random(20260810)

manifest = []


def record_file(path):
    with open(path, "rb") as f:
        data = f.read()
    digest = hashlib.sha256(data).hexdigest()
    manifest.append({
        "file": os.path.relpath(path, OUT),
        "sha256": digest,
        "size": len(data),
    })
    return digest


# ---------------------------------------------------------------------------
# Font helper (falls back to default bitmap font if no TTF is available)
# ---------------------------------------------------------------------------
def get_font(size):
    for candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# STAGE 1 + 4 shared artifact: the leaked screenshot
# ---------------------------------------------------------------------------
def build_leaked_screenshot():
    stage1_dir = os.path.join(OUT, "stage1")
    stage4_dir = os.path.join(OUT, "stage4")
    os.makedirs(stage1_dir, exist_ok=True)
    os.makedirs(stage4_dir, exist_ok=True)

    W, H = 900, 560
    img = Image.new("RGB", (W, H), (245, 246, 248))
    d = ImageDraw.Draw(img)

    title_font = get_font(26)
    label_font = get_font(16)
    body_font = get_font(16)
    small_font = get_font(13)
    watermark_font = get_font(15)

    # Header bar
    d.rectangle([0, 0, W, 60], fill=(20, 40, 90))
    d.text((20, 15), "NXB Bank - Internal Micro Loan Portal", font=title_font, fill=(255, 255, 255))

    # Card
    d.rectangle([30, 90, W - 30, H - 60], outline=(180, 184, 190), width=2, fill=(255, 255, 255))
    y = 115
    rows = [
        ("Application ID:", SEED["application_id"]),
        ("Customer ID (synthetic):", SEED["customer_synthetic_id"]),
        ("Owning Branch:", SEED["application_owner_branch"]),
        ("Salary Band:", "LKR 90,000 - 120,000"),
        ("Loan Amount Requested:", "LKR 450,000"),
    ]
    for label, value in rows:
        d.text((55, y), label, font=label_font, fill=(70, 74, 80))
        d.text((330, y), value, font=body_font, fill=(20, 20, 20))
        y += 34

    y += 10
    d.text((55, y), "Approval Notes:", font=label_font, fill=(70, 74, 80))
    y += 26
    note_lines = [
        "Applicant flagged for expedited processing. A documentation",
        "clearance fee of 2% of the approved loan value applies before",
        "the file is released for external verification. Ref handled",
        "outside standard branch workflow this cycle.",
    ]
    for line in note_lines:
        d.text((55, y), line, font=body_font, fill=(30, 30, 30))
        y += 22

    # Footer / chrome
    d.text((55, H - 90), "Logged in as: EMP042 (BR03)", font=small_font, fill=(90, 90, 90))
    d.text((55, H - 68), "Session: " + SEED["session_id"], font=small_font, fill=(90, 90, 90))

    # Faint workstation watermark (deliberately small - Stage 1 should NOT need it;
    # Stage 4 asks participants to zoom into this exact region).
    watermark_text = SEED["workstation_id"]
    d.text((W - 230, H - 40), watermark_text, font=watermark_font, fill=(210, 213, 218))

    # Save full-resolution master (used for Stage 4 - forensic zoom)
    master_path = os.path.join(stage4_dir, "leaked_screenshot_master.png")
    img.save(master_path)

    # Save participant-facing copy for Stage 1 (identical pixels; participants
    # are simply not told where to look yet)
    stage1_path = os.path.join(stage1_dir, "leaked_post.png")
    img.save(stage1_path)

    h1 = record_file(stage1_path)
    h4 = record_file(master_path)
    return h1, h4


hash_stage1_png, hash_stage4_png = build_leaked_screenshot()
print("[+] Built leaked screenshot (shared Stage 1 / Stage 4 artifact)")

# ---------------------------------------------------------------------------
# STAGE 1: broker site data (source index + ad metadata used to build HTML)
# ---------------------------------------------------------------------------
stage1_dir = os.path.join(OUT, "stage1")

FEE_PHRASE = "documentation clearance fee of 2% of the approved loan value"

broker_ads = []
# 5 distractor ads + 1 correct ad. Distractors share loan/fee vocabulary but
# never combine BOTH the exact fee phrase AND the correct contact code.
distractor_templates = [
    ("PUB-011", "BRK04", "processing charge of 3% applies before release"),
    ("PUB-012", "BRK09", "administrative fee required for fast-track approval"),
    ("PUB-013", "BRK21", "documentation clearance fee of 2% of the approved loan value"),  # phrase match, wrong contact
    ("PUB-014", "BRK17", "flat handling fee of LKR 5,000 for verification"),  # contact match, wrong phrase
    ("PUB-016", "BRK30", "urgent loan file release, contact for terms"),
]
for post_id, contact, phrase in distractor_templates:
    broker_ads.append({"post_id": post_id, "contact_code": contact, "phrase": phrase, "match": False})

# The correct ad: BOTH the exact fee phrase AND contact code BRK17
broker_ads.append({
    "post_id": SEED["public_post"],
    "contact_code": SEED["broker_account"],
    "phrase": FEE_PHRASE,
    "match": True,
})

with open(os.path.join(stage1_dir, "broker_ads_source.json"), "w") as f:
    json.dump(broker_ads, f, indent=2)

print("[+] Stage 1 broker ad data prepared (%d ads, 1 correct match)" % len(broker_ads))

# ---------------------------------------------------------------------------
# STAGE 2: encoded chat fragment
# ---------------------------------------------------------------------------
stage2_dir = os.path.join(OUT, "stage2")
os.makedirs(stage2_dir, exist_ok=True)

chat_plaintext = (
    f"handle:ghostbroker17 - file for {SEED['application_id']} is ready, "
    f"same fee terms as discussed. reply when the transfer clears. "
    f"[TRAINING CHECKPOINT FLAG: {FLAGS['stage2']}]"
)
encoded_body = base64.b64encode(chat_plaintext.encode("utf-8")).decode("ascii")

chat_fragment = {
    "export_format": "SharedDriveChatExport-v1",
    "export_note": "message 'body' field is Base64-encoded per export spec section 4.2; "
                   "this is an ENCODING used for transport, not an encryption scheme - "
                   "no secret key is required to reverse it.",
    "message_id": SEED["message_fragment_id"],
    "encoding": "base64",
    "charset": "utf-8",
    "body": encoded_body,
}
chat_path = os.path.join(stage2_dir, "chat_fragment.json")
with open(chat_path, "w") as f:
    json.dump(chat_fragment, f, indent=2)

chat_hash = record_file(chat_path)
manifest_path = os.path.join(stage2_dir, "manifest_sha256.txt")
with open(manifest_path, "w") as f:
    f.write(f"{chat_hash}  chat_fragment.json\n")
record_file(manifest_path)

print("[+] Stage 2 chat_fragment.json generated (decoded checkpoint flag embedded)")

# ---------------------------------------------------------------------------
# STAGE 4: asset register + capture events
# ---------------------------------------------------------------------------
stage4_dir = os.path.join(OUT, "stage4")
os.makedirs(stage4_dir, exist_ok=True)

asset_register = [
    ["workstation_id", "branch", "assigned_employee_id", "asset_type", "status"],
    ["NXB-BR01-WS02", "BR01", "EMP011", "Teller Workstation", "active"],
    ["NXB-BR03-WS05", "BR03", "EMP038", "Loan Officer Workstation", "active"],
    [SEED["workstation_id"], "BR03", SEED["employee_id"], "Loan Officer Workstation", "active"],
    ["NXB-BR08-WS01", "BR08", "EMP090", "Loan Officer Workstation", "active"],
    ["NXB-BR03-WS09", "BR03", "EMP044", "Loan Officer Workstation", "decommissioned"],
]
with open(os.path.join(stage4_dir, "asset_register.csv"), "w", newline="") as f:
    csv.writer(f).writerows(asset_register)

capture_events = [
    ["capture_event_id", "workstation_id", "application_id", "timestamp_utc+0530", "capture_type"],
    ["CAP-0301", "NXB-BR01-WS02", "APP-0711", "2026-08-10T09:02:00+05:30", "screen_capture"],
    ["CAP-0308", "NXB-BR03-WS05", "APP-0799", "2026-08-10T09:10:00+05:30", "screen_capture"],
    [SEED["capture_event"], SEED["workstation_id"], SEED["application_id"], "2026-08-10T09:18:00+05:30", "screen_capture"],
    ["CAP-0315", "NXB-BR08-WS01", "APP-0850", "2026-08-10T09:20:00+05:30", "screen_capture"],
]
with open(os.path.join(stage4_dir, "capture_events.csv"), "w", newline="") as f:
    csv.writer(f).writerows(capture_events)

stage4_files = ["leaked_screenshot_master.png", "asset_register.csv", "capture_events.csv"]
with open(os.path.join(stage4_dir, "manifest_sha256.txt"), "w") as f:
    for fn in stage4_files:
        with open(os.path.join(stage4_dir, fn), "rb") as fh:
            f.write(f"{hashlib.sha256(fh.read()).hexdigest()}  {fn}\n")
for fn in stage4_files + ["manifest_sha256.txt"]:
    record_file(os.path.join(stage4_dir, fn))

print("[+] Stage 4 asset_register.csv / capture_events.csv generated")

# ---------------------------------------------------------------------------
# STAGE 5: authentication / access / session / leave logs (with distractors)
# ---------------------------------------------------------------------------
stage5_dir = os.path.join(OUT, "stage5")
os.makedirs(stage5_dir, exist_ok=True)

auth_rows = [["event_id", "employee_id", "workstation_id", "timestamp_utc+0530", "result"]]
app_access_rows = [["access_id", "employee_id", "application_id", "session_id", "timestamp_utc+0530"]]
session_rows = [["session_id", "employee_id", "workstation_id", "login_time_utc+0530", "logout_time_utc+0530"]]
leave_rows = [["employee_id", "leave_date", "leave_type", "approved_by"]]

# --- The unrelated distractor: failed login for EMP019, no session, no app access ---
auth_rows.append(["AUTH-0001", SEED["unrelated_failed_employee"], "NXB-BR02-WS03",
                   "2026-08-10T08:42:00+05:30", "FAILED"])
auth_rows.append([SEED["unrelated_failed_event"], SEED["unrelated_failed_employee"], "NXB-BR02-WS03",
                   "2026-08-10T08:42:07+05:30", "FAILED"])
# Storyline (report 3.3 / Stage 5): Ruwan (EMP042) points at this alert and claims he was on leave.
# The leave record exists, but a leave record alone neither proves nor excludes system activity.
leave_rows.append([SEED["employee_id"], "2026-08-10", "full_day", "MGR-003"])
# EMP019's failed login has no successful session, no WS07 match and no APP-0842 access record.

# --- The real causal chain ---
auth_rows.append(["AUTH-0002", SEED["employee_id"], SEED["workstation_id"],
                   "2026-08-10T09:12:00+05:30", "SUCCESS"])
session_rows.append([SEED["session_id"], SEED["employee_id"], SEED["workstation_id"],
                      "2026-08-10T09:12:05+05:30", "2026-08-10T09:40:00+05:30"])
app_access_rows.append(["ACC-0501", SEED["employee_id"], SEED["application_id"],
                         SEED["session_id"], "2026-08-10T09:16:00+05:30"])

# --- Padding / noise records (unrelated normal activity) ---
noise_employees = ["EMP011", "EMP022", "EMP033", "EMP044", "EMP055", "EMP066", "EMP077", "EMP088"]
noise_ws = ["NXB-BR01-WS02", "NXB-BR03-WS05", "NXB-BR08-WS01", "NXB-BR03-WS09"]
apps_noise = ["APP-0711", "APP-0799", "APP-0850", "APP-0602", "APP-0733"]
t = 1
for i in range(1, 55):
    emp = RNG.choice(noise_employees)
    ws = RNG.choice(noise_ws)
    hour = 8 + (i % 6)
    minute = (i * 3) % 60
    t0 = datetime(2026, 8, 10, hour, minute)
    ts = t0.strftime("%Y-%m-%dT%H:%M:00+05:30")
    logout_ts = (t0 + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:00+05:30")  # always after login
    result = "SUCCESS" if i % 11 != 0 else "FAILED"
    auth_rows.append([f"AUTH-{1000+i}", emp, ws, ts, result])
    if result == "SUCCESS" and i % 2 == 0:
        sid = f"SES-N{100+i}"
        session_rows.append([sid, emp, ws, ts, logout_ts])
        if i % 3 == 0:
            app_access_rows.append([f"ACC-{2000+i}", emp, RNG.choice(apps_noise), sid, ts])

alert_note = (
    "IT SECURITY ALERT NOTE\n"
    "-----------------------\n"
    f"Ref: {SEED['unrelated_failed_event']}\n"
    f"A failed login attempt was recorded for account {SEED['unrelated_failed_employee']} at "
    "08:42:00 (+05:30) on 2026-08-10, originating from workstation NXB-BR02-WS03.\n\n"
    f"The loan officer under investigation ({SEED['employee_id']}, Ruwan) points to this alert, "
    "attributes the leaked application incident to it, and states he was on leave for the full day.\n\n"
    f"Leave records show a leave entry for {SEED['employee_id']} on that date. "
    "Leave status alone does not prove or disprove system activity, and this alert has no "
    "matching successful session or application-access record. Investigators should not treat "
    "this alert as confirmed evidence without further correlation.\n"
)
with open(os.path.join(stage5_dir, "alert_note.txt"), "w") as f:
    f.write(alert_note)

with open(os.path.join(stage5_dir, "auth.csv"), "w", newline="") as f:
    csv.writer(f).writerows(auth_rows)
with open(os.path.join(stage5_dir, "app_access.csv"), "w", newline="") as f:
    csv.writer(f).writerows(app_access_rows)
with open(os.path.join(stage5_dir, "workstation_sessions.csv"), "w", newline="") as f:
    csv.writer(f).writerows(session_rows)
with open(os.path.join(stage5_dir, "leave.csv"), "w", newline="") as f:
    csv.writer(f).writerows(leave_rows)

for fn in ["auth.csv", "app_access.csv", "workstation_sessions.csv", "leave.csv", "alert_note.txt"]:
    record_file(os.path.join(stage5_dir, fn))

print(f"[+] Stage 5 logs generated ({len(auth_rows)-1} auth, {len(app_access_rows)-1} access, "
      f"{len(session_rows)-1} sessions)")

# ---------------------------------------------------------------------------
# STAGE 6: messages.jsonl + directory.csv + broker_ledger.csv
# ---------------------------------------------------------------------------
stage6_dir = os.path.join(OUT, "stage6")
os.makedirs(stage6_dir, exist_ok=True)

directory_rows = [["handle", "employee_id", "full_name", "branch"]]
directory_rows.append(["ghostbroker17", "N/A", "N/A (external broker contact)", "N/A"])
directory_rows.append(["r.silva", "EMP011", "R. Silva", "BR01"])
directory_rows.append(["nxb_ruwan", SEED["employee_id"], "Ruwan (synthetic)", "BR03"])
directory_rows.append(["a.perera", "EMP038", "A. Perera", "BR03"])
directory_rows.append(["t.fernando", "EMP090", "T. Fernando", "BR08"])
with open(os.path.join(stage6_dir, "directory.csv"), "w", newline="") as f:
    csv.writer(f).writerows(directory_rows)

broker_ledger_rows = [["tx_ref", "broker_account", "amount_lkr", "date", "note"]]
broker_ledger_rows.append(["TX-101", "BRK04", "8000", "2026-08-05", "unrelated file"])
broker_ledger_rows.append([SEED["broker_tx_ref"], SEED["broker_account"], "9000",
                            "2026-08-10", f"payment ref linked to {SEED['application_id']}"])
broker_ledger_rows.append(["TX-142", "BRK30", "6000", "2026-08-11", "unrelated file"])
with open(os.path.join(stage6_dir, "broker_ledger.csv"), "w", newline="") as f:
    csv.writer(f).writerows(broker_ledger_rows)

# messages.jsonl - ~200 records, mostly noise, one real chain (CHAT-77)
messages = []
real_msg_body = (
    f"handle:nxb_ruwan -> ghostbroker17 | app {SEED['application_id']} confirmed, "
    f"payment ref {SEED['broker_tx_ref']} incoming."
)
messages.append({
    "message_id": SEED["chat_message_id"],
    "sender_handle": "nxb_ruwan",
    "application_id": SEED["application_id"],
    "transaction_ref": SEED["broker_tx_ref"],
    "body_b64": base64.b64encode(real_msg_body.encode()).decode(),
})

# Decoys that also carry application_id APP-0842 but are NOT the employee-to-broker chain:
# the external broker's own messages (handle is not an employee in directory.csv).
for mid, tx, txt in [
    ("CHAT-76", None, "handle:ghostbroker17 -> nxb_ruwan | is the file ready?"),
    ("CHAT-78", SEED["broker_tx_ref"], "handle:ghostbroker17 -> nxb_ruwan | transfer sent, see ledger."),
]:
    messages.append({
        "message_id": mid,
        "sender_handle": "ghostbroker17",
        "application_id": SEED["application_id"],
        "transaction_ref": tx,
        "body_b64": base64.b64encode(txt.encode()).decode(),
    })

noise_handles = ["r.silva", "a.perera", "t.fernando", "ghostbroker04", "ghostbroker30", "unknownuser"]
noise_apps = ["APP-0711", "APP-0799", "APP-0850", "APP-0602", "APP-0733", None]
noise_tx = ["TX-101", "TX-142", None]
for i in range(200):
    handle = RNG.choice(noise_handles)
    app = RNG.choice(noise_apps)
    tx = RNG.choice(noise_tx)
    body = f"handle:{handle} -> misc chat noise record {i} - nothing relevant here."
    messages.append({
        "message_id": f"MSG-{3000+i}",
        "sender_handle": handle,
        "application_id": app,
        "transaction_ref": tx,
        "body_b64": base64.b64encode(body.encode()).decode(),
    })
RNG.shuffle(messages)

with open(os.path.join(stage6_dir, "messages.jsonl"), "w") as f:
    for m in messages:
        f.write(json.dumps(m) + "\n")

schema_md = """# Stage 6 - data schema and example output

You are given three files here plus the Stage 5 evidence you already hold
(`app_access.csv`, `workstation_sessions.csv`). Python 3 standard library is enough
(`csv`, `json`, `base64`).

## messages.jsonl  (one JSON object per line, order is NOT meaningful)
| field | type | notes |
|---|---|---|
| message_id | string | unique message reference |
| sender_handle | string | chat handle, maps to `directory.csv` |
| application_id | string or null | application the message was tagged with |
| transaction_ref | string or null | payment reference, maps to `broker_ledger.csv` |
| body_b64 | string | Base64 of a UTF-8 message body |

## directory.csv
`handle, employee_id, full_name, branch` - `N/A` means the handle is not a bank employee.

## broker_ledger.csv
`tx_ref, broker_account, amount_lkr, date, note`

## Stage 5 files you will need to join
`app_access.csv`: `access_id, employee_id, application_id, session_id, timestamp_utc+0530`
`workstation_sessions.csv`: `session_id, employee_id, workstation_id, login_time_utc+0530, logout_time_utc+0530`

## Required output: evidence.json
A JSON object with exactly these six string fields (values below are PLACEHOLDERS, not the answer):

```json
{
  "employee_id": "EMP000",
  "application_id": "APP-0000",
  "workstation_id": "NXB-BR00-WS00",
  "session_id": "SES-000",
  "broker_transaction_ref": "TX-000",
  "message_id": "CHAT-00"
}
```

## Rules
* Several messages mention the target application. Only the chain that links an *employee*
  to a *payment record for that application* counts; explain at least one of your joins.
* Your script `correlate.py` must give the same result if the input rows are shuffled.
* Do not hard-code the answer values.
"""
with open(os.path.join(stage6_dir, "SCHEMA.md"), "w") as f:
    f.write(schema_md)

for fn in ["messages.jsonl", "directory.csv", "broker_ledger.csv", "SCHEMA.md"]:
    record_file(os.path.join(stage6_dir, fn))

print(f"[+] Stage 6 messages.jsonl generated ({len(messages)} records, 1 real chain)")

# ---------------------------------------------------------------------------
# Expected evidence.json for Stage 6 (kept server-side only, used by checker/tests)
# ---------------------------------------------------------------------------
expected_evidence = {
    "employee_id": SEED["employee_id"],
    "application_id": SEED["application_id"],
    "workstation_id": SEED["workstation_id"],
    "session_id": SEED["session_id"],
    "broker_transaction_ref": SEED["broker_tx_ref"],
    "message_id": SEED["chat_message_id"],
}
with open(os.path.join(SECRETS_DIR, "expected_evidence_stage6.json"), "w") as f:
    json.dump(expected_evidence, f, indent=2)

# ---------------------------------------------------------------------------
# Canonical answer key for the evidence-checker service (secret)
# ---------------------------------------------------------------------------
answer_key = {
    "stage1": {"post_id": SEED["public_post"], "contact_code": SEED["broker_account"]},
    "stage4": {"workstation_id": SEED["workstation_id"], "capture_event": SEED["capture_event"]},
    "stage5": {
        "session_id": SEED["session_id"],
        "employee_id": SEED["employee_id"],
        "unrelated_failed_event": SEED["unrelated_failed_event"],
    },
    "stage6": expected_evidence,
    "flags": FLAGS,
}
with open(os.path.join(SECRETS_DIR, "answer_key.json"), "w") as f:
    json.dump(answer_key, f, indent=2)

with open(os.path.join(SECRETS_DIR, "canonical_seed.json"), "w") as f:
    json.dump(SEED, f, indent=2)

with open(os.path.join(OUT, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)

print("\n[+] All evidence generated under:", OUT)
print("[+] Secret answer key at:", os.path.join(SECRETS_DIR, "answer_key.json"))
print("[+] Manifest (SHA-256 of every distributed file):", os.path.join(OUT, "manifest.json"))
print("\nSTAGE FLAGS (for CTFd import - keep private):")
for k, v in FLAGS.items():
    print(f"  {k}: {v}")
