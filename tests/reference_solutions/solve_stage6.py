#!/usr/bin/env python3
"""
Reference solution for Stage 6 ("Reconstruct the Ledger").
FACILITATOR / TESTING USE ONLY - do not give this to participants.

Given ONLY the target application_id (known from Stages 2-3) and the evidence
folders, it derives every other field through real joins:

  messages.jsonl  --application_id-->  candidate messages (Base64 bodies decoded)
  messages.jsonl  --sender_handle--->  directory.csv   -> employee_id
  messages.jsonl  --transaction_ref->  broker_ledger.csv (note must reference the application)
  app_access.csv  --application_id-->  session_id          (Stage 5 evidence)
  workstation_sessions.csv --session_id--> employee_id + workstation_id
  cross-check: session employee == directory employee

Usage:
    python3 solve_stage6.py --stage6-dir ../../evidence-generation/output/stage6 \\
                             --stage5-dir ../../evidence-generation/output/stage5 \\
                             --application-id APP-0842 --out evidence.json [--shuffle]
"""
import argparse
import base64
import csv
import json
import os
import random


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def solve(stage6_dir, stage5_dir, application_id, shuffle=False):
    directory = {r["handle"]: r for r in read_csv(os.path.join(stage6_dir, "directory.csv"))}
    ledger = {r["tx_ref"]: r for r in read_csv(os.path.join(stage6_dir, "broker_ledger.csv"))}
    access = read_csv(os.path.join(stage5_dir, "app_access.csv"))
    sessions = {r["session_id"]: r for r in read_csv(os.path.join(stage5_dir, "workstation_sessions.csv"))}

    with open(os.path.join(stage6_dir, "messages.jsonl")) as f:
        messages = [json.loads(line) for line in f if line.strip()]
    if shuffle:
        random.shuffle(messages)

    # Join 1: application -> session -> workstation/employee
    app_sessions = [a for a in access if a["application_id"] == application_id and a["session_id"] in sessions]
    if len(app_sessions) != 1:
        raise SystemExit(f"Expected exactly one session for {application_id}, found {len(app_sessions)}")
    sess = sessions[app_sessions[0]["session_id"]]

    # Join 2+3: message -> directory (employee) and message -> ledger (payment)
    hits = []
    for m in messages:
        if m.get("application_id") != application_id:
            continue
        body = base64.b64decode(m["body_b64"]).decode("utf-8", errors="replace")
        person = directory.get(m.get("sender_handle"))
        if not person or person["employee_id"] in ("", "N/A"):
            continue                      # external broker handle, not an employee
        tx = ledger.get(m.get("transaction_ref") or "")
        if not tx or application_id not in tx["note"]:
            continue                      # no matching payment record for this application
        hits.append((m, person, tx, body))
    if len(hits) != 1:
        raise SystemExit(f"Expected exactly one employee->broker message chain, found {len(hits)}")
    m, person, tx, _ = hits[0]

    # Consistency check across independent sources
    if person["employee_id"] != sess["employee_id"]:
        raise SystemExit("Directory employee does not match session employee - evidence is inconsistent")

    return {
        "employee_id": person["employee_id"],
        "application_id": application_id,
        "workstation_id": sess["workstation_id"],
        "session_id": sess["session_id"],
        "broker_transaction_ref": tx["tx_ref"],
        "message_id": m["message_id"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage6-dir", required=True)
    ap.add_argument("--stage5-dir", required=True)
    ap.add_argument("--application-id", required=True)
    ap.add_argument("--out", default="evidence.json")
    ap.add_argument("--shuffle", action="store_true", help="shuffle input rows (T09)")
    args = ap.parse_args()
    evidence = solve(args.stage6_dir, args.stage5_dir, args.application_id, args.shuffle)
    with open(args.out, "w") as f:
        json.dump(evidence, f, indent=2)
    print(f"[+] Wrote {args.out}:\n{json.dumps(evidence, indent=2)}")


if __name__ == "__main__":
    main()
