#!/usr/bin/env python3
"""
Seeds loan_portal.db with:
  - one test account (BR03 loan officer, credentials given to participants)
  - twelve synthetic loan applications across several branches
Run once at image build time (see Dockerfile).
"""
import hashlib
import os
import sqlite3

DB_PATH = os.environ.get("LOAN_DB_PATH", "loan_portal.db")

TEST_USERNAME = "br03_officer"
TEST_PASSWORD = "Training#2026"  # synthetic lab credential, intentionally simple


def pw_hash(pw: str) -> str:
    # Not production-grade; this is a synthetic training app.
    return hashlib.sha256(pw.encode()).hexdigest()


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            branch TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE applications (
            application_id TEXT PRIMARY KEY,
            owning_branch TEXT,
            customer_synthetic_id TEXT,
            salary_band TEXT,
            amount_requested TEXT,
            approval_notes TEXT
        )
    """)

    cur.execute(
        "INSERT INTO accounts (username, password_hash, role, branch) VALUES (?, ?, ?, ?)",
        (TEST_USERNAME, pw_hash(TEST_PASSWORD), "loan_officer", "BR03"),
    )

    applications = [
        ("APP-0801", "BR03", "NXB-DEMO-0801", "LKR 60,000-80,000", "LKR 200,000", "Standard review, no flags."),
        ("APP-0802", "BR03", "NXB-DEMO-0802", "LKR 70,000-90,000", "LKR 300,000", "Standard review."),
        ("APP-0803", "BR03", "NXB-DEMO-0803", "LKR 80,000-100,000", "LKR 250,000", "Pending documents."),
        ("APP-0711", "BR01", "NXB-DEMO-0711", "LKR 55,000-70,000", "LKR 150,000", "Standard review."),
        ("APP-0799", "BR03", "NXB-DEMO-0799", "LKR 65,000-85,000", "LKR 220,000", "Standard review."),
        ("APP-0850", "BR08", "NXB-DEMO-0850", "LKR 75,000-95,000", "LKR 280,000", "Standard review."),
        ("APP-0602", "BR02", "NXB-DEMO-0602", "LKR 60,000-75,000", "LKR 180,000", "Standard review."),
        ("APP-0733", "BR03", "NXB-DEMO-0733", "LKR 90,000-110,000", "LKR 350,000", "Standard review."),
        (
            "APP-0842", "BR08", "NXB-DEMO-0842", "LKR 90,000-120,000", "LKR 450,000",
            "Applicant flagged for expedited processing. A documentation clearance fee of "
            "2% of the approved loan value applies before the file is released for external "
            "verification. Ref handled outside standard branch workflow this cycle.",
        ),
        ("APP-0904", "BR09", "NXB-DEMO-0904", "LKR 50,000-65,000", "LKR 140,000", "Standard review."),
        ("APP-0955", "BR03", "NXB-DEMO-0955", "LKR 85,000-100,000", "LKR 300,000", "Standard review."),
        ("APP-0611", "BR06", "NXB-DEMO-0611", "LKR 60,000-80,000", "LKR 190,000", "Standard review."),
    ]
    cur.executemany(
        "INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?)",
        applications,
    )

    conn.commit()
    conn.close()
    print(f"[+] Seeded {DB_PATH} with 1 account and {len(applications)} applications.")
    print(f"    Test login -> username: {TEST_USERNAME}  password: {TEST_PASSWORD}")


if __name__ == "__main__":
    main()
