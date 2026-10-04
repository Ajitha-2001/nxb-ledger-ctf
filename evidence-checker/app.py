#!/usr/bin/env python3
"""
NXB Ledger - Evidence Checker
==============================
A small, deliberately conservative validation service for the stages whose
answers are structured facts rather than a single embedded checkpoint flag
(Stages 1, 4, 5 and 6). Stages 2 and 3 expose their flags directly once the
task is solved, per the design report, and do not use this service.

Security posture (matches the design report's "Flag Validation" section):
  - Accepts only bounded JSON (<= 16 KB).
  - Rejects unexpected fields and wrong types for the fields it does expect.
  - Never executes participant-supplied code or reads arbitrary paths.
  - Incorrect responses are generic (no partial-correctness hints).
  - Simple per-IP-per-stage attempt cooldown to slow brute forcing.

The answer key is loaded from a read-only mounted secrets file and is never
returned to the client in any form.
"""
import json
import os
import time
from collections import defaultdict
from threading import Lock

from flask import Flask, jsonify, request

app = Flask(__name__)

MAX_BODY_BYTES = 16 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

ANSWER_KEY_PATH = os.environ.get("ANSWER_KEY_PATH", "/run/secrets/answer_key.json")
with open(ANSWER_KEY_PATH) as f:
    ANSWER_KEY = json.load(f)

FLAGS = ANSWER_KEY["flags"]

# --- naive in-memory rate limiting: 1 attempt per 3 seconds per (ip, stage) ---
_last_attempt = defaultdict(float)
_lock = Lock()
COOLDOWN_SECONDS = 3
MAX_ATTEMPTS_PER_MINUTE = 15
_attempt_log = defaultdict(list)


def rate_limited(key):
    now = time.time()
    with _lock:
        if now - _last_attempt[key] < COOLDOWN_SECONDS:
            return True
        _last_attempt[key] = now
        log = _attempt_log[key]
        log.append(now)
        _attempt_log[key] = [t for t in log if now - t < 60]
        if len(_attempt_log[key]) > MAX_ATTEMPTS_PER_MINUTE:
            return True
    return False


def client_key(stage):
    return f"{request.remote_addr}:{stage}"


def bad_request(msg="Malformed request."):
    return jsonify({"correct": False, "message": msg}), 400


def incorrect():
    return jsonify({"correct": False, "message": "Incorrect. Please review the evidence and try again."}), 200


def correct(flag):
    return jsonify({"correct": True, "flag": flag}), 200


def get_json_strict(expected_fields):
    """Parse JSON body, reject unexpected fields / wrong types / oversized input."""
    if request.content_length is not None and request.content_length > MAX_BODY_BYTES:
        return None, "Request too large."
    if not request.is_json:
        return None, "Content-Type must be application/json."
    try:
        data = request.get_json(force=False, silent=False)
    except Exception:
        return None, "Invalid JSON."
    if not isinstance(data, dict):
        return None, "JSON body must be an object."
    unexpected = set(data.keys()) - set(expected_fields.keys())
    if unexpected:
        return None, "Unexpected fields in request."
    for field, field_type in expected_fields.items():
        if field not in data:
            return None, f"Missing field: {field}"
        if not isinstance(data[field], field_type):
            return None, f"Field {field} has the wrong type."
        if isinstance(data[field], str) and len(data[field]) > 128:
            return None, f"Field {field} is too long."
    return data, None


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


@app.route("/check/stage1", methods=["POST"])
def check_stage1():
    if rate_limited(client_key("stage1")):
        return jsonify({"correct": False, "message": "Too many attempts. Please wait."}), 429
    data, err = get_json_strict({
        "post_id": str,
        "contact_code": str,
        "feature1": str,
        "feature2": str,
    })
    if err:
        return bad_request(err)
    key = ANSWER_KEY["stage1"]
    if (data["post_id"].strip().upper() == key["post_id"]
            and data["contact_code"].strip().upper() == key["contact_code"]
            and data["feature1"].strip()
            and data["feature2"].strip()):
        return correct(FLAGS["stage1"])
    return incorrect()


@app.route("/check/stage4", methods=["POST"])
def check_stage4():
    if rate_limited(client_key("stage4")):
        return jsonify({"correct": False, "message": "Too many attempts. Please wait."}), 429
    data, err = get_json_strict({
        "workstation_id": str,
        "capture_event": str,
    })
    if err:
        return bad_request(err)
    key = ANSWER_KEY["stage4"]
    if (data["workstation_id"].strip().upper() == key["workstation_id"]
            and data["capture_event"].strip().upper() == key["capture_event"]):
        return correct(FLAGS["stage4"])
    return incorrect()


@app.route("/check/stage5", methods=["POST"])
def check_stage5():
    if rate_limited(client_key("stage5")):
        return jsonify({"correct": False, "message": "Too many attempts. Please wait."}), 429
    data, err = get_json_strict({
        "session_id": str,
        "employee_id": str,
        "unrelated_failed_event": str,
    })
    if err:
        return bad_request(err)
    key = ANSWER_KEY["stage5"]
    if (data["session_id"].strip().upper() == key["session_id"]
            and data["employee_id"].strip().upper() == key["employee_id"]
            and data["unrelated_failed_event"].strip().upper() == key["unrelated_failed_event"]):
        return correct(FLAGS["stage5"])
    return incorrect()


@app.route("/check/stage6", methods=["POST"])
def check_stage6():
    if rate_limited(client_key("stage6")):
        return jsonify({"correct": False, "message": "Too many attempts. Please wait."}), 429
    expected_fields = {
        "employee_id": str,
        "application_id": str,
        "workstation_id": str,
        "session_id": str,
        "broker_transaction_ref": str,
        "message_id": str,
    }
    data, err = get_json_strict(expected_fields)
    if err:
        return bad_request(err)
    key = ANSWER_KEY["stage6"]
    ok = all(
        data[field].strip().upper() == key[field].upper()
        for field in expected_fields
    )
    if ok:
        return correct(FLAGS["stage6"])
    return incorrect()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

# ---------------------------------------------------------------------------
# Browser submission forms (GET)
# The challenge descriptions link players directly at these URLs. A browser
# visit is a GET, so each /check/<stage> also serves a small styled HTML form.
# The form submits via fetch() as JSON to the same URL, so the strict JSON
# validation, answer-key secrecy and rate limiting of the POST handlers apply
# unchanged. No answer material is embedded in the page.
# ---------------------------------------------------------------------------

FORM_CSS = """
body{background:#070707;color:#d7d7d7;font-family:'Courier New',monospace;margin:0;padding:24px;}
.box{max-width:560px;margin:32px auto;border:1px solid #c1121f;background:#0d0d0f;padding:28px;box-shadow:0 0 24px rgba(193,18,31,.25);}
h1{color:#ff2b3a;font-size:20px;letter-spacing:3px;margin:0 0 4px;}
h2{color:#f5f5f5;font-size:16px;font-weight:normal;margin:0 0 20px;}
p.sub{color:#8a8a8a;font-size:12px;margin:0 0 20px;}
label{display:block;margin:12px 0 4px;color:#ff6b74;font-size:13px;}
input{width:100%%;box-sizing:border-box;background:#000;border:1px solid #c1121f;color:#f5f5f5;padding:10px;font-family:inherit;font-size:14px;}
input:focus{outline:none;border-color:#ff2b3a;box-shadow:0 0 8px rgba(255,43,58,.4);}
button{margin-top:20px;width:100%%;background:#c1121f;color:#fff;border:none;padding:12px;font-family:inherit;font-size:15px;letter-spacing:2px;cursor:pointer;}
button:hover{background:#ff2b3a;}
#result{margin-top:18px;padding:12px;font-size:14px;word-break:break-all;display:none;}
#result.ok{display:block;border:1px solid #00e676;color:#00e676;}
#result.bad{display:block;border:1px solid #ff2b3a;color:#ff6b74;}
.idx a{display:block;margin:8px 0;color:#ff6b74;}
"""

def _form_page(title, blurb, fields):
    inputs = "\n".join(
        '<label for="%s">%s</label><input id="%s" name="%s" maxlength="128" required autocomplete="off">' % (n, lbl, n, n)
        for n, lbl in fields
    )
    field_names = json.dumps([n for n, _ in fields])
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>%s - NXB Ledger</title><style>%s</style></head><body>"
            "<div class='box'><h1>&#x1f575; NXB LEDGER</h1><h2>%s</h2>"
            "<p class='sub'>%s</p>"
            "<form id='f'>%s<button type='submit'>SUBMIT EVIDENCE</button></form>"
            "<div id='result'></div>"
            "<script>"
            "var F=%s;"
            "document.getElementById('f').addEventListener('submit',function(e){"
            "e.preventDefault();"
            "var r=document.getElementById('result');r.className='';r.textContent='Validating...';r.style.display='block';"
            "var d={};for(var i=0;i<F.length;i++){d[F[i]]=document.getElementsByName(F[i])[0].value;}"
            "fetch(window.location.pathname,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})"
            ".then(function(resp){return resp.json().then(function(j){return {s:resp.status,j:j};});})"
            ".then(function(x){"
            "if(x.j.correct){r.textContent='ACCESS GRANTED - flag: '+x.j.flag;r.className='ok';}"
            "else{r.textContent=(x.j.message||'Incorrect.');r.className='bad';}"
            "})"
            ".catch(function(){r.textContent='Request failed. Is the checker reachable?';r.className='bad';});"
            "});"
            "</script></div></body></html>") % (title, FORM_CSS, title, blurb, inputs, field_names)

STAGE_FORMS = {
    "stage1": ("Stage 1 - The Broker's Promise",
               "Correlate the leaked post against the broker ads, then submit your findings.",
               [("post_id", "Post ID  (e.g. PUB-017)"),
                ("contact_code", "Broker contact code  (e.g. BRK17)"),
                ("feature1", "Distinctive feature 1"),
                ("feature2", "Distinctive feature 2")]),
    "stage4": ("Stage 4 - The Workstation Trace",
               "Identify the workstation and the capture event from the forensic image.",
               [("workstation_id", "Workstation ID"),
                ("capture_event", "Capture event")]),
    "stage5": ("Stage 5 - The False Trail",
               "Follow the session trail and name the unrelated failed event.",
               [("session_id", "Session ID"),
                ("employee_id", "Employee ID"),
                ("unrelated_failed_event", "Unrelated failed event")]),
    "stage6": ("Stage 6 - Reconstruct the Ledger",
               "Reconstruct the full chain: all six identifiers must match.",
               [("employee_id", "Employee ID"),
                ("application_id", "Application ID"),
                ("workstation_id", "Workstation ID"),
                ("session_id", "Session ID"),
                ("broker_transaction_ref", "Broker transaction ref"),
                ("message_id", "Message ID")]),
}

@app.route("/", methods=["GET"])
def index():
    links = "\n".join(
        "<a href='/check/%s'>%s</a>" % (stage, title)
        for stage, (title, _, _) in STAGE_FORMS.items()
    )
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>NXB Ledger - Evidence Checker</title><style>%s</style></head>"
            "<body><div class='box idx'><h1>&#x1f575; NXB LEDGER</h1>"
            "<h2>Evidence Checker</h2>"
            "<p class='sub'>Select a stage to submit evidence:</p>%s</div></body></html>") % (FORM_CSS, links)

@app.route("/check/<stage>", methods=["GET"])
def check_form(stage):
    if stage not in STAGE_FORMS:
        return jsonify({"correct": False, "message": "Unknown stage."}), 404
    title, blurb, fields = STAGE_FORMS[stage]
    return _form_page(title, blurb, fields)
