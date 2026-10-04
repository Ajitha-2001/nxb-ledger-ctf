#!/usr/bin/env python3
"""
Smoke test for the NXB Ledger deployment. Run AFTER `docker compose up -d`
and after evidence-generation has produced output/secrets/answer_key.json
(this script reads the canonical answers directly - it's a build-verification
test, not a participant walkthrough).

    python3 scripts/smoke_test.py --host 192.168.56.10

Covers (informally) T01-T09 from the design report's testing plan:
  - loan portal login + BOLA exploit path
  - evidence checker: correct/incorrect/malformed handling for stages 1,4,5,6
  - broker site reachability and flag-leak check
  - negative cases (distractors, wrong fields, decoy message, oversized body, rate limit)
  - closed ports 3306/6379/22 (run from a participant machine for a meaningful isolation test)

Note: the checker enforces a 3 s cooldown per stage, so the test paces itself (takes ~1 minute).
"""
import argparse
import base64
import json
import os
import socket
import sys
import time

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSWER_KEY_PATH = os.path.join(BASE, "evidence-generation", "output", "secrets", "answer_key.json")
CHAT_FRAGMENT_PATH = os.path.join(BASE, "evidence-generation", "output", "stage2", "chat_fragment.json")


def ok(label, cond):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}")
    return cond


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.56.10")
    args = ap.parse_args()
    H = args.host
    CH = f"http://{H}:8082"

    with open(ANSWER_KEY_PATH) as f:
        key = json.load(f)
    flags = key["flags"]
    all_pass = True

    def check(label, cond):
        nonlocal all_pass
        all_pass &= ok(label, bool(cond))

    def post(stage, payload, **kw):
        """POST to the checker. The checker allows 1 attempt / 3 s per stage, so wait first."""
        time.sleep(3.2)
        return requests.post(f"{CH}/check/{stage}", json=payload, timeout=5, **kw)

    print("== Broker site (Stage 1) ==")
    r = requests.get(f"http://{H}:8081/index.html", timeout=5)
    check("broker site index reachable", r.status_code == 200)
    check("theme assets served", requests.get(f"http://{H}:8081/assets/nxb-theme.css", timeout=5).status_code == 200)
    check("correct ad page reachable", requests.get(f"http://{H}:8081/ads/{key['stage1']['post_id']}.html", timeout=5).status_code == 200)
    check("source JSON not served", requests.get(f"http://{H}:8081/broker_ads_source.json", timeout=5).status_code in (403, 404))
    leak = "".join(requests.get(f"http://{H}:8081/{p}", timeout=5).text for p in ("index.html", "assets/nxb-fx.js"))
    check("no flags in broker site", not any(v in leak for v in flags.values()))

    print("== Stage 1 checker: correct + distractors ==")
    r = post("stage1", {**key["stage1"], "feature1": "fee phrase", "feature2": "contact code"})
    check("correct pair accepted and returns flag", r.ok and r.json().get("flag") == flags["stage1"])
    r = post("stage1", {"post_id": "PUB-013", "contact_code": "BRK21", "feature1": "fee", "feature2": "x"})
    check("phrase-only distractor (PUB-013/BRK21) rejected", r.ok and r.json().get("correct") is False and "flag" not in r.json())
    r = post("stage1", {"post_id": "PUB-014", "contact_code": "BRK17", "feature1": "contact", "feature2": "x"})
    check("contact-only distractor (PUB-014/BRK17) rejected", r.ok and r.json().get("correct") is False)

    print("== Stage 2 (decode locally) ==")
    with open(CHAT_FRAGMENT_PATH) as f:
        frag = json.load(f)
    check("stage2 flag present in decoded body", flags["stage2"] in base64.b64decode(frag["body"]).decode())

    print("== Loan portal (Stage 3, BOLA) ==")
    P = f"http://{H}:8080"
    bad = requests.post(f"{P}/login", data={"username": "br03_officer", "password": "wrong"}, timeout=5)
    check("wrong password rejected", "Invalid credentials" in bad.text)
    s = requests.Session()
    s.post(f"{P}/login", data={"username": "br03_officer", "password": "Training#2026"}, timeout=5)
    own = s.get(f"{P}/application/APP-0801", timeout=5)
    check("own-branch application opens without a flag", own.status_code == 200 and flags["stage3"] not in own.text)
    check("cross-branch APP-0842 returns stage3 flag", flags["stage3"] in s.get(f"{P}/application/APP-0842", timeout=5).text)
    check("unauthenticated request redirected to login",
          requests.get(f"{P}/application/APP-0842", timeout=5, allow_redirects=False).status_code in (301, 302))

    print("== Checkers: correct answers (Stages 4-6) ==")
    for st in ("stage4", "stage5", "stage6"):
        r = post(st, key[st])
        check(f"{st} correct answer accepted", r.ok and r.json().get("flag") == flags[st])

    print("== Checkers: wrong answers must not leak anything ==")
    r = post("stage4", {"workstation_id": "NXB-BR03-WS07", "capture_event": "CAP-0301"})
    check("stage4 right workstation + wrong capture rejected", r.json().get("correct") is False and "flag" not in r.json())
    r = post("stage5", {**key["stage5"], "unrelated_failed_event": "FAIL-001"})
    check("stage5 one wrong field rejected", r.json().get("correct") is False)
    r = post("stage6", {**key["stage6"], "message_id": "CHAT-76"})
    check("stage6 decoy message CHAT-76 rejected", r.json().get("correct") is False)

    print("== Checker robustness (T10) ==")
    r = post("stage1", {**key["stage1"], "feature1": "a", "feature2": "b", "extra_field": "nope"})
    check("unexpected field rejected with 400", r.status_code == 400)
    time.sleep(3.2)
    r = requests.post(f"{CH}/check/stage1", data="not json", headers={"Content-Type": "application/json"}, timeout=5)
    check("malformed JSON rejected", r.status_code in (400, 415))
    time.sleep(3.2)
    r = requests.post(f"{CH}/check/stage1", data=b"x" * 20000, headers={"Content-Type": "application/json"}, timeout=5)
    check("oversized body rejected (413)", r.status_code == 413)
    time.sleep(3.2)
    first = requests.post(f"{CH}/check/stage4", json={"workstation_id": "a", "capture_event": "b"}, timeout=5)
    second = requests.post(f"{CH}/check/stage4", json={"workstation_id": "a", "capture_event": "b"}, timeout=5)
    check("immediate repeat attempt is rate limited (429)", first.status_code == 200 and second.status_code == 429)

    print("== Isolation (T11, from this machine) ==")
    for port in (3306, 6379, 22):
        sock = socket.socket(); sock.settimeout(2)
        closed = sock.connect_ex((H, port)) != 0
        sock.close()
        check(f"port {port} not reachable", closed)

    print("\n" + ("ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED"))
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
