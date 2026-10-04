#!/usr/bin/env python3
"""
Generates .env for docker-compose:
  - random MariaDB / CTFd / Flask secrets (fresh every build)
  - STAGE3_FLAG pulled from evidence-generation/output/secrets/flags.json

Run AFTER evidence-generation/generate_evidence.py.
"""
import json
import os
import secrets

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS_PATH = os.path.join(BASE, "evidence-generation", "output", "secrets", "flags.json")
ENV_PATH = os.path.join(BASE, ".env")


def token(n=32):
    return secrets.token_urlsafe(n)


def main():
    if not os.path.exists(FLAGS_PATH):
        raise SystemExit(
            f"Missing {FLAGS_PATH}. Run evidence-generation/generate_evidence.py first."
        )
    with open(FLAGS_PATH) as f:
        flags = json.load(f)

    if os.path.exists(ENV_PATH):
        # Keep existing secrets, but make sure STAGE3_FLAG matches flags.json.
        with open(ENV_PATH) as f:
            lines = f.read().splitlines()
        want = f"STAGE3_FLAG={flags['stage3']}"
        if want in lines:
            print(f"[=] {ENV_PATH} already matches flags.json - unchanged.")
            return
        lines = [l for l in lines if not l.startswith("STAGE3_FLAG=")] + [want]
        with open(ENV_PATH, "w") as f:
            f.write("\n".join(lines) + "\n")
        print("[!] STAGE3_FLAG in .env did not match flags.json - updated. Run: docker compose up -d --build loan-portal")
        return

    lines = [
        f"HOST_IP=192.168.56.10",
        f"MARIADB_ROOT_PASSWORD={token(16)}",
        f"MARIADB_PASSWORD={token(16)}",
        f"CTFD_SECRET_KEY={token(32)}",
        f"LOAN_PORTAL_SECRET_KEY={token(32)}",
        f"STAGE3_FLAG={flags['stage3']}",
    ]
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV_PATH, 0o600)
    print(f"[+] Wrote {ENV_PATH} (chmod 600). STAGE3_FLAG = {flags['stage3']}")


if __name__ == "__main__":
    main()
