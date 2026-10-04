#!/usr/bin/env python3
"""
Offline evidence consistency check (no Docker needed). Covers parts of T05, T07-T09.
    python3 tests/check_evidence.py
Exit code 0 only if every check passes.
"""
import csv
import hashlib
import json
import os
import random
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "evidence-generation", "output")
sys.path.insert(0, os.path.join(ROOT, "tests", "reference_solutions"))
import solve_stage6  # noqa: E402

fails = 0


def check(name, cond):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name)
    fails += 0 if cond else 1


def rows(p):
    with open(os.path.join(OUT, p), newline="") as f:
        return list(csv.DictReader(f))


key = json.load(open(os.path.join(OUT, "secrets", "answer_key.json")))
seed = json.load(open(os.path.join(OUT, "secrets", "canonical_seed.json")))

# manifest hashes
manifest = json.load(open(os.path.join(OUT, "manifest.json")))
check("manifest hashes match files", all(
    hashlib.sha256(open(os.path.join(OUT, m["file"]), "rb").read()).hexdigest() == m["sha256"] for m in manifest))
import shutil, subprocess
if shutil.which("sha256sum"):
    for st, mf in (("stage4", "manifest_sha256.txt"), ("stage2", "manifest_sha256.txt")):
        rc = subprocess.run(["sha256sum", "-c", mf], cwd=os.path.join(OUT, st), capture_output=True).returncode
        check(f"sha256sum -c passes in {st}", rc == 0)
flags = key["flags"]
check("all flags have a >=128-bit token (32 hex chars)", all(
    len(v.split("_", 1)[1].rstrip("}")) >= 32 for v in flags.values()))
check("stage6 SCHEMA.md present and has no answer values", os.path.exists(os.path.join(OUT, "stage6", "SCHEMA.md"))
      and not any(v in open(os.path.join(OUT, "stage6", "SCHEMA.md")).read() for v in key["stage6"].values()))
check("stage4 manifest_sha256.txt exists", os.path.exists(os.path.join(OUT, "stage4", "manifest_sha256.txt")))
for line in open(os.path.join(OUT, "stage4", "manifest_sha256.txt")):
    h, fn = line.split()
    check(f"stage4 manifest hash ok: {fn}", hashlib.sha256(open(os.path.join(OUT, "stage4", fn), "rb").read()).hexdigest() == h)

# stage 4
check("capture event matches workstation+application", any(
    r["capture_event_id"] == key["stage4"]["capture_event"] and r["workstation_id"] == seed["workstation_id"]
    and r["application_id"] == seed["application_id"] for r in rows("stage4/capture_events.csv")))

# stage 5
sess = rows("stage5/workstation_sessions.csv")
check("no session logs out before it logs in", all(
    datetime.fromisoformat(r["logout_time_utc+0530"]) > datetime.fromisoformat(r["login_time_utc+0530"]) for r in sess))
acc = [r for r in rows("stage5/app_access.csv") if r["application_id"] == seed["application_id"]]
check("exactly one access record for target app", len(acc) == 1)
check("target session belongs to EMP042 on WS07", any(
    r["session_id"] == acc[0]["session_id"] and r["employee_id"] == seed["employee_id"]
    and r["workstation_id"] == seed["workstation_id"] for r in sess))
check("failed event is EMP019 with no session/access", seed["unrelated_failed_event"] in
      [r["event_id"] for r in rows("stage5/auth.csv")] and not any(r["employee_id"] == "EMP019" for r in sess)
      and not any(r["employee_id"] == "EMP019" for r in rows("stage5/app_access.csv")))
check("leave record is for EMP042 (matches storyline)", any(r["employee_id"] == seed["employee_id"] for r in rows("stage5/leave.csv")))
check("alert note names EMP042 as the one claiming leave", seed["employee_id"] in open(os.path.join(OUT, "stage5", "alert_note.txt")).read())

# stage 6, original and shuffled
s6, s5 = os.path.join(OUT, "stage6"), os.path.join(OUT, "stage5")
expected = key["stage6"]
check("stage6 solver matches answer key", solve_stage6.solve(s6, s5, seed["application_id"]) == expected)
random.seed(1)
check("stage6 solver stable under shuffled rows (x20)", all(
    solve_stage6.solve(s6, s5, seed["application_id"], shuffle=True) == expected for _ in range(20)))
n = sum(1 for l in open(os.path.join(s6, "messages.jsonl")) if json.loads(l).get("application_id") == seed["application_id"])
check("decoy messages exist for target app (>1)", n > 1)

print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
