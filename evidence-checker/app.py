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
# Browser submission forms (GET) - broker-board hacker theme
# The challenge descriptions link players directly at these URLs. A browser
# visit is a GET, so each /check/<stage> also serves a styled HTML form.
# The form submits via fetch() as JSON to the same URL, so the strict JSON
# validation, answer-key secrecy and rate limiting of the POST handlers apply
# unchanged. No answer material is embedded in the page.
# Visual language mirrors theme/nxb-theme.css (broker board): red/black ops
# console, glitch hero, terminal-window submission forms.
# ---------------------------------------------------------------------------

FORM_CSS = """
:root{--bg:#060506;--panel:#110809;--panel2:#180b0d;--line:#3d1018;--red:#ff2a44;--red2:#b8102a;--glow:rgba(255,42,68,.38);--txt:#eadcdd;--dim:#9b7c81;--ok:#4dff94;--mono:"JetBrains Mono","Cascadia Code",Consolas,"DejaVu Sans Mono",ui-monospace,monospace}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--txt);font:15px/1.65 var(--mono);background:var(--bg);background-image:radial-gradient(ellipse 80% 45% at 50% -8%,rgba(255,42,68,.24),transparent 70%),linear-gradient(rgba(255,42,68,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,42,68,.05) 1px,transparent 1px);background-size:auto,44px 44px,44px 44px;background-attachment:fixed}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:60;background:repeating-linear-gradient(0deg,rgba(0,0,0,.26) 0 1px,transparent 1px 3px)}
#rain{position:fixed;inset:0;width:100%;height:100%;z-index:0;opacity:.32;pointer-events:none}
::selection{background:var(--red);color:#000}
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 28px;background:rgba(6,5,6,.92);border-bottom:1px solid var(--red2);box-shadow:0 2px 24px rgba(255,42,68,.18)}
.brand{font-weight:800;letter-spacing:.14em;color:#fff;font-size:16px}
.brand b{color:var(--red)}
.brand::after{content:"\\2588";color:var(--red);margin-left:6px;animation:blink 1.1s steps(1) infinite}
.pill{border:1px solid var(--red2);color:var(--red);padding:2px 10px;font-size:12px;letter-spacing:.08em;background:rgba(255,42,68,.08)}
main{width:100%;max-width:760px;margin:0 auto;padding:40px 24px 56px;position:relative;z-index:1}
main.wide{max-width:1040px}
footer{text-align:center;color:var(--dim);font-size:12px;padding:22px;border-top:1px solid var(--line);position:relative;z-index:1}
.hero{padding:10px 0 30px}
.glitch{position:relative;display:inline-block;font-size:clamp(28px,5.6vw,56px);font-weight:800;letter-spacing:.02em;line-height:1.05;color:#fff;text-shadow:0 0 26px var(--glow);margin:0 0 14px}
.glitch::before,.glitch::after{content:attr(data-text);position:absolute;left:0;top:0;width:100%;overflow:hidden}
.glitch::before{color:var(--red);left:-3px;clip-path:inset(0 0 60% 0)}
.glitch::after{color:#7d0016;left:3px;clip-path:inset(55% 0 0 0)}
.typed{color:var(--dim);min-height:1.7em;margin:0 0 8px}
.typed::before{content:"root@nxb:~$ ";color:var(--red)}
.typed::after{content:"\\2588";color:var(--red);animation:blink 1s steps(1) infinite}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr);gap:18px}
.card{position:relative;background:linear-gradient(160deg,var(--panel2),var(--panel));border:1px solid var(--line);padding:20px 22px;color:inherit;text-decoration:none;display:flex;flex-direction:column;transition:border-color .2s,box-shadow .2s,transform .2s}
.card::before,.card::after{content:"";position:absolute;width:14px;height:14px;border:2px solid var(--red);pointer-events:none}
.card::before{top:-1px;left:-1px;border-right:0;border-bottom:0}
.card::after{bottom:-1px;right:-1px;border-left:0;border-top:0}
.card:hover{border-color:var(--red2);box-shadow:0 0 28px rgba(255,42,68,.2);transform:translateY(-2px)}
.card .id{font-weight:800;color:var(--red);letter-spacing:.06em;font-size:18px;margin:0 0 4px}
.card p{margin:0 0 14px;color:#dccacc;font-size:14px}
.card .go{margin-top:auto;align-self:flex-start;color:#fff;border:1px solid var(--red);padding:9px 20px;font-size:13px;font-weight:700;letter-spacing:.06em;clip-path:polygon(10px 0,100% 0,100% calc(100% - 10px),calc(100% - 10px) 100%,0 100%,0 10px)}
.card:hover .go{background:var(--red);color:#000;box-shadow:0 0 22px var(--glow)}
.win{border:1px solid var(--red2);background:rgba(10,4,5,.94);box-shadow:0 0 50px rgba(255,42,68,.22);position:relative}
.win::before,.win::after{content:"";position:absolute;width:14px;height:14px;border:2px solid var(--red);pointer-events:none;z-index:2}
.win::before{top:-1px;left:-1px;border-right:0;border-bottom:0}
.win::after{bottom:-1px;right:-1px;border-left:0;border-top:0}
.win .bar{display:flex;align-items:center;gap:7px;padding:9px 14px;border-bottom:1px solid var(--line);background:#150709;font-size:12px;color:var(--dim)}
.win .bar i{width:10px;height:10px;border-radius:50%;background:var(--line)}
.win .bar i:first-child{background:var(--red)}
.win .bar span{margin-left:auto}
.win .wbody{padding:26px 26px 22px}
.win h2{margin:0 0 8px;font-size:20px;color:#fff;font-weight:700}
.win h2::before{content:"# ";color:var(--red)}
p.sub{color:var(--dim);font-size:13px;margin:0 0 20px}
label{display:block;font-size:12.5px;color:var(--dim);letter-spacing:.06em;margin-bottom:4px}
input[type=text]{width:100%;font:inherit;color:#fff;background:#0a0405;border:1px solid var(--line);border-left:3px solid var(--red2);padding:11px 12px;margin-bottom:16px;caret-color:var(--red)}
input:focus{outline:none;border-color:var(--red);box-shadow:0 0 0 3px rgba(255,42,68,.18)}
button[type=submit]{width:100%;font:inherit;font-size:14px;font-weight:700;letter-spacing:.12em;cursor:pointer;color:#fff;background:var(--red2);border:1px solid var(--red);padding:13px;clip-path:polygon(12px 0,100% 0,100% calc(100% - 12px),calc(100% - 12px) 100%,0 100%,0 12px);transition:background .15s,box-shadow .15s,color .15s}
button[type=submit]:hover{background:var(--red);color:#000;box-shadow:0 0 26px var(--glow)}
#result{margin-top:18px;padding:12px 14px;font-size:14px;word-break:break-all;display:none}
#result.ok{display:block;border:1px solid var(--ok);background:rgba(77,255,148,.07);color:var(--ok);box-shadow:0 0 24px rgba(77,255,148,.18)}
#result.bad{display:block;border:1px solid var(--red);background:rgba(255,42,68,.12);color:#ffb3bd}
#result.bad::before{content:"[!] ";color:var(--red);font-weight:800}
p.note{font-size:12.5px;color:var(--dim);margin-top:18px;line-height:1.5}
@keyframes blink{50%{opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
@media (max-width:600px){.topbar{padding:10px 16px}main{padding:26px 16px 40px}.win .wbody{padding:20px 18px}}
"""

RAIN_JS = r"""
/* NXB theme effects: red code-rain background (#rain) and typewriter line ([data-type]). Pure cosmetic, no network. */
(function(){
  var calm=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var t=document.querySelector('[data-type]');
  if(t){var s=t.getAttribute('data-type');if(calm){t.textContent=s}else{var i=0;(function k(){t.textContent=s.slice(0,++i);if(i<s.length)setTimeout(k,32)})()}}
  var c=document.getElementById('rain');if(!c||calm)return;
  var x=c.getContext('2d'),f=16,cols,drops,ch='01ABCDEF<>/\\{}[]#$%&*+=NXB';
  function size(){c.width=innerWidth;c.height=innerHeight;cols=Math.ceil(c.width/f);drops=[];for(var i=0;i<cols;i++)drops[i]=Math.random()*-50}
  size();addEventListener('resize',size);
  setInterval(function(){
    x.fillStyle='rgba(6,5,6,.16)';x.fillRect(0,0,c.width,c.height);x.font=f+'px monospace';
    for(var i=0;i<cols;i++){
      x.fillStyle=Math.random()>.97?'#fff':'#ff2a44';
      x.fillText(ch[Math.floor(Math.random()*ch.length)],i*f,drops[i]*f);
      if(drops[i]*f>c.height&&Math.random()>.975)drops[i]=0;drops[i]++;
    }
  },60);
})();

"""

def _form_page(stage, title, blurb, fields):
    inputs = "\n".join(
        '<label for="%s">%s</label>'
        '<input type="text" id="%s" name="%s" maxlength="128" required autocomplete="off">' % (n, lbl, n, n)
        for n, lbl in fields
    )
    field_names = json.dumps([n for n, _ in fields])
    return ( "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + title + " - NXB Ledger Evidence Checker</title>"
        "<style>" + FORM_CSS + "</style></head><body><canvas id='rain'></canvas>"
        '<div class="topbar"><div class="brand">NXB<b>LEDGER</b></div>'
        '<div class="pill">EVIDENCE CHECKER</div></div>'
        "<main><div class='win'>"
        "<div class='bar'><i></i><i></i><i></i><span>submit // " + stage + "</span></div>"
        "<div class='wbody'><h2>" + title + "</h2>"
        "<p class='sub'>" + blurb + "</p>"
        "<form id='f'>" + inputs + "<button type='submit'>SUBMIT EVIDENCE</button></form>"
        "<div id='result'></div>"
        "</div></div>"
        "<p class='note'>Validated as JSON against the same strict rules as the API. No answer material is embedded in this page.</p>"
        "</main>"
        "<footer>NXB Ledger CTF &mdash; evidence validation terminal</footer>"
        "<script>"
        "var F=" + field_names + ";"
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
        "</script>" + "<script>" + RAIN_JS + "</script></body></html>" )

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
    cards = []
    for stage, (title, _, _) in STAGE_FORMS.items():
        num, _, name = title.partition(" - ")
        cards.append(
            "<a class='card' href='/check/" + stage + "'><div class='id'>" + num.upper() + "</div>"
            "<p>" + name + "</p><span class='go'>Open terminal</span></a>"
        )
    return ( "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>NXB Ledger - Evidence Checker</title>"
        "<style>" + FORM_CSS + "</style></head><body><canvas id='rain'></canvas>"
        '<div class="topbar"><div class="brand">NXB<b>LEDGER</b></div>'
        '<div class="pill">EVIDENCE CHECKER</div></div>'
        "<main class='wide'>"
        "<div class='hero'><h1 class='glitch' data-text='EVIDENCE CHECKER'>EVIDENCE CHECKER</h1>"
        "<p class='typed' data-type='validating stage submissions for the NXB investigation'></p></div>"
        "<div class='grid'>" + "\n".join(cards) + "</div>"
        "</main>"
        "<footer>NXB Ledger CTF &mdash; evidence validation terminal</footer>"
        "<script>" + RAIN_JS + "</script></body></html>" )

@app.route("/check/<stage>", methods=["GET"])
def check_form(stage):
    if stage not in STAGE_FORMS:
        return jsonify({"correct": False, "message": "Unknown stage."}), 404
    title, blurb, fields = STAGE_FORMS[stage]
    return _form_page(stage, title, blurb, fields)
